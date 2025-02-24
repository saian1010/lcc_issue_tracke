from loginapp import app
from loginapp import db
from flask import redirect, render_template, request, session, url_for
from flask_bcrypt import Bcrypt
import re

# Create an instance of the Bcrypt class, which we'll be using to hash user
# passwords during login and registration.
flask_bcrypt = Bcrypt(app)

# Default role assigned to new users upon registration.
DEFAULT_USER_ROLE = 'visitor'

def user_home_url():
    """Generates a URL to the homepage for the currently logged-in user.
    
    If the user is not logged in, or the role stored in their session cookie is
    invalid, this returns the URL for the login page instead."""
    role = session.get('role', None)

    if role=='visitor':
        home_endpoint='customer_home'
    elif role=='helper':
        home_endpoint='staff_home'
    elif role=='admin':
        home_endpoint='admin_home'
    else:
        home_endpoint = 'login'
    
    return url_for(home_endpoint)

@app.route('/')
def root():
    """Root endpoint (/)
    
    Methods:
    - get: Redirects guests to the login page, and redirects logged-in users to
        their own role-specific homepage.
    """
    return redirect(user_home_url())

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page endpoint.

    Methods:
    - get: Renders the login page.
    - post: Attempts to log the user in using the credentials supplied via the
        login form, and either:
        - Redirects the user to their role-specific homepage (if successful)
        - Renders the login page again with an error message (if unsuccessful).
    
    If the user is already logged in, both get and post requests will redirect
    to their role-specific homepage.
    """
    if 'loggedin' in session:
         return redirect(user_home_url())

    if request.method=='POST' and 'username' in request.form and 'password' in request.form:
        # Get the login details submitted by the user.
        username = request.form['username']
        password = request.form['password']

        # Attempt to validate the login details against the database.
        with db.get_cursor() as cursor:
            # Try to retrieve the account details for the specified username.
            #
            # Note: we use a Python multiline string (triple quote) here to
            # make the query more readable in source code. This is just a style
            # choice: the line breaks are ignored by MySQL, and it would be
            # equally valid to put the whole SQL statement on one line like we
            # do at the beginning of the `signup` function.
            cursor.execute('''
                           SELECT user_id, username, password_hash, role
                           FROM users
                           WHERE username = %s;
                           ''', (username,))
            account = cursor.fetchone()
            
            if account is not None:
                # We found a matching account: now we need to check whether the
                # password they supplied matches the hash in our database.
                password_hash = account['password_hash']
                
                if flask_bcrypt.check_password_hash(password_hash, password):
                    # Password is correct. Save the user's ID, username, and role
                    # as session data, which we can access from other routes to
                    # determine who's currently logged in.
                    # 
                    # Users can potentially see and edit these details using their
                    # web browser. However, the session cookie is signed with our
                    # app's secret key. That means if they try to edit the cookie
                    # to impersonate another user, the signature will no longer
                    # match and Flask will know the session data is invalid.
                    session['loggedin'] = True
                    session['user_id'] = account['user_id']
                    session['username'] = account['username']
                    session['role'] = account['role']

                    return redirect(user_home_url())
                else:
                    # Password is incorrect. Re-display the login form, keeping
                    # the username provided by the user so they don't need to
                    # re-enter it. We also set a `password_invalid` flag that
                    # the template uses to display a validation message.
                    return render_template('login.html',
                                           username=username,
                                           password_invalid=True)
            else:
                # We didn't find an account in the database with this username.
                # Re-display the login form, keeping the username so the user
                # can see what they entered (otherwise, they might just keep
                # trying the same thing). We also set a `username_invalid` flag
                # that tells the template to display an appropriate message.
                #
                # Note: In this example app, we tell the user if the user
                # account doesn't exist. Many websites (e.g. Google, Microsoft)
                # do this, but other sites display a single "Invalid username
                # or password" message to prevent an attacker from determining
                # whether a username exists or not. Here, we accept that risk
                # to provide more useful feedback to the user.
                return render_template('login.html', 
                                       username=username,
                                       username_invalid=True)

    # This was a GET request, or an invalid POST (no username and/or password),
    # so we just render the login form with no pre-populated details or flags.
    return render_template('login.html')

@app.route('/signup', methods=['GET','POST'])
def signup():
    """Signup (registration) page endpoint.

    Methods:
    - get: Renders the signup page.
    - post: Attempts to create a new user account using the details supplied
        via the signup form, then renders the signup page again with a welcome
        message (if successful) or one or more error message(s) explaining why
        signup could not be completed.

    If the user is already logged in, both get and post requests will redirect
    to their role-specific homepage.
    """
    if 'loggedin' in session:
         return redirect(user_home_url())
    
    if request.method == 'POST' and all(field in request.form for field in ['username', 'email', 'password', 'first_name', 'last_name', 'location']):
        # Get form data and strip whitespace
        username = request.form['username'].strip()
        email = request.form['email'].strip()
        password = request.form['password']  # Don't strip password as spaces might be intentional
        first_name = request.form['first_name'].strip()
        last_name = request.form['last_name'].strip()
        location = request.form['location'].strip()

        # Initialize error variables
        errors = {}

        # Check if all required fields are present
        if not all([username, email, password, first_name, last_name, location]):
            if not username:
                errors['username_error'] = 'Username is required.'
            if not email:
                errors['email_error'] = 'Email is required.'
            if not password:
                errors['password_error'] = 'Password is required.'
            if not first_name:
                errors['first_name_error'] = 'First name is required.'
            if not last_name:
                errors['last_name_error'] = 'Last name is required.'
            if not location:
                errors['location_error'] = 'Location is required.'
        else:
            # Check for existing username
            with db.get_cursor() as cursor:
                cursor.execute('SELECT user_id FROM users WHERE username = %s;',
                               (username,))
                account_already_exists = cursor.fetchone() is not None
            
            # Validate all fields
            if account_already_exists:
                errors['username_error'] = 'An account already exists with this username.'
            elif len(username) > 20:
                errors['username_error'] = 'Your username cannot exceed 20 characters.'
            elif not re.match(r'^[A-Za-z0-9]+$', username):
                errors['username_error'] = 'Your username can only contain letters and numbers.'            

            if len(email) > 320:
                errors['email_error'] = 'Your email address cannot exceed 320 characters.'
            elif not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
                errors['email_error'] = 'Invalid email address.'
                    
            if len(password) < 8:
                errors['password_error'] = 'Password must be at least 8 characters long.'

            if len(first_name) > 50:
                errors['first_name_error'] = 'First name cannot exceed 50 characters.'

            if len(last_name) > 50:
                errors['last_name_error'] = 'Last name cannot exceed 50 characters.'

            if len(location) > 50:
                errors['location_error'] = 'Location cannot exceed 50 characters.'
                    
        if errors:
            # Return form with errors and previously entered values
            return render_template('signup.html',
                                username=username,
                                email=email,
                                first_name=first_name,
                                last_name=last_name,
                                location=location,
                                **errors)
        else:
            # Create new account
            password_hash = flask_bcrypt.generate_password_hash(password)
            
            with db.get_cursor() as cursor:
                cursor.execute('''
                    INSERT INTO users (
                        username, password_hash, email, first_name, last_name,
                        location, role, status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                    ''',
                    (username, password_hash, email, first_name, last_name,
                     location, DEFAULT_USER_ROLE, 'active'))
            
            return render_template('signup.html', signup_successful=True)            

    # GET request or invalid POST
    return render_template('signup.html')

@app.route('/profile')
def profile():
    """User Profile page endpoint.

    Methods:
    - get: Renders the user profile page for the current user.

    If the user is not logged in, requests will redirect to the login page.
    """
    if 'loggedin' not in session:
         return redirect(url_for('login'))

    # Retrieve user profile from the database.
    with db.get_cursor() as cursor:
        cursor.execute('SELECT username, email, role FROM users WHERE user_id = %s;',
                       (session['user_id'],))
        profile = cursor.fetchone()

    return render_template('profile.html', profile=profile)

@app.route('/logout')
def logout():
    """Logout endpoint.

    Methods:
    - get: Logs the current user out (if they were logged in to begin with),
        and redirects them to the login page.
    """
    # Note that nothing actually happens on the server when a user logs out: we
    # just remove the cookie from their web browser. They could technically log
    # back in by manually restoring the cookie we've just deleted. In a high-
    # security web app, you may need additional protections against this (e.g.
    # keeping a record of active sessions on the server side).
    session.pop('loggedin', None)
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('role', None)
    
    return redirect(url_for('login'))