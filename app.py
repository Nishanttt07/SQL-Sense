from flask import Flask, render_template, session, request, jsonify, redirect, url_for
import config
from ai_handler import AIHandler
import json
import os
from urllib.parse import urlparse

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'sql-sense-dev-key-2024')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['TEMPLATES_AUTO_RELOAD'] = True

ai_handler = AIHandler()

@app.route('/')
def index():
    """Home page - choose database type"""
    return render_template('index.html')

@app.route('/connect/mysql', methods=['GET', 'POST'])
def connect_mysql():
    """MySQL connection form and handler"""
    if request.method == 'POST':
        # Get credentials from form
        mysql_credentials = {
            'host': request.form.get('host', '').strip(),
            'user': request.form.get('user', '').strip(),
            'password': request.form.get('password', '').strip(),
            'database': request.form.get('database', '').strip(),
            'port': request.form.get('port', '3306').strip()
        }
        
        # Validate required fields
        if not all([mysql_credentials['host'], mysql_credentials['user'], 
                   mysql_credentials['database']]):
            return render_template('connect_mysql.html', 
                                 error="Please fill in all required fields")
        
        try:
            # Test connection using AI handler
            schema_context = ai_handler.get_schema_context('mysql', mysql_credentials)
            
            if "Error fetching schema" in schema_context or "failed" in schema_context.lower():
                return render_template('connect_mysql.html', 
                                     error=f"Connection failed: {schema_context}")
            
            # Store in session
            session['db_type'] = 'mysql'
            session['db_credentials'] = mysql_credentials
            session['connection_status'] = 'connected'
            session['schema_context'] = schema_context  # Store schema for display
            
            return redirect(url_for('query_interface'))
            
        except Exception as e:
            error_msg = str(e)
            if "Access denied" in error_msg:
                return render_template('connect_mysql.html', 
                                     error="Access denied. Check username and password.")
            elif "Unknown database" in error_msg:
                return render_template('connect_mysql.html', 
                                     error="Database does not exist. Please check the database name.")
            elif "Can't connect" in error_msg:
                return render_template('connect_mysql.html', 
                                     error="Cannot connect to MySQL server. Check host, port, and ensure server is running.")
            else:
                return render_template('connect_mysql.html', 
                                     error=f"Connection failed: {error_msg}")
    
    return render_template('connect_mysql.html')

@app.route('/connect/supabase', methods=['GET', 'POST'])
def connect_supabase():
    """Supabase connection form and handler using Supabase URL and API key"""
    if request.method == 'POST':
        # Get credentials from form using Supabase standard format
        supabase_credentials = {
            'supabase_url': request.form.get('supabase_url', '').strip(),
            'supabase_key': request.form.get('supabase_key', '').strip(),
            'database_password': request.form.get('database_password', '').strip(),
            'host': request.form.get('host', '').strip() or 'db.your-project-ref.supabase.co',
            'port': request.form.get('port', '5432').strip(),
            'database': request.form.get('database', 'postgres').strip(),
            'user': request.form.get('user', 'postgres').strip()
        }
        
        # Validate required fields
        if not all([supabase_credentials['supabase_url'], 
                   supabase_credentials['supabase_key'],
                   supabase_credentials['database_password']]):
            return render_template('connect_supabase.html', 
                                 error="Please fill in all required fields")
        
        # Auto-generate host from Supabase URL if not provided
        if not supabase_credentials['host'] or supabase_credentials['host'] == 'db.your-project-ref.supabase.co':
            try:
                url_obj = urlparse(supabase_credentials['supabase_url'])
                hostname = url_obj.hostname
                if hostname and 'supabase.co' in hostname:
                    supabase_credentials['host'] = hostname.replace('supabase.co', 'supabase.co').replace('https://', 'db.')
            except:
                pass
        
        try:
            # Test connection using AI handler
            schema_context = ai_handler.get_schema_context('supabase', supabase_credentials)
            
            if "PostgreSQL support not available" in schema_context:
                # Store anyway for demo purposes
                session['db_type'] = 'supabase'
                session['db_credentials'] = supabase_credentials
                session['connection_status'] = 'connected_demo'
                session['schema_context'] = "Demo mode - PostgreSQL support not fully available"
                return redirect(url_for('query_interface'))
            elif "Error fetching schema" in schema_context or "failed" in schema_context.lower():
                return render_template('connect_supabase.html', 
                                     error=f"Connection failed: {schema_context}")
            
            # Store in session
            session['db_type'] = 'supabase'
            session['db_credentials'] = supabase_credentials
            session['connection_status'] = 'connected'
            session['schema_context'] = schema_context  # Store schema for display
            
            return redirect(url_for('query_interface'))
            
        except Exception as e:
            error_msg = str(e)
            if "connection" in error_msg.lower() and "failed" in error_msg.lower():
                return render_template('connect_supabase.html', 
                                     error="Cannot connect to Supabase. Check your Project URL, API Key, and Database Password.")
            elif "authentication" in error_msg.lower():
                return render_template('connect_supabase.html', 
                                     error="Authentication failed. Check your Database Password and API Key.")
            else:
                return render_template('connect_supabase.html', 
                                     error=f"Connection failed: {error_msg}")
    
    return render_template('connect_supabase.html')

