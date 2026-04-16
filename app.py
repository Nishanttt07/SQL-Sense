# #  # app.py




# from flask import Flask, render_template, session, request, jsonify, redirect, url_for
# import config
# from ai_handler import AIHandler
# import json
# import os
# from urllib.parse import urlparse
# import time
# import testfirebase
# from datetime import timedelta
# import uuid

# app = Flask(__name__)
# app.secret_key = os.environ.get('SECRET_KEY', 'sql-sense-dev-key-2024')

# # Enhanced session configuration
# app.config['SESSION_PERMANENT'] = True
# app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)
# app.config['SESSION_COOKIE_HTTPONLY'] = True
# app.config['SESSION_COOKIE_SECURE'] = False
# app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
# app.config['SESSION_COOKIE_NAME'] = 'sql_sense_session'

# # Initialize AI Handler
# ai_handler = AIHandler()

# def clear_previous_connections():
#     """Clear any previous database connections and clean up resources"""
#     session_keys_to_clear = ['db_type', 'db_credentials', 'connection_status', 'schema_context', 'firebase_schema_data', 'connection_id']
#     for key in session_keys_to_clear:
#         session.pop(key, None)
#     session.modified = True

# def format_firebase_schema(schema_data, project_id):
#     """Convert Firebase schema data to readable string format"""
#     if not schema_data:
#         return "No schema data available"
    
#     if not isinstance(schema_data, dict):
#         return f"Schema data format issue: {type(schema_data)} - {str(schema_data)[:200]}"
    
#     schema_info = ["🔥 Firebase Firestore Database Schema"]
#     schema_info.append(f"Project: {project_id}")
#     schema_info.append("=" * 60)
    
#     collection_count = 0
#     total_documents = 0
    
#     for collection_name, documents in schema_data.items():
#         collection_count += 1
        
#         if not isinstance(documents, dict):
#             schema_info.append(f"\n📁 Collection: {collection_name}")
#             schema_info.append("-" * 40)
#             schema_info.append(f"Unexpected data format: {type(documents)}")
#             continue
            
#         doc_count = len(documents)
#         total_documents += doc_count
        
#         schema_info.append(f"\n📁 Collection: {collection_name}")
#         schema_info.append("-" * 40)
#         schema_info.append(f"Documents: {doc_count}")
        
#         sample_count = min(2, doc_count)
#         if sample_count > 0:
#             schema_info.append(f"Sample documents ({sample_count} of {doc_count}):")
#             for i, (doc_id, doc_data) in enumerate(list(documents.items())[:sample_count]):
#                 schema_info.append(f"  📄 {doc_id}:")
                
#                 if isinstance(doc_data, dict):
#                     for key, value in list(doc_data.items())[:3]:
#                         value_str = str(value)
#                         if len(value_str) > 50:
#                             value_str = value_str[:50] + "..."
#                         schema_info.append(f"    - {key}: {value_str}")
#                 else:
#                     schema_info.append(f"    - Data: {str(doc_data)[:100]}...")
                    
#                 if i < sample_count - 1:
#                     schema_info.append("")
    
#     schema_info.append("=" * 60)
#     schema_info.append(f"Total collections: {collection_count}")
#     schema_info.append(f"Total documents: {total_documents}")
    
#     if collection_count == 0:
#         schema_info.append("\n⚠️ No collections found in the database.")
    
#     return "\n".join(schema_info)

# @app.before_request
# def make_session_permanent():
#     session.permanent = True

# @app.route('/')
# def index():
#     """Home page - choose database type"""
#     clear_previous_connections()
#     return render_template('index.html')

# @app.route('/connect/mysql', methods=['GET', 'POST'])
# def connect_mysql():
#     """MySQL connection form and handler"""
#     clear_previous_connections()
    
#     if request.method == 'POST':
#         mysql_credentials = {
#             'host': request.form.get('host', '').strip(),
#             'user': request.form.get('user', '').strip(),
#             'password': request.form.get('password', '').strip(),
#             'database': request.form.get('database', '').strip(),
#             'port': request.form.get('port', '3306').strip()
#         }
        
#         if not all([mysql_credentials['host'], mysql_credentials['user'], mysql_credentials['database']]):
#             return render_template('connect_mysql.html', error="Please fill in all required fields")
        
#         try:
#             schema_context = ai_handler.get_schema_context('mysql', mysql_credentials)
            
#             if "Error fetching schema" in schema_context or "failed" in schema_context.lower():
#                 return render_template('connect_mysql.html', error=f"Connection failed: {schema_context}")
            
#             session.clear()
#             session['db_type'] = 'mysql'
#             session['db_credentials'] = mysql_credentials
#             session['connection_status'] = 'connected'
#             session['schema_context'] = schema_context
#             session.modified = True
            
#             return redirect(url_for('query_interface'))
            
#         except Exception as e:
#             error_msg = str(e)
#             if "Access denied" in error_msg:
#                 return render_template('connect_mysql.html', error="Access denied. Check username and password.")
#             elif "Unknown database" in error_msg:
#                 return render_template('connect_mysql.html', error="Database does not exist. Please check the database name.")
#             elif "Can't connect" in error_msg:
#                 return render_template('connect_mysql.html', error="Cannot connect to MySQL server. Check host, port, and ensure server is running.")
#             else:
#                 return render_template('connect_mysql.html', error=f"Connection failed: {error_msg}")
    
#     return render_template('connect_mysql.html')

# @app.route('/connect/supabase', methods=['GET', 'POST'])
# def connect_supabase():
#     """Supabase connection form and handler"""
#     clear_previous_connections()
    
