import mysql.connector
import firebase_admin
from firebase_admin import credentials, db
import json
import re
from typing import Dict, Any, List
import requests
from urllib.parse import urlparse

class AIHandler:
    def __init__(self):
        self.connections = {}
    
    def get_schema_context(self, db_type: str, db_credentials: Dict[str, Any]) -> str:
        """
        Connect to database and fetch schema information
        Returns formatted string of database schema
        """
        try:
            if db_type == 'mysql':
                return self._get_mysql_schema(db_credentials)
            elif db_type == 'supabase':
                return self._get_supabase_schema(db_credentials)
            elif db_type == 'firebase':
                return self._get_firebase_schema(db_credentials)
            elif db_type == 'demo':
                return self._get_demo_schema()
            else:
                raise ValueError(f"Unsupported database type: {db_type}")
        except Exception as e:
            return f"Error fetching schema: {str(e)}"
    
    def _get_mysql_schema(self, credentials: Dict[str, Any]) -> str:
        """Fetch MySQL schema information"""
        connection = None
        cursor = None
        try:
            connection = mysql.connector.connect(
                host=credentials['host'],
                port=int(credentials.get('port', 3306)),
                user=credentials['user'],
                password=credentials['password'],
                database=credentials['database']
            )
            
            cursor = connection.cursor()
            
            # Get table information
            cursor.execute("""
                SELECT TABLE_NAME, TABLE_COMMENT 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = %s
            """, (credentials['database'],))
            tables = cursor.fetchall()
            
            schema_info = [f"Database: {credentials['database']}"]
            
            if not tables:
                schema_info.append("No tables found in database")
            else:
                for table_name, table_comment in tables:
                    # Get column information for each table
                    cursor.execute("""
                        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_COMMENT
                        FROM INFORMATION_SCHEMA.COLUMNS 
                        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                        ORDER BY ORDINAL_POSITION
                    """, (credentials['database'], table_name))
                    columns = cursor.fetchall()
                    
                    table_schema = f"\nTable: {table_name}"
                    if table_comment:
                        table_schema += f" ({table_comment})"
                    table_schema += "\n"
                    
                    if not columns:
                        table_schema += "  No columns found\n"
                    else:
                        for col_name, data_type, is_nullable, col_default, col_comment in columns:
                            table_schema += f"  - {col_name} ({data_type})"
                            if is_nullable == 'NO':
                                table_schema += " NOT NULL"
                            if col_default:
                                table_schema += f" DEFAULT {col_default}"
                            if col_comment:
                                table_schema += f" COMMENT '{col_comment}'"
                            table_schema += "\n"
                    
                    schema_info.append(table_schema)
            
            return "\n".join(schema_info)
            
        except Exception as e:
            raise Exception(f"MySQL schema discovery failed: {str(e)}")
        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()
    
    def _get_supabase_schema(self, credentials: Dict[str, Any]) -> str:
        """Fetch Supabase (PostgreSQL) schema information using Supabase URL and API key"""
        try:
            # Try to import psycopg2, but provide fallback if not available
            try:
                import psycopg2
                
                # Extract host from Supabase URL or use provided host
                host = self._get_supabase_host(credentials)
                
                # Use standard Supabase connection parameters
                connection = psycopg2.connect(
                    host=host,
                    port=int(credentials.get('port', 5432)),
                    user=credentials.get('user', 'postgres'),
                    password=credentials.get('database_password', ''),
                    database=credentials.get('database', 'postgres'),
                    sslmode='require'  # Supabase requires SSL
                )
                
                cursor = connection.cursor()
                
                # Get table information
                cursor.execute("""
                    SELECT table_name, table_type 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """)
                tables = cursor.fetchall()
                
                schema_info = [f"Supabase Project: {credentials.get('supabase_url', 'Unknown')}"]
                
                if not tables:
                    schema_info.append("No tables found in database")
                else:
                    for table_name, table_type in tables:
                        # Get column information for each table
                        cursor.execute("""
                            SELECT column_name, data_type, is_nullable, column_default
                            FROM information_schema.columns 
                            WHERE table_schema = 'public' AND table_name = %s
                            ORDER BY ordinal_position
                        """, (table_name,))
                        columns = cursor.fetchall()
                        
                        table_schema = f"\nTable: {table_name} ({table_type})\n"
                        
                        if not columns:
                            table_schema += "  No columns found\n"
                        else:
                            for col_name, data_type, is_nullable, col_default in columns:
                                table_schema += f"  - {col_name} ({data_type})"
                                if is_nullable == 'NO':
                                    table_schema += " NOT NULL"
                                if col_default:
                                    table_schema += f" DEFAULT {col_default}"
                                table_schema += "\n"
                        
                        schema_info.append(table_schema)
                
                cursor.close()
                connection.close()
                
                return "\n".join(schema_info)
                
            except ImportError:
                return "PostgreSQL support not available. Please install psycopg2 for full Supabase support."
            
        except Exception as e:
            error_msg = str(e)
            if "connection" in error_msg.lower():
                return f"Could not connect to Supabase. Please check your credentials and ensure the database is running. Error: {error_msg}"
            elif "authentication" in error_msg.lower():
                return f"Authentication failed. Please check your database password. Error: {error_msg}"
            else:
                return f"Supabase schema discovery failed: {error_msg}"
    
    def _get_supabase_host(self, credentials: Dict[str, Any]) -> str:
        """Extract database host from Supabase URL"""
        # If host is explicitly provided, use it
        if credentials.get('host') and credentials['host'] != 'db.your-project-ref.supabase.co':
            return credentials['host']
        
        # Otherwise, generate from Supabase URL
        supabase_url = credentials.get('supabase_url', '')
        if supabase_url and 'supabase.co' in supabase_url:
            try:
                url_obj = urlparse(supabase_url)
                hostname = url_obj.hostname
                if hostname:
                    # Convert project URL to database host
                    # Format: https://project-ref.supabase.co -> db.project-ref.supabase.co
                    return f"db.{hostname}"
            except Exception as e:
                print(f"Error parsing Supabase URL: {e}")
        
        # Fallback to default or provided host
        return credentials.get('host', 'db.project-ref.supabase.co')
    
    def _get_firebase_schema(self, credentials: Dict[str, Any]) -> str:
        """Fetch Firebase collections structure"""
        try:
            # Initialize Firebase app
            service_account_info = json.loads(credentials['service_account_key'])
            firebase_cred = credentials.Certificate(service_account_info)
            
            if not firebase_admin._apps:
                firebase_admin.initialize_app(firebase_cred, {
                    'databaseURL': credentials['database_url']
                })
            
            # Get root reference
            root_ref = db.reference('/')
            root_data = root_ref.get(limit=10)  # Limit for initial discovery
            
            schema_info = ["Firebase Database Structure:"]
            
            def explore_structure(data, path="", depth=0):
                if isinstance(data, dict):
                    for key, value in data.items():
                        new_path = f"{path}/{key}" if path else key
                        indent = "  " * depth
                        if isinstance(value, dict):
                            schema_info.append(f"{indent}📁 {key}/ (collection)")
                            explore_structure(value, new_path, depth + 1)
                        else:
                            value_type = type(value).__name__
                            schema_info.append(f"{indent}📄 {key}: {value_type}")
                elif data is not None:
                    schema_info.append(f"{indent}📄 (value): {type(data).__name__}")
            
            explore_structure(root_data)
            
            return "\n".join(schema_info) if len(schema_info) > 1 else "No data found in Firebase"
            
        except Exception as e:
            raise Exception(f"Firebase structure discovery failed: {str(e)}")
    
    def _get_demo_schema(self) -> str:
        """Return demo schema for testing"""
        return """
Demo Database Schema:

Users Table:
- id (INT, PRIMARY KEY)
- username (VARCHAR)
- email (VARCHAR)
- created_at (DATETIME)
- status (VARCHAR)

Products Table:
- id (INT, PRIMARY KEY)
- name (VARCHAR)
- price (DECIMAL)
- category (VARCHAR)
- stock_quantity (INT)

Orders Table:
- id (INT, PRIMARY KEY)
- user_id (INT, FOREIGN KEY)
- product_id (INT, FOREIGN KEY)
- quantity (INT)
- order_date (DATETIME)
- status (VARCHAR)

Students Table:
- id (INT, PRIMARY KEY)
- first_name (VARCHAR)
- last_name (VARCHAR)
- age (INT)
- grade (VARCHAR)
- email (VARCHAR)

Clubs Table:
- id (INT, PRIMARY KEY)
- name (VARCHAR)
- description (TEXT)
- created_at (DATETIME)
- member_count (INT)
"""
    
    def generate_query(self, db_type: str, db_credentials: Dict[str, Any], user_prompt: str, gemini_api_key: str) -> str:
        """
        Generate SQL/NoSQL query using Gemini AI with direct API calls
        """
        try:
            # Get schema context
            schema_context = self.get_schema_context(db_type, db_credentials)
            
            # Create system prompt
            system_prompt = self._create_system_prompt(db_type, schema_context)
            
            # Use the available models from your account
            model_names = [
                'gemini-2.0-flash-001',  # Fast and reliable
                'gemini-2.0-flash',      # Alternative flash model
                'gemini-2.0-flash-exp',  # Experimental flash
                'gemini-pro-latest',     # Latest pro model
            ]
            
            last_error = None
            
            for model_name in model_names:
                try:
                    print(f"Trying Gemini model: {model_name}")
                    result = self._call_gemini_api(
                        api_key=gemini_api_key,
                        model_name=model_name,
                        system_prompt=system_prompt,
                        user_prompt=user_prompt
                    )
                    print(f"Success with model: {model_name}")
                    
                    # Clean the generated query before returning
                    cleaned_query = self._clean_generated_query(result)
                    return cleaned_query
                    
                except Exception as e:
                    last_error = e
                    print(f"Model {model_name} failed: {str(e)}")
                    continue
            
            # If all models fail, provide helpful error
            raise Exception(f"All model attempts failed. Last error: {str(last_error)}\nTry using one of these models: gemini-2.0-flash-001, gemini-2.0-flash, or gemini-pro-latest")
            
        except Exception as e:
            raise Exception(f"Query generation failed: {str(e)}")
    
    def _clean_generated_query(self, query: str) -> str:
        """
        Clean the generated query by removing markdown formatting, code blocks, and extra characters
        """
        if not query:
            return query
            
        # Remove markdown code blocks (```sql, ```, ~sql, etc.)
        query = re.sub(r'^```\w*\s*', '', query)  # Remove starting ```sql or ```
        query = re.sub(r'^~sql\s*', '', query)    # Remove starting ~sql
        query = re.sub(r'```\s*$', '', query)     # Remove ending ```
        query = re.sub(r'^"|"$', '', query)       # Remove surrounding quotes
        
        # Remove common markdown artifacts
        query = re.sub(r'^\s*SELECT', 'SELECT', query, flags=re.IGNORECASE)
        query = re.sub(r';\s*$', '', query)  # Remove trailing semicolon if present
        
        # Strip whitespace
        query = query.strip()
        
        # Ensure it starts with a valid SQL keyword
        sql_keywords = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP']
        if not any(query.upper().startswith(keyword) for keyword in sql_keywords):
            # If it doesn't start with a SQL keyword, try to extract the SQL part
            lines = query.split('\n')
            for i, line in enumerate(lines):
                if any(line.strip().upper().startswith(keyword) for keyword in sql_keywords):
                    # Found SQL, take from this line onward
                    query = '\n'.join(lines[i:])
                    break
        
        print(f"Cleaned query: {query}")
        return query
    
    def _call_gemini_api(self, api_key: str, model_name: str, system_prompt: str, user_prompt: str) -> str:
        """Make direct API call to Gemini"""
        # Remove 'models/' prefix if present
        if model_name.startswith('models/'):
            model_name = model_name.replace('models/', '')
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        
        # Create a more strict prompt to prevent markdown
        strict_prompt = f"""{system_prompt}

User Request: {user_prompt}

Generate ONLY the raw SQL query without any markdown, code blocks, or explanations:"""
        
        # Prepare the request payload
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": strict_prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 1024,
            }
        }
        
        # For newer models that support system instructions
        if any(x in model_name for x in ['flash', 'pro']):
            payload["systemInstruction"] = {
                "parts": [{"text": system_prompt + "\n\nIMPORTANT: Return ONLY the raw SQL query without any markdown formatting, code blocks, backticks, or explanations."}]
            }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        print(f"Calling Gemini API with model: {model_name}")
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if 'candidates' in data and len(data['candidates']) > 0:
                return data['candidates'][0]['content']['parts'][0]['text']
            else:
                raise Exception("No response generated from Gemini")
        else:
            error_msg = f"API Error {response.status_code}: {response.text}"
            raise Exception(error_msg)
    
    def _create_system_prompt(self, db_type: str, schema_context: str) -> str:
        """
        Create detailed system prompt for Gemini based on database type and schema
        """
        if db_type == 'mysql':
            db_specific = """
            For MySQL:
            - Use backticks for table and column names if they contain special characters
            - Use NOW() for current timestamp
            - Use LIMIT for row limiting
            - Use IFNULL() or COALESCE() for null handling
            """
        elif db_type == 'supabase':
            db_specific = """
            For Supabase (PostgreSQL):
            - Use double quotes for table and column names if they contain special characters
            - Use CURRENT_TIMESTAMP for current timestamp
            - Use LIMIT for row limiting
            - Use COALESCE() for null handling
            - Use ILIKE for case-insensitive pattern matching
            """
        elif db_type == 'firebase':
            db_specific = """
            For Firebase (NoSQL):
            - Generate JavaScript-like syntax for Firebase queries
            - Use orderByChild(), orderByKey(), orderByValue() for sorting
            - Use equalTo(), startAt(), endAt() for filtering
            - Use limitToFirst(), limitToLast() for limiting results
            - Remember Firebase uses JSON-like structure with collections and documents
            """
        elif db_type == 'demo':
            db_specific = """
            For Demo Mode (MySQL-like syntax):
            - Use standard SQL syntax
            - Assume MySQL compatibility
            - Generate readable, example queries
            """
        else:
            db_specific = ""
        
        return f"""
        You are an expert {db_type.upper()} database assistant. Your task is to generate accurate, efficient, and secure database queries based on the user's natural language requests.

        DATABASE SCHEMA CONTEXT:
        {schema_context}

        {db_specific}

        CRITICAL INSTRUCTIONS:
        1. Generate ONLY the raw SQL query code - no explanations, no markdown formatting, no code blocks, no backticks
        2. Ensure the query is syntactically correct for the target database
        3. Use appropriate functions and syntax for the specific database type
        4. Include proper WHERE clauses for filtering when requested
        5. Use appropriate JOINs when multiple tables are involved
        6. Always include sensible ordering when displaying lists of data
        7. For aggregation queries, use appropriate GROUP BY clauses
        8. Make the query efficient and production-ready
        9. DO NOT wrap the query in markdown code blocks (no ```sql, no ```, no ~sql)
        10. DO NOT add any explanations or comments
        11. ONLY use tables and columns that exist in the provided schema context

        EXAMPLES:
        User: "Show me all active users"
        Response: SELECT * FROM users WHERE status = 'active' ORDER BY created_at DESC

        User: "Count orders by status"
        Response: SELECT status, COUNT(*) as order_count FROM orders GROUP BY status ORDER BY order_count DESC

        User: "Find products with price over $100"
        Response: SELECT * FROM products WHERE price > 100 ORDER BY price DESC

        User: "name from students"
        Response: SELECT name FROM students

        User: "show all clubs"
        Response: SELECT * FROM clubs

        IMPORTANT: Return ONLY the raw SQL query code, nothing else.
        """
    
    def execute_query(self, db_type: str, db_credentials: Dict[str, Any], query: str) -> Dict[str, Any]:
        """
        Execute the generated query against the database
        """
        try:
            # Clean the query before execution (in case it wasn't cleaned properly)
            cleaned_query = self._clean_generated_query(query)
            print(f"Executing cleaned query: {cleaned_query}")
            
            if db_type == 'mysql':
                return self._execute_mysql_query(db_credentials, cleaned_query)
            elif db_type == 'supabase':
                return self._execute_supabase_query(db_credentials, cleaned_query)
            elif db_type == 'firebase':
                return self._execute_firebase_query(db_credentials, cleaned_query)
            elif db_type == 'demo':
                return self._execute_demo_query(cleaned_query)
            else:
                return {"error": f"Unsupported database type: {db_type}"}
        except Exception as e:
            return {"error": f"Query execution failed: {str(e)}"}
    
    def _execute_mysql_query(self, credentials: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Execute MySQL query"""
        connection = None
        cursor = None
        try:
            connection = mysql.connector.connect(
                host=credentials['host'],
                port=int(credentials.get('port', 3306)),
                user=credentials['user'],
                password=credentials['password'],
                database=credentials['database']
            )
            
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query)
            
            if query.strip().upper().startswith('SELECT'):
                result = cursor.fetchall()
            else:
                connection.commit()
                result = [{"affected_rows": cursor.rowcount, "message": "Query executed successfully"}]
            
            return {"data": result}
            
        except Exception as e:
            raise Exception(f"MySQL query execution failed: {str(e)}")
        finally:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()
    
    def _execute_supabase_query(self, credentials: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Execute Supabase (PostgreSQL) query using Supabase URL and API key"""
        try:
            # Try to use psycopg2 if available
            try:
                import psycopg2
                
                # Extract host from Supabase URL or use provided host
                host = self._get_supabase_host(credentials)
                
                # Use standard Supabase connection parameters
                connection = psycopg2.connect(
                    host=host,
                    port=int(credentials.get('port', 5432)),
                    user=credentials.get('user', 'postgres'),
                    password=credentials.get('database_password', ''),
                    database=credentials.get('database', 'postgres'),
                    sslmode='require'  # Supabase requires SSL
                )
                
                cursor = connection.cursor()
                cursor.execute(query)
                
                if query.strip().upper().startswith('SELECT'):
                    # Get column names
                    columns = [desc[0] for desc in cursor.description]
                    result = [dict(zip(columns, row)) for row in cursor.fetchall()]
                else:
                    connection.commit()
                    result = [{"affected_rows": cursor.rowcount, "message": "Query executed successfully"}]
                
                cursor.close()
                connection.close()
                
                return {"data": result}
                
            except ImportError:
                return {"data": [{"message": "PostgreSQL support not available. Install psycopg2 for full functionality.", "query": query}]}
            
        except Exception as e:
            error_msg = str(e)
            # Provide more user-friendly error messages for common PostgreSQL errors
            if "relation" in error_msg and "does not exist" in error_msg:
                # Extract table name from error message
                table_match = re.search(r'relation "([^"]+)" does not exist', error_msg)
                if table_match:
                    table_name = table_match.group(1)
                    raise Exception(f"Table '{table_name}' does not exist in your database. Please check the table name or create the table first.")
                else:
                    raise Exception(f"Table does not exist in your database. Please check your query and ensure all tables exist.")
            elif "relation" in error_msg and "already exists" in error_msg:
                table_match = re.search(r'relation "([^"]+)" already exists', error_msg)
                if table_match:
                    table_name = table_match.group(1)
                    raise Exception(f"Table '{table_name}' already exists. You cannot create a table with the same name.")
                else:
                    raise Exception(f"Table already exists. Please choose a different table name.")
            elif "column" in error_msg and "does not exist" in error_msg:
                column_match = re.search(r'column "([^"]+)" does not exist', error_msg)
                if column_match:
                    column_name = column_match.group(1)
                    raise Exception(f"Column '{column_name}' does not exist. Please check the column name in your query.")
                else:
                    raise Exception(f"Column does not exist. Please check your query.")
            elif "syntax error" in error_msg.lower():
                raise Exception(f"SQL syntax error in your query. Please check the query and try again.")
            elif "connection" in error_msg.lower():
                raise Exception(f"Could not connect to Supabase. Please check your credentials and ensure the database is running.")
            else:
                raise Exception(f"Supabase query execution failed: {error_msg}")
    
    def _execute_firebase_query(self, credentials: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Execute Firebase query"""
        try:
            # For Firebase, we'll need to parse and execute the JavaScript-like query
            # This is a simplified implementation - in production, you'd want more robust parsing
            
            # Initialize Firebase if not already done
            service_account_info = json.loads(credentials['service_account_key'])
            firebase_cred = credentials.Certificate(service_account_info)
            
            if not firebase_admin._apps:
                firebase_admin.initialize_app(firebase_cred, {
                    'databaseURL': credentials['database_url']
                })
            
            # Simple query execution for demonstration
            # In a real implementation, you'd parse the generated Firebase query syntax
            ref = db.reference('/')
            data = ref.get()
            
            return {"data": [{"firebase_data": data}] if data else []}
            
        except Exception as e:
            raise Exception(f"Firebase query execution failed: {str(e)}")
    
    def _execute_demo_query(self, query: str) -> Dict[str, Any]:
        """Execute demo query (simulated)"""
        # Convert query to lowercase for easier matching
        query_lower = query.lower().strip()
        
        # Remove semicolons and extra spaces
        query_clean = query_lower.replace(';', '').strip()
        
        print(f"Demo query: {query_clean}")  # Debug logging
        
        # Handle different query patterns
        if "clubs" in query_clean:
            return {
                "data": [
                    {"id": 1, "name": "Chess Club", "description": "Strategy and board games", "member_count": 25},
                    {"id": 2, "name": "Drama Club", "description": "Theater and performance arts", "member_count": 18},
                    {"id": 3, "name": "Science Club", "description": "STEM activities and experiments", "member_count": 32},
                    {"id": 4, "name": "Debate Club", "description": "Public speaking and arguments", "member_count": 22}
                ]
            }
        elif "students" in query_clean and "name" in query_clean:
            return {
                "data": [
                    {"name": "John Doe"},
                    {"name": "Jane Smith"},
                    {"name": "Bob Johnson"},
                    {"name": "Alice Brown"},
                    {"name": "Charlie Wilson"}
                ]
            }
        elif "students" in query_clean:
            return {
                "data": [
                    {"id": 1, "name": "John Doe", "age": 20, "grade": "A"},
                    {"id": 2, "name": "Jane Smith", "age": 21, "grade": "B"},
                    {"id": 3, "name": "Bob Johnson", "age": 19, "grade": "A"},
                    {"id": 4, "name": "Alice Brown", "age": 22, "grade": "C"},
                    {"id": 5, "name": "Charlie Wilson", "age": 20, "grade": "B"}
                ]
            }
        elif "users" in query_clean and "active" in query_clean:
            return {
                "data": [
                    {"id": 1, "username": "john_doe", "email": "john@example.com", "status": "active"},
                    {"id": 3, "username": "jane_smith", "email": "jane@example.com", "status": "active"}
                ]
            }
        elif "products" in query_clean and "price" in query_clean:
            return {
                "data": [
                    {"id": 1, "name": "Laptop", "price": 999.99, "category": "Electronics"},
                    {"id": 2, "name": "Phone", "price": 699.99, "category": "Electronics"},
                    {"id": 3, "name": "Tablet", "price": 399.99, "category": "Electronics"}
                ]
            }
        elif "select" in query_clean:
            # Generic SELECT query response
            return {
                "data": [
                    {"result": "Demo query executed successfully", "query": query},
                    {"note": "This is simulated data from demo mode"}
                ]
            }
        else:
            # For non-SELECT queries or unknown tables
            return {
                "data": [
                    {"message": "Query executed successfully in demo mode", "query": query},
                    {"affected_rows": 1, "status": "success"}
                ]
            }