@app.route('/connect/firebase', methods=['GET', 'POST'])
def connect_firebase():
    """Firebase connection form and handler"""
    if request.method == 'POST':
        firebase_credentials = {
            'service_account_key': request.form.get('service_account_key', '').strip(),
            'database_url': request.form.get('database_url', '').strip()
        }
        
        # Validate required fields
        if not all([firebase_credentials['service_account_key'], 
                   firebase_credentials['database_url']]):
            return render_template('connect_firebase.html', 
                                 error="Please fill in all required fields")
        
        try:
            # Validate JSON
            json.loads(firebase_credentials['service_account_key'])
            
            # Test connection using AI handler
            schema_context = ai_handler.get_schema_context('firebase', firebase_credentials)
            
            if "Error fetching schema" in schema_context or "failed" in schema_context.lower():
                return render_template('connect_firebase.html', 
                                     error=f"Connection failed: {schema_context}")
            
            session['db_type'] = 'firebase'
            session['db_credentials'] = firebase_credentials
            session['connection_status'] = 'connected'
            session['schema_context'] = schema_context  # Store schema for display
            
            return redirect(url_for('query_interface'))
            
        except json.JSONDecodeError:
            return render_template('connect_firebase.html', 
                                 error="Invalid JSON in service account key")
        except Exception as e:
            return render_template('connect_firebase.html', 
                                 error=f"Connection setup failed: {str(e)}")
    
    return render_template('connect_firebase.html')

@app.route('/demo')
def demo_mode():
    """Demo mode without real database connection"""
    session['db_type'] = 'demo'
    session['db_credentials'] = {'mode': 'demo'}
    session['connection_status'] = 'demo'
    session['schema_context'] = ai_handler.get_schema_context('demo', {})
    return redirect(url_for('query_interface'))

@app.route('/query')
def query_interface():
    """Main query interface"""
    if 'db_type' not in session:
        return redirect(url_for('index'))
    
    # Ensure schema context is available
    if 'schema_context' not in session:
        try:
            session['schema_context'] = ai_handler.get_schema_context(
                session['db_type'], 
                session.get('db_credentials', {})
            )
        except:
            session['schema_context'] = "Unable to fetch schema"
    
    return render_template('query_interface.html')

@app.route('/api/generate-query', methods=['POST'])
def generate_query():
    """API endpoint to generate SQL query using AI"""
    if 'db_type' not in session:
        return jsonify({'error': 'No database connection. Please connect to a database first.'}), 400
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400
        
    user_prompt = data.get('prompt')
    
    if not user_prompt:
        return jsonify({'error': 'No prompt provided'}), 400
    
    try:
        # Generate query using AI handler
        generated_query = ai_handler.generate_query(
            db_type=session['db_type'],
            db_credentials=session['db_credentials'],
            user_prompt=user_prompt,
            gemini_api_key=config.GEMINI_API_KEY
        )
        
        return jsonify({'query': generated_query})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/execute-query', methods=['POST'])
def execute_query():
    """API endpoint to execute the generated query"""
    if 'db_type' not in session:
        return jsonify({'error': 'No database connection. Please connect to a database first.'}), 400
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400
        
    query = data.get('query')
    
    if not query:
        return jsonify({'error': 'No query provided'}), 400
    
    try:
        # Execute query using AI handler
        result = ai_handler.execute_query(
            db_type=session['db_type'],
            db_credentials=session['db_credentials'],
            query=query
        )
        
        # Ensure result has consistent structure
        if 'error' in result:
            return jsonify({'error': result['error']}), 500
        else:
            return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/get-schema')
def get_schema():
    """API endpoint to get current database schema"""
    if 'db_type' not in session:
        return jsonify({'error': 'No database connection'}), 400
    
    try:
        # Refresh schema context
        schema_context = ai_handler.get_schema_context(
            session['db_type'], 
            session.get('db_credentials', {})
        )
        session['schema_context'] = schema_context
        return jsonify({'schema': schema_context})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/disconnect')
def disconnect():
    """Clear session and disconnect from database"""
    session.clear()
    return redirect(url_for('index'))

@app.route('/test-connection', methods=['POST'])
def test_connection():
    """Test database connection without redirecting"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No JSON data provided'})
        
    db_type = data.get('db_type')
    credentials = data.get('credentials')
    
    if not db_type or not credentials:
        return jsonify({'success': False, 'error': 'Missing db_type or credentials'})
    
    try:
        schema_context = ai_handler.get_schema_context(db_type, credentials)
        
        if "Error fetching schema" in schema_context or "failed" in schema_context.lower():
            return jsonify({'success': False, 'error': schema_context})
        else:
            return jsonify({'success': True, 'message': 'Connection successful!', 'schema_preview': schema_context[:200] + '...'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/connection-status')
def connection_status():
    """Get current connection status"""
    if 'db_type' not in session:
        return jsonify({'connected': False})
    
    status_info = {
        'connected': True,
        'db_type': session['db_type'],
        'connection_status': session.get('connection_status', 'unknown'),
        'schema_available': 'schema_context' in session
    }
    
    return jsonify(status_info)

# Debug routes
@app.route('/debug/routes')
def debug_routes():
    """Show all registered routes for debugging"""
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods),
            'path': str(rule)
        })
    return jsonify(routes)

@app.route('/debug/session')
def debug_session():
    """Show current session data"""
    return jsonify(dict(session))

@app.route('/test')
def test_route():
    return "Flask is working!"

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)