#     if request.method == 'POST':
#         supabase_credentials = {
#             'supabase_url': request.form.get('supabase_url', '').strip(),
#             'supabase_key': request.form.get('supabase_key', '').strip(),
#             'database_password': request.form.get('database_password', '').strip(),
#             'host': request.form.get('host', '').strip() or 'db.your-project-ref.supabase.co',
#             'port': request.form.get('port', '5432').strip(),
#             'database': request.form.get('database', 'postgres').strip(),
#             'user': request.form.get('user', 'postgres').strip()
#         }
        
#         if not all([supabase_credentials['supabase_url'], supabase_credentials['supabase_key'], supabase_credentials['database_password']]):
#             return render_template('connect_supabase.html', error="Please fill in all required fields")
        
#         if not supabase_credentials['host'] or supabase_credentials['host'] == 'db.your-project-ref.supabase.co':
#             try:
#                 url_obj = urlparse(supabase_credentials['supabase_url'])
#                 hostname = url_obj.hostname
#                 if hostname and 'supabase.co' in hostname:
#                     supabase_credentials['host'] = hostname.replace('supabase.co', 'supabase.co').replace('https://', 'db.')
#             except:
#                 pass
        
#         try:
#             schema_context = ai_handler.get_schema_context('supabase', supabase_credentials)
            
#             if "PostgreSQL support not available" in schema_context:
#                 session.clear()
#                 session['db_type'] = 'supabase'
#                 session['db_credentials'] = supabase_credentials
#                 session['connection_status'] = 'connected_demo'
#                 session['schema_context'] = "Demo mode - PostgreSQL support not fully available"
#                 session.modified = True
#                 return redirect(url_for('query_interface'))
#             elif "Error fetching schema" in schema_context or "failed" in schema_context.lower():
#                 return render_template('connect_supabase.html', error=f"Connection failed: {schema_context}")
            
#             session.clear()
#             session['db_type'] = 'supabase'
#             session['db_credentials'] = supabase_credentials
#             session['connection_status'] = 'connected'
#             session['schema_context'] = schema_context
#             session.modified = True
            
#             return redirect(url_for('query_interface'))
            
#         except Exception as e:
#             error_msg = str(e)
#             if "connection" in error_msg.lower() and "failed" in error_msg.lower():
#                 return render_template('connect_supabase.html', error="Cannot connect to Supabase. Check your Project URL, API Key, and Database Password.")
#             elif "authentication" in error_msg.lower():
#                 return render_template('connect_supabase.html', error="Authentication failed. Check your Database Password and API Key.")
#             else:
#                 return render_template('connect_supabase.html', error=f"Connection failed: {error_msg}")
    
#     return render_template('connect_supabase.html')

# @app.route('/connect/firebase', methods=['GET'])
# def connect_firebase():
#     """Firebase connection page"""
#     clear_previous_connections()
#     return render_template('connect_firebase.html')

# @app.route('/demo')
# def demo_mode():
#     """Demo mode without real database connection"""
#     clear_previous_connections()
#     session['db_type'] = 'demo'
#     session['db_credentials'] = {'mode': 'demo'}
#     session['connection_status'] = 'demo'
#     session['schema_context'] = ai_handler.get_schema_context('demo', {})
#     session.modified = True
#     return redirect(url_for('query_interface'))

# @app.route('/query')
# def query_interface():
#     """Main query interface"""
#     print(f"DEBUG: Query interface - Session: {dict(session)}")
    
#     if 'db_type' not in session:
#         return redirect(url_for('index'))
    
#     if 'schema_context' not in session:
#         try:
#             if session['db_type'] == 'firebase' and 'firebase_schema_data' in session:
#                 firebase_json = json.loads(session['db_credentials'].get('service_account_json', '{}'))
#                 project_id = firebase_json.get('project_id', 'Unknown')
#                 session['schema_context'] = format_firebase_schema(session['firebase_schema_data'], project_id)
#             else:
#                 session['schema_context'] = ai_handler.get_schema_context(
#                     session['db_type'], 
#                     session.get('db_credentials', {})
#                 )
#             session.modified = True
#         except Exception as e:
#             session['schema_context'] = f"Unable to fetch schema: {str(e)}"
#             session.modified = True
    
#     return render_template('query_interface.html')

# # API Endpoints

# @app.route('/api/generate-query', methods=['POST'])
# def generate_query():
#     """API endpoint to generate SQL query using AI"""
#     print(f"DEBUG: Generate query - Session: {dict(session)}")
    
#     if 'db_type' not in session:
#         return jsonify({'error': 'No database connection. Please connect to a database first.'}), 400
    
#     # For Firebase, check if we have proper connection data
#     if session['db_type'] == 'firebase':
#         if 'db_credentials' not in session or not session['db_credentials']:
#             return jsonify({'error': 'Firebase connection not properly established. Please reconnect.'}), 400
        
#         # Ensure we have schema data using cache
#         connection_id = session.get('connection_id')
#         if connection_id:
#             schema_data, schema_context = ai_handler.schema_cache.get_schema(connection_id)
#             if schema_data and schema_context:
#                 session['firebase_schema_data'] = schema_data
#                 session['schema_context'] = schema_context
#                 session.modified = True
#                 print(f"DEBUG: Using cached schema for connection: {connection_id}")
#             else:
#                 # Load schema if not in cache
#                 try:
#                     firebase_json = json.loads(session['db_credentials'].get('service_account_json', '{}'))
#                     success, message, schema_data = testfirebase.connect_and_load_schema(firebase_json)
#                     if success:
#                         project_id = firebase_json.get('project_id', 'Unknown')
#                         schema_context = format_firebase_schema(schema_data, project_id)
#                         # Store in cache
#                         ai_handler.schema_cache.store_schema(connection_id, schema_data, schema_context)
#                         session['firebase_schema_data'] = schema_data
#                         session['schema_context'] = schema_context
#                         session.modified = True
#                         print(f"DEBUG: Loaded fresh schema and cached it for connection: {connection_id}")
#                     else:
#                         return jsonify({'error': f'Firebase schema loading failed: {message}'}), 500
#                 except Exception as e:
#                     return jsonify({'error': f'Firebase connection issue: {str(e)}'}), 500
    
