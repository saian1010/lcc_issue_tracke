from loginapp import app
from loginapp import db
from flask import redirect, render_template, session, url_for, request, flash
from datetime import datetime

@app.route('/issues/new', methods=['GET', 'POST'])
def create_issue():
    """Create new issue endpoint.
    
    Methods:
    - GET: Renders the issue creation form
    - POST: Handles form submission and creates new issue
    
    If the user is not logged in or is a visitor, redirects to login or shows access denied.
    """
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    elif session['role'] == 'visitor':
        return render_template('access_denied.html'), 403
        
    if request.method == 'POST':
        summary = request.form.get('summary')
        description = request.form.get('description')
        
        if not summary or not description:
            flash('Please fill in all required fields')
            return render_template('issues/create.html')
            
        try:
            with db.get_cursor() as cursor:
                # Create new issue
                sql = """INSERT INTO issues 
                        (user_id, summary, description, created_at, status) 
                        VALUES (%s, %s, %s, %s, %s)"""
                values = (session['user_id'], summary, description, 
                         datetime.now(), 'new')
                cursor.execute(sql, values)
                db.commit()
            
            flash('Issue created successfully!')
            return redirect(url_for('list_issues'))
        except Exception as e:
            flash('Failed to create issue. Please try again later')
            return render_template('issues/create.html')
            
    return render_template('issues/create.html')

@app.route('/issues')
def list_issues():
    """List issues endpoint.
    
    Methods:
    - GET: Displays all issues in descending order by creation date
    
    If the user is not logged in, redirects to login page.
    """
    if 'loggedin' not in session:
        return redirect(url_for('login'))
        
    with db.get_cursor() as cursor:
        cursor.execute("""
            SELECT i.*, u.username 
            FROM issues i 
            JOIN users u ON i.user_id = u.user_id 
            ORDER BY i.created_at DESC
        """)
        issues = cursor.fetchall()
    
    return render_template('issues/list.html', issues=issues)

@app.route('/issues/<int:issue_id>')
def view_issue(issue_id):
    if 'loggedin' not in session:
        return redirect(url_for('login'))
        
    with db.get_cursor() as cursor:
        cursor.execute("""
            SELECT i.*, u.username 
            FROM issues i 
            JOIN users u ON i.user_id = u.user_id 
            WHERE i.issue_id = %s
        """, (issue_id,))
        issue = cursor.fetchone()
        
    if not issue:
        return render_template('404.html'), 404
        
    return render_template('issues/view.html', issue=issue) 