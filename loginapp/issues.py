from loginapp import app
from loginapp import db
from flask import redirect, render_template, session, url_for, request, flash
from datetime import datetime

@app.route('/issues')
def list_issues():
    """List issues endpoint with pagination and filters."""
    if 'loggedin' not in session:
        return redirect(url_for('login'))
        
    page = request.args.get('page', 1, type=int)
    search_name = request.args.get('search_name', '')
    status_filter = request.args.get('status', '')
    is_resolved = request.args.get('resolved', '') == 'true'
    
    per_page = 10
    offset = (page - 1) * per_page
    
    cursor = db.get_db().cursor()
    
    # Base query
    query = """
        SELECT i.*, u.username 
        FROM issues i 
        JOIN users u ON i.user_id = u.user_id 
        WHERE 1=1
    """
    params = []
    
    # Add filters
    if session['role'] == 'visitor':
        query += " AND i.user_id = %s"
        params.append(session['user_id'])
        
    if search_name:
        query += " AND i.summary LIKE %s"
        params.append(f"%{search_name}%")
        
    # 根据标签页添加状态条件
    if is_resolved:
        query += " AND i.status = 'resolved'"
    else:
        query += " AND i.status != 'resolved'"
        if status_filter:
            query += " AND i.status = %s"
            params.append(status_filter)
    
    # Get total count for pagination
    count_query = f"SELECT COUNT(*) FROM ({query}) as t"
    cursor.execute(count_query, params)
    total_count = cursor.fetchone()[0]
    total_pages = (total_count + per_page - 1) // per_page
    
    # Add sorting and pagination
    query += " ORDER BY i.created_at DESC LIMIT %s OFFSET %s"
    params.extend([per_page, offset])
    
    # Execute final query
    cursor.execute(query, params)
    issues = cursor.fetchall()
    cursor.close()
    
    return render_template('issues/list.html', 
                         issues=issues,
                         current_page=page,
                         total_pages=total_pages,
                         search_name=search_name,
                         status_filter=status_filter)

@app.route('/issues/new', methods=['GET', 'POST'])
def create_issue():
    """Create new issue endpoint."""
    if 'loggedin' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        summary = request.form.get('summary', '').strip()
        description = request.form.get('description', '').strip()
        
        # Validate input
        if not summary or not description:
            flash('Please fill in all required fields')
            return render_template('issues/create.html')
            
        if len(summary) > 255:
            flash('Summary must not exceed 255 characters')
            return render_template('issues/create.html')
            
        if len(summary) < 3:
            flash('Summary must be at least 3 characters long')
            return render_template('issues/create.html')
            
        if len(description) < 50:
            flash('Description must be at least 50 characters long')
            return render_template('issues/create.html')
            
        if len(description) > 5000:
            flash('Description must not exceed 5000 characters')
            return render_template('issues/create.html')
            
        try:
            cursor = db.get_db().cursor()
            sql = """INSERT INTO issues 
                    (user_id, summary, description, created_at, status) 
                    VALUES (%s, %s, %s, %s, %s)"""
            values = (session['user_id'], summary, description, 
                     datetime.now(), 'new')
            cursor.execute(sql, values)
            db.get_db().commit()
            cursor.close()
            
            return redirect(url_for('list_issues'))
            
        except Exception as e:
            print(f"Error creating issue: {str(e)}")
            flash('Failed to create issue. Please try again later')
            return render_template('issues/create.html')
            
    return render_template('issues/create.html')

@app.route('/issues/<int:issue_id>')
def view_issue(issue_id):
    """View issue details and comments."""
    if 'loggedin' not in session:
        return redirect(url_for('login'))
        
    cursor = db.get_db().cursor()
    
    # Get issue details with specific field order
    cursor.execute("""
        SELECT 
            i.issue_id,          -- 0
            i.user_id,           -- 1
            i.summary,           -- 2
            i.description,       -- 3
            i.status,            -- 4
            i.created_at,        -- 5
            u.username,          -- 6
            u.role,              -- 7
            u.profile_image      -- 8
        FROM issues i 
        JOIN users u ON i.user_id = u.user_id 
        WHERE i.issue_id = %s
    """, (issue_id,))
    issue = cursor.fetchone()
    
    if not issue:
        cursor.close()
        return render_template('404.html'), 404
        
    # Get comments with user info, ordered by created_at DESC
    cursor.execute("""
        SELECT 
            c.comment_id,        -- 0
            c.user_id,           -- 1
            c.content,           -- 2
            c.created_at,        -- 3
            c.issue_id,          -- 4
            u.username,          -- 5
            u.role,              -- 6
            u.profile_image      -- 7
        FROM comments c
        JOIN users u ON c.user_id = u.user_id
        WHERE c.issue_id = %s
        ORDER BY c.created_at DESC
    """, (issue_id,))
    comments = cursor.fetchall()
    cursor.close()
    
    # Convert profile_image filename to full path
    def get_image_path(filename):
        return f'/loginapp/uploads/{filename}' if filename else '/static/default.png'
    
    # Create new issue tuple with updated image path
    issue = list(issue)
    issue[8] = get_image_path(issue[8])
    
    # Create new comments list with updated image paths
    comments = [list(comment) for comment in comments]
    for comment in comments:
        comment[7] = get_image_path(comment[7])
    
    return render_template('issues/view.html', 
                         issue=issue,
                         comments=comments,
                         default_picture='/static/default.png')

@app.route('/issues/<int:issue_id>/comments', methods=['POST'])
def add_comment(issue_id):
    if 'loggedin' not in session:
        return redirect(url_for('login'))
        
    content = request.form.get('content', '').strip()
    
    if not content:
        flash('Comment cannot be empty')
        return redirect(url_for('view_issue', issue_id=issue_id))
        
    if len(content) < 10:
        flash('Comment must be at least 10 characters long')
        return redirect(url_for('view_issue', issue_id=issue_id))
        
    if len(content) > 1000:
        flash('Comment must not exceed 1000 characters')
        return redirect(url_for('view_issue', issue_id=issue_id))
        
    try:
        with db.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO comments (issue_id, user_id, content, created_at)
                VALUES (%s, %s, %s, %s)
            """, (issue_id, session['user_id'], content, datetime.now()))
            db.get_db().commit()
            
    except Exception as e:
        print(f"Error adding comment: {str(e)}")
        flash('Failed to add comment. Please try again later')
        
    return redirect(url_for('view_issue', issue_id=issue_id)) 