#     data = request.get_json()
#     if not data:
#         return jsonify({'error': 'No JSON data provided'}), 400
        
#     user_prompt = data.get('prompt')
    
#     if not user_prompt:
#         return jsonify({'error': 'No prompt provided'}), 400
    
#     try:
#         # Use cached schema context if available
#         if 'schema_context' not in session:
#             if session['db_type'] == 'firebase' and 'firebase_schema_data' in session:
#                 firebase_json = json.loads(session['db_credentials'].get('service_account_json', '{}'))
#                 project_id = firebase_json.get('project_id', 'Unknown')
#                 session['schema_context'] = format_firebase_schema(session['firebase_schema_data'], project_id)
#             else:
#                 session['schema_context'] = ai_handler.get_schema_context(
#                     session['db_type'], 
#                     session.get('db_credentials', {})
#                 )
#             session.modified = True
        
#         # Pass connection_id for Firebase
#         connection_id = session.get('connection_id')
#         generated_query = ai_handler.generate_query(
#             db_type=session['db_type'],
#             db_credentials=session['db_credentials'],
#             user_prompt=user_prompt,
#             gemini_api_key=config.GEMINI_API_KEY,
#             connection_id=connection_id
#         )
        
#         return jsonify({'query': generated_query})
    
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

# @app.route('/api/execute-query', methods=['POST'])
# def execute_query():
#     """API endpoint to execute the generated query"""
#     print(f"DEBUG: Execute query - Session: {dict(session)}")
    
#     if 'db_type' not in session:
#         return jsonify({'error': 'No database connection. Please connect to a database first.'}), 400
    
#     data = request.get_json()
#     if not data:
#         return jsonify({'error': 'No JSON data provided'}), 400
        
#     query = data.get('query')
    
#     if not query:
#         return jsonify({'error': 'No query provided'}), 400
    
#     try:
#         start_time = time.time()
        
#         # Pass connection_id for Firebase
#         connection_id = session.get('connection_id')
#         result = ai_handler.execute_query(
#             db_type=session['db_type'],
#             db_credentials=session['db_credentials'],
#             query=query,
#             connection_id=connection_id
#         )
        
#         execution_time = time.time() - start_time
        
#         if 'error' in result:
#             return jsonify({'error': result['error']}), 500
#         else:
#             if isinstance(result, dict):
#                 result['execution_time'] = round(execution_time, 2)
#             return jsonify(result)
    
#     except Exception as e:
#         return jsonify({'error': f"Query execution failed: {str(e)}"}), 500

# @app.route('/api/get-schema')
# def get_schema():
#     """API endpoint to get current database schema"""
#     print(f"DEBUG: Get schema - Session: {dict(session)}")
    
#     if 'db_type' not in session:
#         return jsonify({'error': 'No database connection'}), 400
    
#     try:
#         if session['db_type'] == 'firebase':
#             connection_id = session.get('connection_id')
#             if connection_id:
#                 schema_data, schema_context = ai_handler.schema_cache.get_schema(connection_id)
#                 if schema_data and schema_context:
#                     return jsonify({'schema': schema_context})
            
#             # Fallback to loading from Firebase if not in cache
#             if 'db_credentials' in session and session['db_credentials']:
#                 firebase_json = json.loads(session['db_credentials'].get('service_account_json', '{}'))
#                 success, message, schema_data = testfirebase.connect_and_load_schema(firebase_json)
#                 if success:
#                     project_id = firebase_json.get('project_id', 'Unknown')
#                     schema_context = format_firebase_schema(schema_data, project_id)
                    
#                     # Store in cache if we have a connection_id
#                     if connection_id:
#                         ai_handler.schema_cache.store_schema(connection_id, schema_data, schema_context)
                    
#                     return jsonify({'schema': schema_context})
#                 else:
#                     return jsonify({'error': f"Error loading schema: {message}"})
#             else:
#                 return jsonify({'error': "No Firebase credentials available"})
#         else:
#             schema_context = ai_handler.get_schema_context(
#                 session['db_type'], 
#                 session.get('db_credentials', {})
#             )
#             return jsonify({'schema': schema_context})
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

# @app.route('/api/firebase/store-connection', methods=['POST'])
# def api_firebase_store_connection():
#     """API endpoint to store Firebase connection in session"""
#     print(f"DEBUG: Store connection - Session before: {dict(session)}")
    
#     try:
#         data = request.get_json()
        
#         if not data or 'service_account_json' not in data:
#             return jsonify({'success': False, 'error': 'No Firebase JSON provided'})
        
#         # Generate a connection ID for cache
#         connection_id = str(uuid.uuid4())
        
#         # Store in session
#         session['db_type'] = 'firebase'
#         session['db_credentials'] = {
#             'service_account_json': data['service_account_json']
#         }
#         session['connection_status'] = 'connected'
#         session['connection_id'] = connection_id  # Store connection ID
        
#         # Store schema data in server cache instead of session
#         if 'schema_data' in data and data['schema_data']:
#             firebase_json = json.loads(data['service_account_json'])
#             project_id = firebase_json.get('project_id', 'Unknown')
#             formatted_schema = format_firebase_schema(data['schema_data'], project_id)
            
#             # Store in server cache
#             ai_handler.schema_cache.store_schema(
#                 connection_id, 
#                 data['schema_data'], 
#                 formatted_schema
#             )
#             session['schema_context'] = formatted_schema
        
#         # CRITICAL: Force session to be saved
#         session.modified = True
        
#         print(f"DEBUG: Store connection - Session after: {dict(session)}")
#         print(f"DEBUG: Connection ID generated: {connection_id}")
        
#         return jsonify({
#             'success': True, 
#             'message': 'Firebase connection stored successfully',
#             'connection_id': connection_id,
#             'schema': session.get('schema_context', 'Schema not available'),
#             'collections': list(data.get('schema_data', {}).keys()) if data.get('schema_data') else []
#         })
            
#     except Exception as e:
#         print(f"DEBUG: Store connection error: {str(e)}")
#         return jsonify({'success': False, 'error': f'Error storing connection: {str(e)}'})

# @app.route('/api/firebase/collections')
# def get_firebase_collections():
#     """API endpoint to get Firebase collections"""
#     print(f"DEBUG: Get collections - Session: {dict(session)}")
    
#     if 'db_type' not in session or session['db_type'] != 'firebase':
#         return jsonify({'success': False, 'error': 'Not connected to Firebase. Session db_type: ' + str(session.get('db_type'))}), 400
    
#     try:
#         connection_id = session.get('connection_id')
#         if connection_id:
#             schema_data, _ = ai_handler.schema_cache.get_schema(connection_id)
#             if schema_data:
#                 collections = list(schema_data.keys())
#                 return jsonify({'success': True, 'collections': collections})
        
#         # Fallback to loading from Firebase if not in cache
#         if 'db_credentials' in session and session['db_credentials']:
#             firebase_json = json.loads(session['db_credentials'].get('service_account_json', '{}'))
#             success, message, schema_data = testfirebase.connect_and_load_schema(firebase_json)
#             if success:
#                 # Store in cache
#                 if connection_id:
#                     project_id = firebase_json.get('project_id', 'Unknown')
#                     schema_context = format_firebase_schema(schema_data, project_id)
#                     ai_handler.schema_cache.store_schema(connection_id, schema_data, schema_context)
                
#                 collections = list(schema_data.keys())
#                 return jsonify({'success': True, 'collections': collections})
#             else:
#                 return jsonify({'success': False, 'error': f'Failed to load schema: {message}'})
        
#         return jsonify({'success': False, 'error': 'No Firebase credentials or schema data available in session'})
            
#     except Exception as e:
#         print(f"DEBUG: Get collections error: {str(e)}")
#         return jsonify({'success': False, 'error': f'Error loading collections: {str(e)}'}), 500

# @app.route('/test-connection', methods=['POST'])
# def test_connection():
#     """Test database connection without redirecting"""
#     data = request.get_json()
#     if not data:
#         return jsonify({'success': False, 'error': 'No JSON data provided'})
        
#     db_type = data.get('db_type')
#     credentials = data.get('credentials')
    
#     if not db_type or not credentials:
#         return jsonify({'success': False, 'error': 'Missing db_type or credentials'})
    
#     try:
#         if db_type == 'firebase':
#             if 'service_account_json' in credentials:
#                 try:
#                     firebase_json = json.loads(credentials['service_account_json'])
#                 except json.JSONDecodeError as e:
#                     return jsonify({'success': False, 'error': f'Invalid JSON format: {str(e)}'})
#             else:
#                 firebase_json = credentials
            
#             success, message, schema_data = testfirebase.connect_and_load_schema(firebase_json)
            
#             if success:
#                 schema_context = format_firebase_schema(schema_data, firebase_json.get('project_id', 'Unknown'))
#                 return jsonify({
#                     'success': True, 
#                     'message': 'Connection successful!', 
#                     'schema_preview': schema_context[:500] + '...' if len(schema_context) > 500 else schema_context,
#                     'schema_data': schema_data
#                 })
#             else:
#                 return jsonify({'success': False, 'error': message})
#         else:
#             schema_context = ai_handler.get_schema_context(db_type, credentials)
            
#             if "Error fetching schema" in schema_context or "failed" in schema_context.lower():
#                 return jsonify({'success': False, 'error': schema_context})
#             else:
#                 return jsonify({
#                     'success': True, 
#                     'message': 'Connection successful!', 
#                     'schema_preview': schema_context[:200] + '...'
#                 })
            
#     except Exception as e:
#         return jsonify({'success': False, 'error': str(e)})

# @app.route('/connection-status')
# def connection_status():
#     """Get current connection status"""
#     print(f"DEBUG: Connection status - Session: {dict(session)}")
    
#     if 'db_type' not in session:
#         return jsonify({'connected': False, 'session_keys': list(session.keys())})
    
#     status_info = {
#         'connected': True,
#         'db_type': session['db_type'],
#         'connection_status': session.get('connection_status', 'unknown'),
#         'schema_available': 'schema_context' in session,
#         'session_keys': list(session.keys()),
#         'connection_id': session.get('connection_id')  # Add connection_id to response
#     }
    
#     # Add Firebase-specific info
#     if session['db_type'] == 'firebase' and 'db_credentials' in session:
#         try:
#             firebase_json = json.loads(session['db_credentials'].get('service_account_json', '{}'))
#             status_info['project_id'] = firebase_json.get('project_id', 'Unknown')
            
#             # Get collections from cache
#             connection_id = session.get('connection_id')
#             if connection_id:
#                 schema_data, _ = ai_handler.schema_cache.get_schema(connection_id)
#                 if schema_data:
#                     status_info['collections'] = list(schema_data.keys())
#         except:
#             pass
    
#     return jsonify(status_info)

# @app.route('/disconnect')
# def disconnect():
#     """Clear session and disconnect from database"""
#     # Clear server cache if we have a connection_id
#     if 'connection_id' in session:
#         ai_handler.schema_cache.remove_schema(session['connection_id'])
    
#     session.clear()
#     return redirect(url_for('index'))

# # Debug routes
# @app.route('/debug/session')
# def debug_session():
#     """Show current session data"""
#     session_data = dict(session)
#     if 'db_credentials' in session_data:
#         session_data['db_credentials'] = {k: '***' if k in ['password', 'private_key', 'supabase_key'] else v 
#                                          for k, v in session_data['db_credentials'].items()}
#     return jsonify(session_data)

# @app.route('/debug/clear-session')
# def debug_clear_session():
#     """Debug route to clear session completely"""
#     # Clear server cache if we have a connection_id
#     if 'connection_id' in session:
#         ai_handler.schema_cache.remove_schema(session['connection_id'])
    
#     session.clear()
#     return jsonify({'message': 'Session cleared completely'})

# if __name__ == '__main__':
#     app.run(debug=True, host='0.0.0.0', port=5000)
from flask import Flask, render_template, session, request, jsonify, redirect, url_for
import config
from ai_handler import AIHandler
import json
import os
from urllib.parse import urlparse
import time
import testfirebase
from datetime import timedelta
import uuid

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'sql-sense-dev-key-2024')

# Enhanced session configuration
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_NAME'] = 'sql_sense_session'

# Initialize AI Handler
ai_handler = AIHandler()

def clear_previous_connections():
    """Clear any previous database connections and clean up resources"""
    session_keys_to_clear = ['db_type', 'db_credentials', 'connection_status', 'schema_context', 'firebase_schema_data', 'connection_id']
    for key in session_keys_to_clear:
        session.pop(key, None)
    session.modified = True

def format_firebase_schema(schema_data, project_id):
    """Convert Firebase schema data to readable string format"""
    if not schema_data:
        return "No schema data available"
    
    if not isinstance(schema_data, dict):
        return f"Schema data format issue: {type(schema_data)} - {str(schema_data)[:200]}"
    
    schema_info = ["🔥 Firebase Firestore Database Schema"]
    schema_info.append(f"Project: {project_id}")
    schema_info.append("=" * 60)
    
    collection_count = 0
    total_documents = 0
    
    for collection_name, documents in schema_data.items():
        collection_count += 1
        
        if not isinstance(documents, dict):
            schema_info.append(f"\n📁 Collection: {collection_name}")
            schema_info.append("-" * 40)
            schema_info.append(f"Unexpected data format: {type(documents)}")
            continue
            
        doc_count = len(documents)
        total_documents += doc_count
        
        schema_info.append(f"\n📁 Collection: {collection_name}")
        schema_info.append("-" * 40)
        schema_info.append(f"Documents: {doc_count}")
        
        sample_count = min(2, doc_count)
        if sample_count > 0:
            schema_info.append(f"Sample documents ({sample_count} of {doc_count}):")
            for i, (doc_id, doc_data) in enumerate(list(documents.items())[:sample_count]):
                schema_info.append(f"  📄 {doc_id}:")
                
                if isinstance(doc_data, dict):
                    for key, value in list(doc_data.items())[:3]:
                        value_str = str(value)
                        if len(value_str) > 50:
                            value_str = value_str[:50] + "..."
                        schema_info.append(f"    - {key}: {value_str}")
                else:
                    schema_info.append(f"    - Data: {str(doc_data)[:100]}...")
                    
                if i < sample_count - 1:
                    schema_info.append("")
    
    schema_info.append("=" * 60)
    schema_info.append(f"Total collections: {collection_count}")
    schema_info.append(f"Total documents: {total_documents}")
    
    if collection_count == 0:
        schema_info.append("\n⚠️ No collections found in the database.")
    
    return "\n".join(schema_info)

@app.before_request
def make_session_permanent():
    session.permanent = True

@app.route('/')
def index():
    """Home page - choose database type"""
    clear_previous_connections()
    return render_template('index.html')

@app.route('/connect/mysql', methods=['GET', 'POST'])
def connect_mysql():
    """MySQL connection form and handler"""
    clear_previous_connections()
    
    if request.method == 'POST':
        mysql_credentials = {
            'host': request.form.get('host', '').strip(),
            'user': request.form.get('user', '').strip(),
            'password': request.form.get('password', '').strip(),
            'database': request.form.get('database', '').strip(),
            'port': request.form.get('port', '3306').strip()
        }
        
        if not all([mysql_credentials['host'], mysql_credentials['user'], mysql_credentials['database']]):
            return render_template('connect_mysql.html', error="Please fill in all required fields")
        
        try:
            schema_context = ai_handler.get_schema_context('mysql', mysql_credentials)
            
            # Improved error handling with None checking
            if not schema_context:
                return render_template('connect_mysql.html', error="Connection failed: No response from database server")
            elif "Error fetching schema" in schema_context or "failed" in schema_context.lower():
                error_msg = schema_context
                # Clean up common error messages
                if "argument of type 'NoneType' is not iterable" in error_msg:
                    error_msg = "Database connection failed: Invalid database response. Please check if the database exists and is accessible."
                return render_template('connect_mysql.html', error=f"Connection failed: {error_msg}")
            
            session.clear()
            session['db_type'] = 'mysql'
            session['db_credentials'] = mysql_credentials
            session['connection_status'] = 'connected'
            session['schema_context'] = schema_context
            session.modified = True
            
            return redirect(url_for('query_interface'))
            
        except Exception as e:
            error_msg = str(e)
            # Handle the specific NoneType error
            if "argument of type 'NoneType' is not iterable" in error_msg:
                error_msg = "Database connection failed: Invalid response from database. Please verify your database exists and you have proper permissions."
            elif "Access denied" in error_msg:
                return render_template('connect_mysql.html', error="Access denied. Check username and password.")
            elif "Unknown database" in error_msg:
                return render_template('connect_mysql.html', error="Database does not exist. Please check the database name.")
            elif "Can't connect" in error_msg:
                return render_template('connect_mysql.html', error="Cannot connect to MySQL server. Check host, port, and ensure server is running.")
            else:
                return render_template('connect_mysql.html', error=f"Connection failed: {error_msg}")
    
    return render_template('connect_mysql.html')

@app.route('/connect/supabase', methods=['GET', 'POST'])
def connect_supabase():
    """Supabase connection form and handler"""
    clear_previous_connections()
    
    if request.method == 'POST':
        supabase_credentials = {
            'supabase_url': request.form.get('supabase_url', '').strip(),
            'supabase_key': request.form.get('supabase_key', '').strip(),
            'database_password': request.form.get('database_password', '').strip(),
            'host': request.form.get('host', '').strip() or 'db.your-project-ref.supabase.co',
            'port': request.form.get('port', '5432').strip(),
            'database': request.form.get('database', 'postgres').strip(),
            'user': request.form.get('user', 'postgres').strip()
        }
        
        if not all([supabase_credentials['supabase_url'], supabase_credentials['supabase_key'], supabase_credentials['database_password']]):
            return render_template('connect_supabase.html', error="Please fill in all required fields")
        
        if not supabase_credentials['host'] or supabase_credentials['host'] == 'db.your-project-ref.supabase.co':
            try:
                url_obj = urlparse(supabase_credentials['supabase_url'])
                hostname = url_obj.hostname
                if hostname and 'supabase.co' in hostname:
                    supabase_credentials['host'] = hostname.replace('supabase.co', 'supabase.co').replace('https://', 'db.')
            except:
                pass
        
        try:
            schema_context = ai_handler.get_schema_context('supabase', supabase_credentials)
            
            if "PostgreSQL support not available" in schema_context:
                session.clear()
                session['db_type'] = 'supabase'
                session['db_credentials'] = supabase_credentials
                session['connection_status'] = 'connected_demo'
                session['schema_context'] = "Demo mode - PostgreSQL support not fully available"
                session.modified = True
                return redirect(url_for('query_interface'))
            elif "Error fetching schema" in schema_context or "failed" in schema_context.lower():
                return render_template('connect_supabase.html', error=f"Connection failed: {schema_context}")
            
            session.clear()
            session['db_type'] = 'supabase'
            session['db_credentials'] = supabase_credentials
            session['connection_status'] = 'connected'
            session['schema_context'] = schema_context
            session.modified = True
            
            return redirect(url_for('query_interface'))
            
        except Exception as e:
            error_msg = str(e)
            if "connection" in error_msg.lower() and "failed" in error_msg.lower():
                return render_template('connect_supabase.html', error="Cannot connect to Supabase. Check your Project URL, API Key, and Database Password.")
            elif "authentication" in error_msg.lower():
                return render_template('connect_supabase.html', error="Authentication failed. Check your Database Password and API Key.")
            else:
                return render_template('connect_supabase.html', error=f"Connection failed: {error_msg}")
    
    return render_template('connect_supabase.html')

@app.route('/connect/firebase', methods=['GET'])
def connect_firebase():
    """Firebase connection page"""
    clear_previous_connections()
    return render_template('connect_firebase.html')

@app.route('/demo')
def demo_mode():
    """Demo mode without real database connection"""
    clear_previous_connections()
    session['db_type'] = 'demo'
    session['db_credentials'] = {'mode': 'demo'}
    session['connection_status'] = 'demo'
    session['schema_context'] = ai_handler.get_schema_context('demo', {})
    session.modified = True
    return redirect(url_for('query_interface'))

@app.route('/query')
def query_interface():
    """Main query interface"""
    print(f"DEBUG: Query interface - Session: {dict(session)}")
    
    if 'db_type' not in session:
        return redirect(url_for('index'))
    
    if 'schema_context' not in session:
        try:
            if session['db_type'] == 'firebase' and 'firebase_schema_data' in session:
                firebase_json = json.loads(session['db_credentials'].get('service_account_json', '{}'))
                project_id = firebase_json.get('project_id', 'Unknown')
                session['schema_context'] = format_firebase_schema(session['firebase_schema_data'], project_id)
            else:
                session['schema_context'] = ai_handler.get_schema_context(
                    session['db_type'], 
                    session.get('db_credentials', {})
                )
            session.modified = True
        except Exception as e:
            session['schema_context'] = f"Unable to fetch schema: {str(e)}"
            session.modified = True
    
    return render_template('query_interface.html')

# API Endpoints

@app.route('/api/generate-query', methods=['POST'])
def generate_query():
    """API endpoint to generate SQL query using AI"""
    print(f"DEBUG: Generate query - Session: {dict(session)}")
    
    if 'db_type' not in session:
        return jsonify({'error': 'No database connection. Please connect to a database first.'}), 400
    
    # For Firebase, check if we have proper connection data
    if session['db_type'] == 'firebase':
        if 'db_credentials' not in session or not session['db_credentials']:
            return jsonify({'error': 'Firebase connection not properly established. Please reconnect.'}), 400
        
        # Ensure we have schema data using cache
        connection_id = session.get('connection_id')
        if connection_id:
            schema_data, schema_context = ai_handler.schema_cache.get_schema(connection_id)
            if schema_data and schema_context:
                session['firebase_schema_data'] = schema_data
                session['schema_context'] = schema_context
                session.modified = True
                print(f"DEBUG: Using cached schema for connection: {connection_id}")
            else:
                # Load schema if not in cache
                try:
                    firebase_json = json.loads(session['db_credentials'].get('service_account_json', '{}'))
                    success, message, schema_data = testfirebase.connect_and_load_schema(firebase_json)
                    if success:
                        project_id = firebase_json.get('project_id', 'Unknown')
                        schema_context = format_firebase_schema(schema_data, project_id)
                        # Store in cache
                        ai_handler.schema_cache.store_schema(connection_id, schema_data, schema_context)
                        session['firebase_schema_data'] = schema_data
                        session['schema_context'] = schema_context
                        session.modified = True
                        print(f"DEBUG: Loaded fresh schema and cached it for connection: {connection_id}")
                    else:
                        return jsonify({'error': f'Firebase schema loading failed: {message}'}), 500
                except Exception as e:
                    return jsonify({'error': f'Firebase connection issue: {str(e)}'}), 500
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400
        
    user_prompt = data.get('prompt')
    
    if not user_prompt:
        return jsonify({'error': 'No prompt provided'}), 400
    
    try:
        # Use cached schema context if available
        if 'schema_context' not in session:
            if session['db_type'] == 'firebase' and 'firebase_schema_data' in session:
                firebase_json = json.loads(session['db_credentials'].get('service_account_json', '{}'))
                project_id = firebase_json.get('project_id', 'Unknown')
                session['schema_context'] = format_firebase_schema(session['firebase_schema_data'], project_id)
            else:
                session['schema_context'] = ai_handler.get_schema_context(
                    session['db_type'], 
                    session.get('db_credentials', {})
                )
            session.modified = True
        
        # Pass connection_id for Firebase
        connection_id = session.get('connection_id')
        generated_query = ai_handler.generate_query(
            db_type=session['db_type'],
            db_credentials=session['db_credentials'],
            user_prompt=user_prompt,
            gemini_api_key=config.GEMINI_API_KEY,
            connection_id=connection_id
        )
        
        return jsonify({'query': generated_query})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/execute-query', methods=['POST'])
def execute_query():
    """API endpoint to execute the generated query"""
    print(f"DEBUG: Execute query - Session: {dict(session)}")
    
    if 'db_type' not in session:
        return jsonify({'error': 'No database connection. Please connect to a database first.'}), 400
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data provided'}), 400
        
    query = data.get('query')
    
    if not query:
        return jsonify({'error': 'No query provided'}), 400
    
    try:
        start_time = time.time()
        
        # Pass connection_id for Firebase
        connection_id = session.get('connection_id')
        result = ai_handler.execute_query(
            db_type=session['db_type'],
            db_credentials=session['db_credentials'],
            query=query,
            connection_id=connection_id
        )
        
        execution_time = time.time() - start_time
        
        if 'error' in result:
            return jsonify({'error': result['error']}), 500
        else:
            if isinstance(result, dict):
                result['execution_time'] = round(execution_time, 2)
            return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': f"Query execution failed: {str(e)}"}), 500

@app.route('/api/get-schema')
def get_schema():
    """API endpoint to get current database schema"""
    print(f"DEBUG: Get schema - Session: {dict(session)}")
    
    if 'db_type' not in session:
        return jsonify({'error': 'No database connection'}), 400
    
    try:
        if session['db_type'] == 'firebase':
            connection_id = session.get('connection_id')
            if connection_id:
                schema_data, schema_context = ai_handler.schema_cache.get_schema(connection_id)
                if schema_data and schema_context:
                    return jsonify({'schema': schema_context})
            
            # Fallback to loading from Firebase if not in cache
            if 'db_credentials' in session and session['db_credentials']:
                firebase_json = json.loads(session['db_credentials'].get('service_account_json', '{}'))
                success, message, schema_data = testfirebase.connect_and_load_schema(firebase_json)
                if success:
                    project_id = firebase_json.get('project_id', 'Unknown')
                    schema_context = format_firebase_schema(schema_data, project_id)
                    
                    # Store in cache if we have a connection_id
                    if connection_id:
                        ai_handler.schema_cache.store_schema(connection_id, schema_data, schema_context)
                    
                    return jsonify({'schema': schema_context})
                else:
                    return jsonify({'error': f"Error loading schema: {message}"})
            else:
                return jsonify({'error': "No Firebase credentials available"})
        else:
            schema_context = ai_handler.get_schema_context(
                session['db_type'], 
                session.get('db_credentials', {})
            )
            return jsonify({'schema': schema_context})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/firebase/store-connection', methods=['POST'])
def api_firebase_store_connection():
    """API endpoint to store Firebase connection in session"""
    print(f"DEBUG: Store connection - Session before: {dict(session)}")
    
    try:
        data = request.get_json()
        
        if not data or 'service_account_json' not in data:
            return jsonify({'success': False, 'error': 'No Firebase JSON provided'})
        
        # Generate a connection ID for cache
        connection_id = str(uuid.uuid4())
        
        # Store in session
        session['db_type'] = 'firebase'
        session['db_credentials'] = {
            'service_account_json': data['service_account_json']
        }
        session['connection_status'] = 'connected'
        session['connection_id'] = connection_id  # Store connection ID
        
        # Store schema data in server cache instead of session
        if 'schema_data' in data and data['schema_data']:
            firebase_json = json.loads(data['service_account_json'])
            project_id = firebase_json.get('project_id', 'Unknown')
            formatted_schema = format_firebase_schema(data['schema_data'], project_id)
            
            # Store in server cache
            ai_handler.schema_cache.store_schema(
                connection_id, 
                data['schema_data'], 
                formatted_schema
            )
            session['schema_context'] = formatted_schema
        
        # CRITICAL: Force session to be saved
        session.modified = True
        
        print(f"DEBUG: Store connection - Session after: {dict(session)}")
        print(f"DEBUG: Connection ID generated: {connection_id}")
        
        return jsonify({
            'success': True, 
            'message': 'Firebase connection stored successfully',
            'connection_id': connection_id,
            'schema': session.get('schema_context', 'Schema not available'),
            'collections': list(data.get('schema_data', {}).keys()) if data.get('schema_data') else []
        })
            
    except Exception as e:
        print(f"DEBUG: Store connection error: {str(e)}")
        return jsonify({'success': False, 'error': f'Error storing connection: {str(e)}'})

@app.route('/api/firebase/collections')
def get_firebase_collections():
    """API endpoint to get Firebase collections"""
    print(f"DEBUG: Get collections - Session: {dict(session)}")
    
    if 'db_type' not in session or session['db_type'] != 'firebase':
        return jsonify({'success': False, 'error': 'Not connected to Firebase. Session db_type: ' + str(session.get('db_type'))}), 400
    
    try:
        connection_id = session.get('connection_id')
        if connection_id:
            schema_data, _ = ai_handler.schema_cache.get_schema(connection_id)
            if schema_data:
                collections = list(schema_data.keys())
                return jsonify({'success': True, 'collections': collections})
        
        # Fallback to loading from Firebase if not in cache
        if 'db_credentials' in session and session['db_credentials']:
            firebase_json = json.loads(session['db_credentials'].get('service_account_json', '{}'))
            success, message, schema_data = testfirebase.connect_and_load_schema(firebase_json)
            if success:
                # Store in cache
                if connection_id:
                    project_id = firebase_json.get('project_id', 'Unknown')
                    schema_context = format_firebase_schema(schema_data, project_id)
                    ai_handler.schema_cache.store_schema(connection_id, schema_data, schema_context)
                
                collections = list(schema_data.keys())
                return jsonify({'success': True, 'collections': collections})
            else:
                return jsonify({'success': False, 'error': f'Failed to load schema: {message}'})
        
        return jsonify({'success': False, 'error': 'No Firebase credentials or schema data available in session'})
            
    except Exception as e:
        print(f"DEBUG: Get collections error: {str(e)}")
        return jsonify({'success': False, 'error': f'Error loading collections: {str(e)}'}), 500

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
        if db_type == 'firebase':
            if 'service_account_json' in credentials:
                try:
                    firebase_json = json.loads(credentials['service_account_json'])
                except json.JSONDecodeError as e:
                    return jsonify({'success': False, 'error': f'Invalid JSON format: {str(e)}'})
            else:
                firebase_json = credentials
            
            success, message, schema_data = testfirebase.connect_and_load_schema(firebase_json)
            
            if success:
                schema_context = format_firebase_schema(schema_data, firebase_json.get('project_id', 'Unknown'))
                return jsonify({
                    'success': True, 
                    'message': 'Connection successful!', 
                    'schema_preview': schema_context[:500] + '...' if len(schema_context) > 500 else schema_context,
                    'schema_data': schema_data
                })
            else:
                return jsonify({'success': False, 'error': message})
        else:
            schema_context = ai_handler.get_schema_context(db_type, credentials)
            
            # Improved None checking
            if schema_context is None:
                return jsonify({'success': False, 'error': 'Connection failed: No response from database server'})
            elif "Error fetching schema" in schema_context or "failed" in schema_context.lower():
                # Check for the specific NoneType error
                if "argument of type 'NoneType' is not iterable" in schema_context:
                    return jsonify({'success': False, 'error': 'Connection failed: Database connection succeeded but schema extraction failed. This may happen if the database is empty or the user doesn\'t have permissions to read the schema.'})
                return jsonify({'success': False, 'error': schema_context})
            else:
                return jsonify({
                    'success': True, 
                    'message': 'Connection successful!', 
                    'schema_preview': schema_context[:200] + '...' if schema_context and len(schema_context) > 200 else schema_context
                })
            
    except Exception as e:
        error_msg = str(e)
        # Handle the specific NoneType error
        if "argument of type 'NoneType' is not iterable" in error_msg:
            return jsonify({'success': False, 'error': 'Connection failed: Database connection succeeded but schema extraction failed. This may happen if the database is empty or the user doesn\'t have permissions to read the schema.'})
        return jsonify({'success': False, 'error': f'Connection test failed: {error_msg}'})

@app.route('/connection-status')
def connection_status():
    """Get current connection status"""
    print(f"DEBUG: Connection status - Session: {dict(session)}")
    
    if 'db_type' not in session:
        return jsonify({'connected': False, 'session_keys': list(session.keys())})
    
    status_info = {
        'connected': True,
        'db_type': session['db_type'],
        'connection_status': session.get('connection_status', 'unknown'),
        'schema_available': 'schema_context' in session,
        'session_keys': list(session.keys()),
        'connection_id': session.get('connection_id')  # Add connection_id to response
    }
    
    # Add Firebase-specific info
    if session['db_type'] == 'firebase' and 'db_credentials' in session:
        try:
            firebase_json = json.loads(session['db_credentials'].get('service_account_json', '{}'))
            status_info['project_id'] = firebase_json.get('project_id', 'Unknown')
            
            # Get collections from cache
            connection_id = session.get('connection_id')
            if connection_id:
                schema_data, _ = ai_handler.schema_cache.get_schema(connection_id)
                if schema_data:
                    status_info['collections'] = list(schema_data.keys())
        except:
            pass
    
    return jsonify(status_info)

@app.route('/disconnect')
def disconnect():
    """Clear session and disconnect from database"""
    # Clear server cache if we have a connection_id
    if 'connection_id' in session:
        ai_handler.schema_cache.remove_schema(session['connection_id'])
    
    session.clear()
    return redirect(url_for('index'))

# Debug routes
@app.route('/debug/session')
def debug_session():
    """Show current session data"""
    session_data = dict(session)
    if 'db_credentials' in session_data:
        session_data['db_credentials'] = {k: '***' if k in ['password', 'private_key', 'supabase_key'] else v 
                                         for k, v in session_data['db_credentials'].items()}
    return jsonify(session_data)

@app.route('/debug/clear-session')
def debug_clear_session():
    """Debug route to clear session completely"""
    # Clear server cache if we have a connection_id
    if 'connection_id' in session:
        ai_handler.schema_cache.remove_schema(session['connection_id'])
    
    session.clear()
    return jsonify({'message': 'Session cleared completely'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)