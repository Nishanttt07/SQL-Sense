# ai_handler.py
import mysql.connector
import firebase_admin
from firebase_admin import credentials, firestore
import json
import re
from typing import Dict, Any, List, Tuple
import requests
from urllib.parse import urlparse
import google.generativeai as genai
import tempfile
import os
from datetime import datetime, timedelta
import uuid
import time
from difflib import SequenceMatcher

# Import the existing schema_cache from your separate file
from schema_cache import schema_cache

class AIHandler:
    def __init__(self):
        self.connections = {}
        # Reference the imported schema_cache
        self.schema_cache = schema_cache
    
    def get_schema_context(self, db_type: str, db_credentials: Dict[str, Any]) -> str:
        """
        Connect to database and fetch schema information
        Returns formatted string of database schema
        """
        try:
            print(f"DEBUG: Getting schema context for {db_type}")
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
            error_msg = f"Error fetching schema: {str(e)}"
            print(f"DEBUG: Schema context error: {error_msg}")
            return error_msg
    
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
    
    def _clean_for_json(self, obj):
        """Recursively converts Firestore data into JSON-safe format."""
        if isinstance(obj, dict):
            return {k: self._clean_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._clean_for_json(v) for v in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()  # convert datetime to string
        else:
            return obj

    def _format_minimal_firebase_schema(self, schema_data, project_id):
        """Create a minimal schema representation for session storage"""
        if not schema_data:
            return "No schema data available"
        
        if not isinstance(schema_data, dict):
            return f"Schema data format issue: {type(schema_data)}"
        
        schema_info = ["🔥 Firebase Firestore Database Schema"]
        schema_info.append(f"Project: {project_id}")
        schema_info.append("=" * 60)
        
        collection_count = 0
        total_documents = 0
        
        for collection_name, documents in schema_data.items():
            collection_count += 1
            doc_count = len(documents) if isinstance(documents, dict) else 0
            total_documents += doc_count
            
            schema_info.append(f"\n📁 Collection: {collection_name}")
            schema_info.append("-" * 40)
            schema_info.append(f"Documents: {doc_count}")
            
            # Show only field names, not data
            if doc_count > 0 and isinstance(documents, dict):
                sample_doc = next(iter(documents.values()))
                if isinstance(sample_doc, dict):
                    fields = list(sample_doc.keys())[:8]  # Show first 8 fields
                    schema_info.append(f"Fields ({len(fields)}): {', '.join(fields)}" + 
                                     ("..." if len(fields) > 8 else ""))
        
        schema_info.append("=" * 60)
        schema_info.append(f"Total collections: {collection_count}")
        schema_info.append(f"Total documents: {total_documents}")
        
        return "\n".join(schema_info)

    def _get_firebase_schema(self, db_credentials: Dict[str, Any]) -> str:
        """Fetch Firebase schema using testfirebase module with minimal representation"""
        try:
            # Import and use testfirebase module
            import testfirebase
            
            if 'service_account_json' in db_credentials and db_credentials['service_account_json']:
                try:
                    firebase_json = json.loads(db_credentials['service_account_json'])
                except json.JSONDecodeError as e:
                    return f"Invalid JSON format in service account: {str(e)}"
            else:
                # Build from individual fields
                firebase_json = {
                    "type": "service_account",
                    "project_id": db_credentials.get('project_id', ''),
                    "private_key": db_credentials.get('private_key', '').replace('\\n', '\n'),
                    "client_email": db_credentials.get('client_email', '')
                }
            
            print(f"DEBUG: Using testfirebase for Firebase schema - project: {firebase_json.get('project_id')}")
            success, message, schema_data = testfirebase.connect_and_load_schema(firebase_json)
            
            if success and schema_data:
                # Return minimal schema representation
                return self._format_minimal_firebase_schema(schema_data, firebase_json.get('project_id', 'Unknown'))
            else:
                return f"Error fetching Firebase schema: {message}"
                
        except Exception as e:
            error_msg = str(e)
            print(f"DEBUG: Firebase schema discovery failed: {error_msg}")
            return f"Error fetching Firebase schema: {error_msg}"

    def get_firebase_schema_with_cache(self, db_credentials: Dict[str, Any], connection_id: str = None):
        """
        Get Firebase schema with server-side caching support
        Returns: (schema_data, schema_context, connection_id)
        """
        try:
            import testfirebase
            
            if 'service_account_json' in db_credentials and db_credentials['service_account_json']:
                firebase_json = json.loads(db_credentials['service_account_json'])
            else:
                firebase_json = {
                    "type": "service_account",
                    "project_id": db_credentials.get('project_id', ''),
                    "private_key": db_credentials.get('private_key', '').replace('\\n', '\n'),
                    "client_email": db_credentials.get('client_email', '')
                }
            
            # Check cache first using the imported schema_cache
            if connection_id:
                schema_data, schema_context = self.schema_cache.get_schema(connection_id)
                if schema_data and schema_context:
                    print(f"DEBUG: Using cached schema for connection: {connection_id}")
                    return schema_data, schema_context, connection_id
            
            # Load schema from Firebase
            print(f"DEBUG: Loading schema from Firebase - project: {firebase_json.get('project_id')}")
            success, message, schema_data = testfirebase.connect_and_load_schema(firebase_json)
            
            if success and schema_data:
                schema_context = self._format_minimal_firebase_schema(schema_data, firebase_json.get('project_id', 'Unknown'))
                
                # Store in cache using the imported schema_cache
                if not connection_id:
                    connection_id = str(uuid.uuid4())
                self.schema_cache.store_schema(connection_id, schema_data, schema_context)
                
                return schema_data, schema_context, connection_id
            else:
                raise Exception(f"Failed to load Firebase schema: {message}")
                
        except Exception as e:
            error_msg = str(e)
            print(f"DEBUG: Firebase schema loading failed: {error_msg}")
            raise Exception(f"Firebase schema loading failed: {error_msg}")
    
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

Patients Table:
- id (INT, PRIMARY KEY)
- first_name (VARCHAR)
- last_name (VARCHAR)
- email (VARCHAR)
- phone (VARCHAR)
- gender (VARCHAR)
- date_of_birth (DATE)
- created_at (DATETIME)

Appointments Table:
- id (INT, PRIMARY KEY)
- patient_id (INT, FOREIGN KEY)
- appointment_date (DATETIME)
- doctor_name (VARCHAR)
- status (VARCHAR)

Clubs Table:
- id (INT, PRIMARY KEY)
- name (VARCHAR)
- description (TEXT)
- created_at (DATETIME)
- member_count (INT)
"""

    def _extract_schema_entities(self, schema_context: str, db_type: str) -> Dict[str, List[str]]:
        """
        Extract tables/collections and their fields from schema context
        Returns: {'tables': ['table1', 'table2'], 'fields': {'table1': ['field1', 'field2']}}
        """
        entities = {'tables': [], 'fields': {}}
        
        if not schema_context:
            return entities
        
        lines = schema_context.split('\n')
        current_table = None
        
        for line in lines:
            line = line.strip()
            
            # Detect table/collection names
            if db_type in ['mysql', 'supabase', 'demo']:
                if line.startswith('Table:'):
                    table_match = re.search(r'Table:\s*(\w+)', line)
                    if table_match:
                        current_table = table_match.group(1)
                        entities['tables'].append(current_table)
                        entities['fields'][current_table] = []
            elif db_type == 'firebase':
                if line.startswith('📁 Collection:'):
                    collection_match = re.search(r'Collection:\s*(\w+)', line)
                    if collection_match:
                        current_table = collection_match.group(1)
                        entities['tables'].append(current_table)
                        entities['fields'][current_table] = []
            
            # Detect fields/columns
            if current_table and ('-' in line or 'Fields:' in line):
                if db_type in ['mysql', 'supabase', 'demo']:
                    field_match = re.search(r'-\s+(\w+)\s*\(', line)
                    if field_match:
                        entities['fields'][current_table].append(field_match.group(1))
                elif db_type == 'firebase':
                    if 'Fields:' in line:
                        fields_part = line.split('Fields:')[-1].strip()
                        field_names = [f.strip() for f in re.split(r',\s*', fields_part) if f.strip()]
                        entities['fields'][current_table].extend(field_names)
        
        return entities

    def _find_best_table_match(self, user_prompt: str, schema_entities: Dict[str, List[str]]) -> Tuple[str, float]:
        """
        Find the best matching table/collection from schema based on user prompt
        Returns: (best_table_name, confidence_score)
        """
        user_words = user_prompt.lower().split()
        best_table = None
        best_score = 0.0
        
        for table in schema_entities.get('tables', []):
            table_lower = table.lower()
            
            # Exact match
            if table_lower in user_prompt.lower():
                return table, 1.0
            
            # Partial match
            for word in user_words:
                if len(word) < 3:
                    continue
                
                # Check if word is similar to table name
                similarity = SequenceMatcher(None, word, table_lower).ratio()
                if similarity > 0.7 and similarity > best_score:
                    best_score = similarity
                    best_table = table
            
            # Check for plural/singular variations
            if table_lower.endswith('s') and table_lower[:-1] in user_prompt.lower():
                return table, 0.9
            elif not table_lower.endswith('s') and (table_lower + 's') in user_prompt.lower():
                return table, 0.9
        
        return best_table, best_score

    def _extract_requested_fields(self, user_prompt: str, schema_entities: Dict[str, List[str]], table: str) -> List[str]:
        """
        Extract specific fields requested by user from the prompt with better matching
        Returns list of field names
        """
        requested_fields = []
        user_prompt_lower = user_prompt.lower()
        
        # Get available fields for the table
        available_fields = schema_entities.get('fields', {}).get(table, [])
        
        if not available_fields:
            return []
        
        # Enhanced field mappings with better pattern matching
        field_keywords = {
            'first_name': ['first name', 'firstname', 'first names', 'first_name', 'given name'],
            'last_name': ['last name', 'lastname', 'last names', 'last_name', 'surname', 'family name'],
            'name': ['name', 'names', 'full name', 'complete name'],
            'email': ['email', 'emails', 'e-mail', 'email address'],
            'id': ['id', 'ids', 'identifier', 'patient id', 'user id'],
            'phone': ['phone', 'phones', 'phone number', 'telephone', 'mobile', 'contact number'],
            'gender': ['gender', 'sex', 'male/female'],
            'age': ['age', 'ages', 'how old'],
            'address': ['address', 'location', 'residence'],
            'city': ['city', 'cities', 'town'],
            'state': ['state', 'province', 'region'],
            'zip_code': ['zip', 'zip code', 'postal code', 'postcode'],
            'birth_date': ['birth date', 'birthdate', 'date of birth', 'dob', 'born'],
            'created_at': ['created at', 'created', 'creation date', 'date created'],
            'updated_at': ['updated at', 'updated', 'last updated', 'modified'],
            'status': ['status', 'state', 'active', 'inactive'],
            'price': ['price', 'prices', 'cost', 'costs', 'amount'],
            'quantity': ['quantity', 'quantities', 'amount', 'stock', 'count'],
            'category': ['category', 'categories', 'type', 'types']
        }
        
        # First, check for exact field matches in the prompt
        for field in available_fields:
            field_lower = field.lower()
            # Check if the field name itself is mentioned
            if field_lower in user_prompt_lower:
                requested_fields.append(field)
        
        # Then use keyword mapping for fields not already found
        for field, keywords in field_keywords.items():
            if (field in available_fields and 
                field not in requested_fields and
                any(keyword in user_prompt_lower for keyword in keywords)):
                requested_fields.append(field)
        
        # Special case: if user asks for "first name" but schema has "first_name"
        if 'first name' in user_prompt_lower and 'first_name' in available_fields and 'first_name' not in requested_fields:
            requested_fields.append('first_name')
        
        # Special case: if user asks for "last name" but schema has "last_name"  
        if 'last name' in user_prompt_lower and 'last_name' in available_fields and 'last_name' not in requested_fields:
            requested_fields.append('last_name')
        
        # If no specific fields found but table has common fields, use them
        if not requested_fields:
            common_fields = ['name', 'first_name', 'title', 'email', 'id']
            for field in common_fields:
                if field in available_fields:
                    requested_fields.append(field)
                    break
        
        return requested_fields

    def _detect_query_type(self, user_prompt: str) -> str:
        """
        Detect the type of query from user prompt
        """
        user_prompt_lower = user_prompt.lower()
        
        # Check for specific query types in order of specificity
        if any(word in user_prompt_lower for word in ['join', 'with', 'together', 'combine', 'related']):
            return "join"
        elif any(word in user_prompt_lower for word in ['count', 'sum', 'average', 'avg', 'total', 'maximum', 'minimum', 'max', 'min', 'group by']):
            return "aggregation"
        elif any(word in user_prompt_lower for word in ['add', 'insert', 'create', 'new', 'register']):
            return "insert"
        elif any(word in user_prompt_lower for word in ['update', 'change', 'modify', 'edit', 'set']):
            return "update"
        elif any(word in user_prompt_lower for word in ['delete', 'remove', 'drop', 'erase']):
            return "delete"
        elif any(word in user_prompt_lower for word in ['where', 'filter', 'condition', 'only', 'specific', 'older', 'younger', 'greater', 'less', 'after', 'before', 'with', 'who', 'whose', 'above', 'below', 'more', 'less']):
            return "filtering"
        elif any(word in user_prompt_lower for word in ['sort', 'order by', 'arrange', 'alphabetical', 'ascending', 'descending']):
            return "sorting"
        elif any(word in user_prompt_lower for word in ['all', 'list', 'show', 'display', 'get']):
            return "select"
        else:
            return "select"  # Default to SELECT

    def extract_table_name(self, user_prompt: str, schema_context: str, db_type: str) -> str:
        """
        Extract table name from user prompt using schema-aware matching
        """
        # First try schema-aware matching
        if schema_context and "No schema" not in schema_context and "Error" not in schema_context:
            schema_entities = self._extract_schema_entities(schema_context, db_type)
            best_table, confidence = self._find_best_table_match(user_prompt, schema_entities)
            
            if best_table and confidence > 0.6:
                print(f"DEBUG: Schema-aware table match: {best_table} (confidence: {confidence})")
                return best_table
        
        # Fallback to pattern-based extraction
        patterns = [
            r'(?:from|table|in)\s+(\w+)',
            r'all\s+(?:\w+\s+)*from\s+(\w+)',
            r'(\w+)\s+table',
            r'get\s+(?:\w+\s+)*from\s+(\w+)',
            r'select\s+(?:\w+\s+)*from\s+(\w+)',
            r'show\s+(?:\w+\s+)*from\s+(\w+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, user_prompt.lower())
            if match:
                table_name = match.group(1)
                if table_name and re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table_name):
                    return table_name
        
        # Look for specific patterns
        if 'stud1234' in user_prompt.lower():
            return 'stud1234'
        
        # Extract from words
        words = user_prompt.lower().split()
        for word in words:
            if word in ['from', 'table', 'select', 'where', 'and', 'or', 'all', 'get', 'show', 'data']:
                continue
            if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', word) and len(word) > 2:
                return word
                
        return "users"  # Default fallback

    def generate_query(self, db_type: str, db_credentials: Dict[str, Any], user_prompt: str, gemini_api_key: str, connection_id: str = None) -> str:
        """
        Generate SQL/NoSQL query using Gemini AI with enhanced schema-aware natural language understanding
        """
        try:
            # Get schema context
            schema_context = self.get_schema_context(db_type, db_credentials)
            
            # For Firebase, use cached schema if available
            if db_type == 'firebase' and connection_id:
                _, cached_schema_context = self.schema_cache.get_schema(connection_id)
                if cached_schema_context:
                    schema_context = cached_schema_context
            
            # Extract table name using schema-aware matching
            extracted_table = self.extract_table_name(user_prompt, schema_context, db_type)
            
            # Extract requested fields
            schema_entities = self._extract_schema_entities(schema_context, db_type)
            requested_fields = self._extract_requested_fields(user_prompt, schema_entities, extracted_table)
            
            # Create enhanced system prompt with schema context and field information
            system_prompt = self._create_enhanced_system_prompt(db_type, schema_context, extracted_table, user_prompt, requested_fields)
            
            # Configure Gemini
            genai.configure(api_key=gemini_api_key)
            
            # Try different models
            model_names = [
                'gemini-2.5-flash',
                'gemini-2.0-flash',
                'gemini-flash-latest'
            ]
            
            last_error = None
            
            for model_name in model_names:
                try:
                    print(f"Trying Gemini model: {model_name}")
                    model = genai.GenerativeModel(model_name)
                    
                    # Create the enhanced prompt with schema context
                    enhanced_prompt = f"""
User Request: "{user_prompt}"
Detected Table: {extracted_table}
Requested Fields: {requested_fields if requested_fields else 'Not specified - use appropriate fields'}
Database Schema Context: {schema_context}

Generate the most appropriate query based on the user's intent and the exact database schema.
Use ONLY the tables and fields that exist in the schema.
"""
                    
                    full_prompt = f"{system_prompt}\n\n{enhanced_prompt}"
                    
                    response = model.generate_content(full_prompt)
                    generated_query = response.text.strip()
                    
                    print(f"DEBUG: Raw generated query: {generated_query}")
                    
                    # Clean the generated query with field awareness
                    cleaned_query = self._clean_generated_query(generated_query, db_type, extracted_table, user_prompt, schema_context, requested_fields)
                    
                    print(f"DEBUG: Cleaned query: {cleaned_query}")
                    
                    if cleaned_query:
                        print(f"Success with model: {model_name}")
                        return cleaned_query
                    
                except Exception as e:
                    last_error = e
                    print(f"Model {model_name} failed: {str(e)}")
                    continue
            
            # If all models fail, try the direct API approach
            try:
                print("Trying direct API approach...")
                result = self._call_gemini_direct_api(gemini_api_key, system_prompt, user_prompt, db_type, extracted_table, schema_context, requested_fields)
                print(f"DEBUG: Direct API result: {result}")
                return result
            except Exception as direct_error:
                last_error = direct_error
            
            # If all attempts fail, generate schema-aware fallback query
            print("Using schema-aware fallback query generation...")
            return self._generate_schema_aware_fallback_query(user_prompt, db_type, extracted_table, schema_context, requested_fields)
            
        except Exception as e:
            print(f"Query generation failed, using fallback: {str(e)}")
            return self._generate_schema_aware_fallback_query(user_prompt, db_type, self.extract_table_name(user_prompt, "", db_type), schema_context, requested_fields)
    
    def _create_enhanced_system_prompt(self, db_type: str, schema_context: str, extracted_table: str, user_prompt: str, requested_fields: List[str]) -> str:
        """
        Create enhanced system prompt with comprehensive query type support
        """
        fields_info = ""
        if requested_fields:
            fields_info = f"SPECIFICALLY REQUESTED FIELDS: {', '.join(requested_fields)}\n"
        else:
            fields_info = "USER HAS NOT SPECIFIED PARTICULAR FIELDS - SELECT APPROPRIATE FIELDS BASED ON THEIR REQUEST\n"
        
        # Detect query type from user prompt
        query_type = self._detect_query_type(user_prompt)
        
        base_prompt = f"""
You are an expert AI trained to convert natural language into accurate database queries.

CRITICAL RULES:
1. **SCHEMA AWARENESS**: Use ONLY the exact table and field names that exist in the provided schema.
2. **FIELD SELECTION**: Select ONLY the specific fields requested by the user. DO NOT use SELECT * or retrieve all fields.
3. **INTENT UNDERSTANDING**: Analyze the user's intent and convert it to the appropriate query type.
4. **EXACT MATCHING**: If the user says "product" but the schema has "products", use "products".

*** QUERY TYPE DETECTED: {query_type.upper()} ***

*** FIELD SELECTION RULES ***
1. NEVER use SELECT * - ALWAYS specify exact column names
2. If user asks for "first name", select ONLY the first_name field
3. If user asks for "names", select ONLY the name or first_name fields
4. Only select fields explicitly mentioned by the user
5. If unsure which fields to select, choose the most relevant 1-2 fields

*** QUERY TYPE EXAMPLES ***

SELECT QUERIES:
- User: "first name of patients" → Query: "SELECT first_name FROM patients"
- User: "patient emails" → Query: "SELECT email FROM patients" 
- User: "all products" → Query: "SELECT name, price FROM products LIMIT 100"
- User: "active users" → Query: "SELECT username, email FROM users WHERE status = 'active'"
- User: "products with price > 100" → Query: "SELECT name, price FROM products WHERE price > 100"

JOIN QUERIES:
- User: "join appointments and patients table" → Query: "SELECT appointments.*, patients.first_name, patients.last_name FROM appointments INNER JOIN patients ON appointments.patient_id = patients.id"
- User: "patients with their appointments" → Query: "SELECT patients.first_name, patients.last_name, appointments.appointment_date FROM patients LEFT JOIN appointments ON patients.id = appointments.patient_id"
- User: "orders with customer information" → Query: "SELECT orders.id, orders.order_date, customers.name, customers.email FROM orders INNER JOIN customers ON orders.customer_id = customers.id"

AGGREGATION QUERIES:
- User: "count of patients" → Query: "SELECT COUNT(*) as patient_count FROM patients"
- User: "average product price" → Query: "SELECT AVG(price) as average_price FROM products"
- User: "total sales by month" → Query: "SELECT MONTH(order_date) as month, SUM(amount) as total_sales FROM orders GROUP BY MONTH(order_date)"
- User: "most expensive product" → Query: "SELECT name, MAX(price) as max_price FROM products"

FILTERING QUERIES:
- User: "patients born after 2000" → Query: "SELECT first_name, last_name FROM patients WHERE date_of_birth > '2000-01-01'"
- User: "products in electronics category" → Query: "SELECT name, price FROM products WHERE category = 'electronics'"
- User: "users with gmail addresses" → Query: "SELECT username, email FROM users WHERE email LIKE '%@gmail.com'"

SORTING QUERIES:
- User: "products by price high to low" → Query: "SELECT name, price FROM products ORDER BY price DESC"
- User: "patients by last name" → Query: "SELECT first_name, last_name FROM patients ORDER BY last_name ASC"
- User: "recent orders first" → Query: "SELECT id, order_date FROM orders ORDER BY order_date DESC"

INSERT QUERIES:
- User: "add new patient John Doe" → Query: "INSERT INTO patients (first_name, last_name, email) VALUES ('John', 'Doe', 'john.doe@email.com')"
- User: "create new product" → Query: "INSERT INTO products (name, price, category) VALUES ('New Product', 99.99, 'General')"

UPDATE QUERIES:
- User: "update patient email" → Query: "UPDATE patients SET email = 'new.email@example.com' WHERE id = 123"
- User: "mark order as completed" → Query: "UPDATE orders SET status = 'completed' WHERE id = 456"

DELETE QUERIES:
- User: "delete inactive users" → Query: "DELETE FROM users WHERE status = 'inactive'"
- User: "remove product by id" → Query: "DELETE FROM products WHERE id = 789"

DATABASE TYPE: {db_type.upper()}

DATABASE SCHEMA CONTEXT:
{schema_context}

DETECTED TABLE FROM USER QUERY: {extracted_table}

{fields_info}
USER REQUEST: "{user_prompt}"

IMPORTANT: 
- Use EXACT table and field names from the schema
- If a field doesn't exist in the schema, DO NOT use it
- Select ONLY the fields the user requested, not all fields
- Match plural/singular forms to the actual schema names
- Generate clean, executable queries
- For JOINs, use proper join conditions based on foreign keys
- For aggregations, use appropriate GROUP BY clauses
- For updates/deletes, always include WHERE clauses to avoid mass updates

"""

        if db_type == 'mysql':
            db_specific = """
### MYSQL QUERY RULES:
- Use standard SQL syntax: SELECT, FROM, WHERE, GROUP BY, ORDER BY, LIMIT, etc.
- Use backticks for table and column names if they contain special characters
- Use NOW() for current timestamp
- Use LIMIT for row limiting (default to 100 for "all" queries)
- Use appropriate JOINs when multiple tables are involved
- Always include WHERE clauses for filtering when requested
- Use ORDER BY for sorting when displaying lists
- Use exact column names from the schema
- **CRITICAL: DO NOT use SELECT * - always specify exact columns**
- For JOINs: Use INNER JOIN, LEFT JOIN, RIGHT JOIN as appropriate
- For aggregations: Use COUNT(), SUM(), AVG(), MAX(), MIN() with proper GROUP BY
- For dates: Use DATE(), MONTH(), YEAR() functions for date operations

EXAMPLES:
- SELECT: SELECT first_name, last_name FROM patients WHERE status = 'active'
- JOIN: SELECT p.first_name, p.last_name, a.appointment_date FROM patients p INNER JOIN appointments a ON p.id = a.patient_id
- AGGREGATION: SELECT COUNT(*) as total_patients FROM patients
- INSERT: INSERT INTO patients (first_name, last_name, email) VALUES ('John', 'Doe', 'john@example.com')
- UPDATE: UPDATE patients SET email = 'new@example.com' WHERE id = 1
- DELETE: DELETE FROM patients WHERE id = 1 AND status = 'inactive'
"""
        elif db_type == 'supabase':
            db_specific = """
### SUPABASE (POSTGRESQL) QUERY RULES:
- Use PostgreSQL syntax
- Use double quotes for table and column names if they contain special characters
- Use CURRENT_TIMESTAMP for current timestamp
- Use LIMIT for row limiting (default to 100 for "all" queries)
- Use ILIKE for case-insensitive pattern matching
- Use exact column names from the schema
- **CRITICAL: DO NOT use SELECT * - always specify exact columns**
- For JOINs: Use INNER JOIN, LEFT JOIN, RIGHT JOIN, FULL JOIN as appropriate
- For aggregations: Use COUNT(), SUM(), AVG(), MAX(), MIN() with proper GROUP BY
- Use RETURNING * for INSERT/UPDATE/DELETE to get affected rows

EXAMPLES:
- SELECT: SELECT first_name, last_name FROM patients WHERE status = 'active'
- JOIN: SELECT p.first_name, p.last_name, a.appointment_date FROM patients p INNER JOIN appointments a ON p.id = a.patient_id
- AGGREGATION: SELECT COUNT(*) as total_patients FROM patients
- INSERT: INSERT INTO patients (first_name, last_name, email) VALUES ('John', 'Doe', 'john@example.com') RETURNING *
- UPDATE: UPDATE patients SET email = 'new@example.com' WHERE id = 1 RETURNING *
- DELETE: DELETE FROM patients WHERE id = 1 AND status = 'inactive' RETURNING *
"""
        elif db_type == 'firebase':
            db_specific = """
### FIREBASE (FIRESTORE) QUERY RULES:
- Generate ONLY Python code using the Firestore SDK
- DO NOT include import statements (they are already handled)
- Use db.collection() to access collections - use EXACT collection names from schema
- Use .where() for filtering with proper operators (==, >, <, >=, <=, array_contains, etc.)
- Use .order_by() for sorting with direction (firestore.Query.ASCENDING/DESCENDING)
- Use .limit() for limiting results (default to 100 for "all" queries)
- Use .stream() to execute the query
- **CRITICAL: Use .select() to specify only the required fields, not all fields**
- ALWAYS include: result = [doc.to_dict() for doc in docs] at the end
- Use exact field names from the schema
- Put each statement on its own line
- For multiple collection queries, use separate queries and combine results

EXAMPLES:
- SELECT: 
  docs = db.collection('patients').select(['first_name', 'last_name']).where('status', '==', 'active').stream()
  result = [doc.to_dict() for doc in docs]

- FILTERING:
  docs = db.collection('products').where('price', '>', 100).where('category', '==', 'electronics').stream()
  result = [doc.to_dict() for doc in docs]

- SORTING:
  docs = db.collection('products').order_by('price', direction=firestore.Query.DESCENDING).limit(10).stream()
  result = [doc.to_dict() for doc in docs]

- MULTIPLE COLLECTIONS (JOIN-like):
  # First get appointments
  appointments_docs = db.collection('appointments').stream()
  appointments = [doc.to_dict() for doc in appointments_docs]
  
  # Then get patients for each appointment
  result = []
  for appointment in appointments:
      patient_doc = db.collection('patients').document(appointment['patient_id']).get()
      if patient_doc.exists:
          patient_data = patient_doc.to_dict()
          combined_data = {**appointment, 'patient_name': patient_data.get('first_name') + ' ' + patient_data.get('last_name')}
          result.append(combined_data)

- INSERT:
  doc_ref = db.collection('patients').document()
  doc_ref.set({
      'first_name': 'John',
      'last_name': 'Doe',
      'email': 'john@example.com'
  })
  result = {'id': doc_ref.id, 'message': 'Patient created successfully'}

- UPDATE:
  doc_ref = db.collection('patients').document('patient_id')
  doc_ref.update({
      'email': 'new@example.com'
  })
  result = {'message': 'Patient updated successfully'}

- DELETE:
  db.collection('patients').document('patient_id').delete()
  result = {'message': 'Patient deleted successfully'}
"""
        elif db_type == 'demo':
            db_specific = """
### DEMO MODE QUERY RULES:
- Use standard SQL syntax (MySQL-like)
- Use exact table and column names from the schema
- Always include sensible ORDER BY when displaying lists
- Use appropriate WHERE clauses for filtering
- **CRITICAL: DO NOT use SELECT * - always specify exact columns**
- For JOINs: Use INNER JOIN with proper ON conditions
- For aggregations: Use appropriate aggregate functions

EXAMPLES:
- SELECT: SELECT first_name, last_name FROM patients WHERE status = 'active'
- JOIN: SELECT p.first_name, p.last_name, a.appointment_date FROM patients p INNER JOIN appointments a ON p.id = a.patient_id
- AGGREGATION: SELECT COUNT(*) as total_patients FROM patients
- INSERT: INSERT INTO patients (first_name, last_name, email) VALUES ('John', 'Doe', 'john@example.com')
- UPDATE: UPDATE patients SET email = 'new@example.com' WHERE id = 1
- DELETE: DELETE FROM patients WHERE id = 1
"""
        else:
            db_specific = ""

        return base_prompt + db_specific + """

### FINAL INSTRUCTIONS:
1. **QUERY TYPE AWARENESS**: Generate the appropriate query type based on user intent
2. **FIELD-SPECIFIC SELECTION**: Select ONLY the fields the user requested, never use SELECT * or get all fields
3. **SCHEMA COMPLIANCE**: Use ONLY tables and columns that exist in the schema
4. **INTENT MAPPING**: Map user intent to the correct schema elements and query type
5. **QUERY OPTIMIZATION**: Make queries efficient and production-ready
6. **NO MARKDOWN**: Return ONLY the raw query code without explanations
7. **SYNTAX CORRECTNESS**: Ensure the query is syntactically correct
8. **EXECUTABLE**: Generate queries that can be directly executed
9. **SAFETY**: For UPDATE/DELETE, always include WHERE clauses to prevent mass operations

Return ONLY the raw query code, nothing else.
"""

    def _call_gemini_direct_api(self, api_key: str, system_prompt: str, user_prompt: str, db_type: str, extracted_table: str, schema_context: str, requested_fields: List[str]) -> str:
        """Alternative approach using direct API calls with enhanced schema-aware prompting"""
        model_names = [
            'gemini-2.5-flash',
            'gemini-2.0-flash'
        ]
        
        for model_name in model_names:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
                
                # Enhanced prompt with schema context
                fields_info = f"Requested Fields: {requested_fields}" if requested_fields else "User did not specify particular fields"
                
                enhanced_prompt = f"""
User Request: "{user_prompt}"
Detected Table: {extracted_table}
{fields_info}
Database Schema: {schema_context}

Generate the most appropriate query using ONLY the exact schema elements provided.
SELECT ONLY THE SPECIFIC FIELDS REQUESTED, NOT ALL FIELDS.
"""
                
                strict_prompt = f"{system_prompt}\n\n{enhanced_prompt}"
                
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
                
                headers = {"Content-Type": "application/json"}
                
                print(f"Calling Gemini API directly with model: {model_name}")
                response = requests.post(url, json=payload, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    if 'candidates' in data and len(data['candidates']) > 0:
                        generated_query = data['candidates'][0]['content']['parts'][0]['text']
                        cleaned_query = self._clean_generated_query(generated_query, db_type, extracted_table, user_prompt, schema_context, requested_fields)
                        if cleaned_query:
                            print(f"Direct API success with model: {model_name}")
                            return cleaned_query
                else:
                    print(f"API Error {response.status_code}: {response.text}")
                    
            except Exception as e:
                print(f"Direct API with {model_name} failed: {str(e)}")
                continue
        
        raise Exception("Direct API approach also failed")
    
    def _clean_generated_query(self, query: str, db_type: str, extracted_table: str, user_prompt: str, schema_context: str, requested_fields: List[str]) -> str:
        """
        Clean the generated query with enhanced validation for all query types
        """
        if not query:
            return query
            
        # Remove markdown code blocks
        query = re.sub(r'^```\w*\s*', '', query)
        query = re.sub(r'```\s*$', '', query)
        query = re.sub(r'^"|"$', '', query)
        
        # Remove common markdown artifacts and extra whitespace
        query = re.sub(r'\s+', ' ', query)
        query = query.strip()
        
        # Fix common SQL typos - ENHANCED
        query = re.sub(r'\bLINIT\b', 'LIMIT', query, flags=re.IGNORECASE)
        query = re.sub(r'\bSELCT\b', 'SELECT', query, flags=re.IGNORECASE)
        query = re.sub(r'\bFORM\b', 'FROM', query, flags=re.IGNORECASE)
        query = re.sub(r'\bWHRER\b', 'WHERE', query, flags=re.IGNORECASE)
        query = re.sub(r'\bJOIN\s+ON\s+ON\b', 'JOIN ON', query, flags=re.IGNORECASE)
        
        # Extract schema entities for field validation
        schema_entities = self._extract_schema_entities(schema_context, db_type)
        table_fields = schema_entities.get('fields', {}).get(extracted_table, [])
        
        # Detect query type for specific cleaning
        query_type = self._detect_query_type(user_prompt)
        
        # ENHANCED: For SQL SELECT queries, always replace SELECT * with specific fields when possible
        if db_type in ['mysql', 'supabase', 'demo'] and 'SELECT *' in query.upper() and query_type in ['select', 'join', 'filtering', 'sorting']:
            # Use requested_fields if available
            if requested_fields:
                valid_fields = [field for field in requested_fields if field in table_fields]
                if valid_fields:
                    field_list = ', '.join(valid_fields)
                    query = re.sub(r'SELECT \*', f'SELECT {field_list}', query, flags=re.IGNORECASE)
                    print(f"DEBUG: Replaced SELECT * with specific fields: {field_list}")
            else:
                # If no requested_fields, use the first few fields or common fields
                common_preferred = ['name', 'first_name', 'title', 'email', 'id']
                preferred_fields = [f for f in common_preferred if f in table_fields]
                if preferred_fields:
                    field_list = ', '.join(preferred_fields[:3])  # Use up to 3 common fields
                    query = re.sub(r'SELECT \*', f'SELECT {field_list}', query, flags=re.IGNORECASE)
                elif table_fields:
                    field_list = ', '.join(table_fields[:3])  # Use first 3 fields
                    query = re.sub(r'SELECT \*', f'SELECT {field_list}', query, flags=re.IGNORECASE)
        
        # ENHANCED: For Firebase, ensure field selection
        if db_type == 'firebase' and 'db.collection' in query:
            if requested_fields and '.select(' not in query:
                valid_fields = [field for field in requested_fields if field in table_fields]
                if valid_fields:
                    field_list = "', '".join(valid_fields)
                    if '.stream()' in query:
                        query = query.replace('.stream()', f".select(['{field_list}']).stream()")
                    elif '.limit(' in query:
                        query = re.sub(r'(\.limit\(\d+\))', f".select(['{field_list}'])\\1", query)
            
            # FIX: Ensure proper newlines for Firebase Python code
            # Replace any missing newlines between statements
            query = re.sub(r'(\.stream\(\))\s*(result\s*=)', r'\1\n\2', query)
            query = re.sub(r'(\.stream\(\))\s*(docs\s*=)', r'\1\n\2', query)
            query = re.sub(r'(\.get\(\))\s*(result\s*=)', r'\1\n\2', query)
            
            # Ensure result assignment is present
            if 'result =' not in query and 'docs =' in query and '.stream()' in query:
                query += '\nresult = [doc.to_dict() for doc in docs]'
            elif 'result =' not in query and 'query.stream()' in query:
                query += '\nresult = [doc.to_dict() for doc in docs]'
        
        # ENHANCED: Add LIMIT if missing for "all" SELECT queries
        user_prompt_lower = user_prompt.lower()
        if ('all' in user_prompt_lower or 'list' in user_prompt_lower or 'show' in user_prompt_lower) and 'LIMIT' not in query.upper() and db_type in ['mysql', 'supabase', 'demo'] and query_type == 'select':
            query += " LIMIT 100"
        
        # ENHANCED: For JOIN queries, ensure proper join conditions
        if query_type == 'join' and 'JOIN' in query.upper() and 'ON' not in query.upper():
            # Try to infer join condition
            tables_in_query = re.findall(r'\b(FROM|JOIN)\s+(\w+)', query, re.IGNORECASE)
            if len(tables_in_query) >= 2:
                table1 = tables_in_query[0][1]  # FROM table
                table2 = tables_in_query[1][1]  # JOIN table
                # Common foreign key patterns
                join_condition = f"ON {table1}.{table2[:-1] if table2.endswith('s') else table2}_id = {table2}.id"
                query = re.sub(r'JOIN\s+' + table2, f'JOIN {table2} {join_condition}', query, flags=re.IGNORECASE)
        
        # ENHANCED: For UPDATE/DELETE queries, add safety WHERE clause if missing
        if query_type in ['update', 'delete'] and 'WHERE' not in query.upper():
            if query_type == 'update':
                query += " WHERE id = 1"  # Safe default
            elif query_type == 'delete':
                query += " WHERE id = 1"  # Safe default
        
        return query

    def _generate_schema_aware_fallback_query(self, user_prompt: str, db_type: str, extracted_table: str, schema_context: str, requested_fields: List[str]) -> str:
        """Generate a schema-aware fallback query for all query types"""
        print(f"Generating schema-aware fallback query for: {user_prompt}")
        
        # Extract schema entities for better field selection
        schema_entities = self._extract_schema_entities(schema_context, db_type)
        table_fields = schema_entities.get('fields', {}).get(extracted_table, [])
        
        user_prompt_lower = user_prompt.lower()
        query_type = self._detect_query_type(user_prompt)
        
        # ENHANCED: Use requested_fields if available, otherwise infer from prompt
        if requested_fields:
            # Use the requested fields that exist in schema
            field_selection = [field for field in requested_fields if field in table_fields]
        else:
            # Infer fields from user prompt with better matching
            field_selection = []
            
            # Check for specific field mentions
            if 'first name' in user_prompt_lower and 'first_name' in table_fields:
                field_selection = ['first_name']
            elif 'name' in user_prompt_lower and 'name' in table_fields:
                field_selection = ['name']
            elif 'email' in user_prompt_lower and 'email' in table_fields:
                field_selection = ['email']
            elif 'phone' in user_prompt_lower and 'phone' in table_fields:
                field_selection = ['phone']
        
        # If no fields determined, use sensible defaults
        if not field_selection:
            if 'first_name' in table_fields:
                field_selection = ['first_name']
            elif 'name' in table_fields:
                field_selection = ['name']
            elif table_fields:
                field_selection = [table_fields[0]]  # Use first field
            else:
                field_selection = ['*']
        
        # Generate the appropriate query based on type
        if query_type == 'join':
            # For JOIN queries, we need to detect the second table
            tables = schema_entities.get('tables', [])
            second_table = None
            for table in tables:
                if table != extracted_table and table in user_prompt_lower:
                    second_table = table
                    break
            
            if second_table and db_type in ['mysql', 'supabase', 'demo']:
                # Generate JOIN query
                if field_selection != ['*']:
                    field_str = ', '.join([f"{extracted_table}.{field}" for field in field_selection])
                else:
                    field_str = f"{extracted_table}.*, {second_table}.*"
                
                # Common join pattern
                join_condition = f"ON {extracted_table}.{second_table[:-1] if second_table.endswith('s') else second_table}_id = {second_table}.id"
                return f"SELECT {field_str} FROM {extracted_table} INNER JOIN {second_table} {join_condition} LIMIT 100"
            else:
                # Fallback to simple SELECT if join not possible
                if db_type in ['mysql', 'supabase', 'demo']:
                    if field_selection != ['*']:
                        field_str = ', '.join(field_selection)
                    else:
                        field_str = '*'
                    return f"SELECT {field_str} FROM {extracted_table} LIMIT 100"
                else:
                    # Firebase fallback for JOIN-like request - FIXED with proper newlines
                    if field_selection != ['*']:
                        field_list = "', '".join(field_selection)
                        return f"docs = db.collection('{extracted_table}').select(['{field_list}']).stream()\nresult = [doc.to_dict() for doc in docs]"
                    else:
                        return f"docs = db.collection('{extracted_table}').stream()\nresult = [doc.to_dict() for doc in docs]"
        
        elif query_type == 'aggregation':
            # Handle aggregation queries
            if 'count' in user_prompt_lower:
                if db_type in ['mysql', 'supabase', 'demo']:
                    return f"SELECT COUNT(*) as total_count FROM {extracted_table}"
                else:
                    return f"docs = db.collection('{extracted_table}').stream()\nresult = len(list(docs))"
            elif any(word in user_prompt_lower for word in ['average', 'avg']):
                if db_type in ['mysql', 'supabase', 'demo'] and 'price' in table_fields:
                    return f"SELECT AVG(price) as average_price FROM {extracted_table}"
                else:
                    return f"# Aggregation not directly supported in Firestore for this field"
            else:
                # Default aggregation
                if db_type in ['mysql', 'supabase', 'demo']:
                    return f"SELECT COUNT(*) as total_count FROM {extracted_table}"
                else:
                    return f"docs = db.collection('{extracted_table}').stream()\nresult = len(list(docs))"
        
        elif query_type == 'insert':
            # Handle INSERT queries
            if db_type in ['mysql', 'supabase', 'demo']:
                sample_values = []
                for field in field_selection[:3]:  # Use first 3 fields
                    if field == 'id':
                        sample_values.append("1")
                    elif 'name' in field:
                        sample_values.append("'John'")
                    elif 'email' in field:
                        sample_values.append("'john@example.com'")
                    else:
                        sample_values.append("'value'")
                
                fields_str = ', '.join(field_selection[:3])
                values_str = ', '.join(sample_values)
                return f"INSERT INTO {extracted_table} ({fields_str}) VALUES ({values_str})"
            else:
                # Firebase INSERT
                field_data = {}
                for field in field_selection[:3]:
                    if 'name' in field:
                        field_data[field] = 'John'
                    elif 'email' in field:
                        field_data[field] = 'john@example.com'
                    else:
                        field_data[field] = 'value'
                
                field_data_str = ', '.join([f"'{k}': '{v}'" for k, v in field_data.items()])
                return f"doc_ref = db.collection('{extracted_table}').document()\ndoc_ref.set({{{field_data_str}}})\nresult = {{'id': doc_ref.id, 'message': 'Document created successfully'}}"
        
        elif query_type in ['update', 'delete']:
            # Handle UPDATE/DELETE queries with safety
            if query_type == 'update':
                if db_type in ['mysql', 'supabase', 'demo']:
                    return f"UPDATE {extracted_table} SET {field_selection[0] if field_selection else 'name'} = 'new_value' WHERE id = 1"
                else:
                    return f"doc_ref = db.collection('{extracted_table}').document('doc_id')\ndoc_ref.update({{'{field_selection[0] if field_selection else 'name'}': 'new_value'}})\nresult = {{'message': 'Document updated successfully'}}"
            else:  # delete
                if db_type in ['mysql', 'supabase', 'demo']:
                    return f"DELETE FROM {extracted_table} WHERE id = 1"
                else:
                    return f"db.collection('{extracted_table}').document('doc_id').delete()\nresult = {{'message': 'Document deleted successfully'}}"
        
        else:
            # Default SELECT query - FIXED with proper newlines for Firebase
            if db_type == 'firebase':
                if field_selection != ['*']:
                    field_list = "', '".join(field_selection)
                    base_query = f"docs = db.collection('{extracted_table}').select(['{field_list}']).stream()"
                else:
                    base_query = f"docs = db.collection('{extracted_table}').stream()"
                
                return f"{base_query}\nresult = [doc.to_dict() for doc in docs]"
            else:
                # SQL databases
                if field_selection != ['*']:
                    field_str = ', '.join(field_selection)
                else:
                    field_str = '*'
                
                return f"SELECT {field_str} FROM {extracted_table} LIMIT 100"

    def _generate_fallback_query(self, user_prompt: str, db_type: str, extracted_table: str) -> str:
        """Legacy fallback method - now uses schema-aware version"""
        return self._generate_schema_aware_fallback_query(user_prompt, db_type, extracted_table, "", [])

    def execute_query(self, db_type: str, db_credentials: Dict[str, Any], query: str, connection_id: str = None) -> Dict[str, Any]:
        """
        Execute the generated query against the database with cache support
        """
        try:
            # Clean the query before execution
            cleaned_query = self._clean_generated_query(query, db_type, "", "", "", [])
            print(f"Executing {db_type} query: {cleaned_query[:200]}...")
            
            if db_type == 'mysql':
                return self._execute_mysql_query(db_credentials, cleaned_query)
            elif db_type == 'supabase':
                return self._execute_supabase_query(db_credentials, cleaned_query)
            elif db_type == 'firebase':
                return self._execute_firebase_query(db_credentials, cleaned_query, connection_id)
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
                return {
                    "columns": list(result[0].keys()) if result else [],
                    "data": result,
                    "row_count": len(result)
                }
            else:
                connection.commit()
                return {
                    "affected_rows": cursor.rowcount, 
                    "message": "Query executed successfully"
                }
            
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
                    result_data = cursor.fetchall()
                    return {
                        "columns": columns,
                        "data": [dict(zip(columns, row)) for row in result_data],
                        "row_count": len(result_data)
                    }
                else:
                    connection.commit()
                    return {
                        "affected_rows": cursor.rowcount, 
                        "message": "Query executed successfully"
                    }
                
            except ImportError:
                return {"error": "PostgreSQL support not available. Install psycopg2 for full functionality."}
            
        except Exception as e:
            error_msg = str(e)
            # Provide more user-friendly error messages
            if "relation" in error_msg and "does not exist" in error_msg:
                table_match = re.search(r'relation "([^"]+)" does not exist', error_msg)
                if table_match:
                    table_name = table_match.group(1)
                    raise Exception(f"Table '{table_name}' does not exist in your database.")
                else:
                    raise Exception(f"Table does not exist in your database.")
            elif "column" in error_msg and "does not exist" in error_msg:
                column_match = re.search(r'column "([^"]+)" does not exist', error_msg)
                if column_match:
                    column_name = column_match.group(1)
                    raise Exception(f"Column '{column_name}' does not exist.")
                else:
                    raise Exception(f"Column does not exist.")
            else:
                raise Exception(f"Supabase query execution failed: {error_msg}")
    
    def _execute_firebase_query(self, db_credentials: Dict[str, Any], query: str, connection_id: str = None) -> Dict[str, Any]:
        """Execute Firebase query using testfirebase module with cache support"""
        try:
            # Import and use testfirebase module
            import testfirebase
            
            if 'service_account_json' in db_credentials and db_credentials['service_account_json']:
                firebase_json = json.loads(db_credentials['service_account_json'])
            else:
                firebase_json = {
                    "type": "service_account",
                    "project_id": db_credentials.get('project_id', ''),
                    "private_key": db_credentials.get('private_key', '').replace('\\n', '\n'),
                    "client_email": db_credentials.get('client_email', '')
                }
            
            # Connect to Firebase
            success, message, schema_data = testfirebase.connect_and_load_schema(firebase_json)
            
            if not success:
                return {"error": f"Firebase connection failed: {message}"}
            
            # Now we need to execute the generated Python code
            temp_file_path = None
            try:
                # Write JSON to a temp file for the execution context
                with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w") as temp_json:
                    json.dump(firebase_json, temp_json)
                    temp_file_path = temp_json.name
                
                # Initialize Firebase with the temporary file
                cred = credentials.Certificate(temp_file_path)
                firebase_admin.initialize_app(cred)
                
                # Get Firestore client
                db = firestore.client()
                
                # Clean the query first - FIXED: Ensure proper newlines for Firebase
                cleaned_query = self._clean_generated_query(query, 'firebase', "", "", "", [])
                
                # ADDITIONAL FIX: Ensure proper newlines for the specific case
                cleaned_query = re.sub(r'(\.stream\(\))\s*(result\s*=)', r'\1\n\2', cleaned_query)
                cleaned_query = re.sub(r'(\.stream\(\))\s*(docs\s*=)', r'\1\n\2', cleaned_query)
                
                print(f"DEBUG: Executing Firebase query: {cleaned_query[:200]}...")
                
                # Prepare the execution environment with necessary imports
                exec_globals = {
                    'db': db,
                    'firestore': firestore,
                    '__builtins__': __builtins__
                }
                
                # Add common Firebase imports to the execution context
                exec_globals.update({
                    'credentials': credentials,
                    'firebase_admin': firebase_admin
                })
                
                # Execute the code in a try block to catch syntax errors
                try:
                    # First, compile the code to check for syntax errors
                    compiled_code = compile(cleaned_query, '<string>', 'exec')
                    
                    # Create a local namespace for execution
                    local_vars = {
                        'db': db,
                        'firestore': firestore,
                        'result': None,
                        'docs': None
                    }
                    
                    # Execute the compiled code
                    exec(compiled_code, exec_globals, local_vars)
                    
                    # Get the result
                    result = local_vars.get('result')
                    
                    # If no result was set, try to get docs and convert
                    if result is None and 'docs' in local_vars and local_vars['docs'] is not None:
                        docs = local_vars['docs']
                        if hasattr(docs, '__iter__'):
                            result = []
                            for doc in docs:
                                if hasattr(doc, 'to_dict'):
                                    result.append(doc.to_dict())
                                else:
                                    result.append(doc)
                        else:
                            result = docs
                    
                    if result is not None:
                        if isinstance(result, list):
                            return {
                                "data": result,
                                "row_count": len(result)
                            }
                        else:
                            return {
                                "result": result,
                                "message": "Firebase operation completed successfully"
                            }
                    else:
                        return {
                            "message": "Firebase operation completed successfully (no result returned)"
                        }
                        
                except SyntaxError as e:
                    # Enhanced error message with line numbers
                    error_msg = str(e)
                    lines = cleaned_query.split('\n')
                    error_with_context = f"Syntax error in generated query: {error_msg}\nQuery lines:\n"
                    for i, line in enumerate(lines, 1):
                        error_with_context += f"{i}: {line}\n"
                    return {"error": error_with_context}
                except Exception as e:
                    # Provide more user-friendly error messages
                    error_msg = str(e)
                    print(f"DEBUG: Firebase query execution failed: {error_msg}")
                    if "collection" in error_msg and "not found" in error_msg:
                        return {"error": "Collection not found. Please check if the collection name exists in your Firebase project."}
                    elif "Permission denied" in error_msg:
                        return {"error": "Permission denied. Please check if your service account has read/write permissions for Firestore."}
                    elif "Invalid argument" in error_msg:
                        return {"error": "Invalid query argument. Please check your Firebase query syntax."}
                    else:
                        return {"error": f"Firebase query execution failed: {error_msg}"}
                    
            except Exception as e:
                # Provide more user-friendly error messages
                error_msg = str(e)
                print(f"DEBUG: Firebase setup failed: {error_msg}")
                return {"error": f"Firebase setup failed: {error_msg}"}
            finally:
                # Clean up Firebase app
                try:
                    if firebase_admin._apps:
                        firebase_admin.delete_app(firebase_admin.get_app())
                except:
                    pass
                
                # Clean up temporary file
                if temp_file_path and os.path.exists(temp_file_path):
                    try:
                        os.unlink(temp_file_path)
                    except:
                        pass
                
        except Exception as e:
            return {"error": f"Firebase execution setup failed: {str(e)}"}
    
    def test_firebase_connection(self, db_credentials: Dict[str, Any]) -> Dict[str, Any]:
        """Test Firebase connection with a simple query"""
        try:
            import testfirebase
            
            if 'service_account_json' in db_credentials and db_credentials['service_account_json']:
                firebase_json = json.loads(db_credentials['service_account_json'])
            else:
                firebase_json = {
                    "type": "service_account",
                    "project_id": db_credentials.get('project_id', ''),
                    "private_key": db_credentials.get('private_key', '').replace('\\n', '\n'),
                    "client_email": db_credentials.get('client_email', '')
                }
            
            success, message, schema_data = testfirebase.connect_and_load_schema(firebase_json)
            
            if success:
                # Try a simple query to list collections
                temp_file_path = None
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w") as temp_json:
                        json.dump(firebase_json, temp_json)
                        temp_file_path = temp_json.name
                    
                    cred = credentials.Certificate(temp_file_path)
                    firebase_admin.initialize_app(cred)
                    
                    db = firestore.client()
                    collections = db.collections()
                    collection_names = [collection.id for collection in collections]
                    
                    return {
                        "success": True,
                        "collections": collection_names,
                        "total_collections": len(collection_names)
                    }
                except Exception as e:
                    return {"error": f"Test query failed: {str(e)}"}
                finally:
                    try:
                        if firebase_admin._apps:
                            firebase_admin.delete_app(firebase_admin.get_app())
                    except:
                        pass
                    if temp_file_path and os.path.exists(temp_file_path):
                        try:
                            os.unlink(temp_file_path)
                        except:
                            pass
            else:
                return {"error": f"Connection failed: {message}"}
                
        except Exception as e:
            return {"error": f"Test failed: {str(e)}"}
    
    def _execute_demo_query(self, query: str) -> Dict[str, Any]:
        """Execute demo query (simulated)"""
        # Convert query to lowercase for easier matching
        query_lower = query.lower().strip()
        
        # Remove semicolons and extra spaces
        query_clean = query_lower.replace(';', '').strip()
        
        print(f"Demo query: {query_clean}")
        
        # Handle different query patterns
        if "join" in query_clean and "appointments" in query_clean and "patients" in query_clean:
            return {
                "columns": ["appointment_id", "patient_id", "appointment_date", "first_name", "last_name"],
                "data": [
                    {"appointment_id": 1, "patient_id": 1, "appointment_date": "2024-01-15 10:00:00", "first_name": "Aarav", "last_name": "Sharma"},
                    {"appointment_id": 2, "patient_id": 2, "appointment_date": "2024-01-16 14:30:00", "first_name": "Ananya", "last_name": "Iyer"},
                    {"appointment_id": 3, "patient_id": 3, "appointment_date": "2024-01-17 09:15:00", "first_name": "Rohan", "last_name": "Patel"}
                ],
                "row_count": 3
            }
        elif "patients" in query_clean and "first_name" in query_clean:
            return {
                "columns": ["first_name"],
                "data": [
                    {"first_name": "Aarav"},
                    {"first_name": "Ananya"},
                    {"first_name": "Rohan"},
                    {"first_name": "Priya"},
                    {"first_name": "Vikram"}
                ],
                "row_count": 5
            }
        elif "appointments" in query_clean:
            return {
                "columns": ["id", "patient_id", "appointment_date", "doctor_name", "status"],
                "data": [
                    {"id": 1, "patient_id": 1, "appointment_date": "2024-01-15 10:00:00", "doctor_name": "Dr. Smith", "status": "scheduled"},
                    {"id": 2, "patient_id": 2, "appointment_date": "2024-01-16 14:30:00", "doctor_name": "Dr. Johnson", "status": "completed"},
                    {"id": 3, "patient_id": 3, "appointment_date": "2024-01-17 09:15:00", "doctor_name": "Dr. Williams", "status": "scheduled"}
                ],
                "row_count": 3
            }
        elif "clubs" in query_clean:
            return {
                "columns": ["id", "name", "description", "member_count"],
                "data": [
                    {"id": 1, "name": "Chess Club", "description": "Strategy and board games", "member_count": 25},
                    {"id": 2, "name": "Drama Club", "description": "Theater and performance arts", "member_count": 18},
                    {"id": 3, "name": "Science Club", "description": "STEM activities and experiments", "member_count": 32},
                    {"id": 4, "name": "Debate Club", "description": "Public speaking and arguments", "member_count": 22}
                ],
                "row_count": 4
            }
        elif "students" in query_clean and "name" in query_clean:
            return {
                "columns": ["name"],
                "data": [
                    {"name": "John Doe"},
                    {"name": "Jane Smith"},
                    {"name": "Bob Johnson"},
                    {"name": "Alice Brown"},
                    {"name": "Charlie Wilson"}
                ],
                "row_count": 5
            }
        elif "students" in query_clean:
            return {
                "columns": ["id", "name", "age", "grade"],
                "data": [
                    {"id": 1, "name": "John Doe", "age": 20, "grade": "A"},
                    {"id": 2, "name": "Jane Smith", "age": 21, "grade": "B"},
                    {"id": 3, "name": "Bob Johnson", "age": 19, "grade": "A"},
                    {"id": 4, "name": "Alice Brown", "age": 22, "grade": "C"},
                    {"id": 5, "name": "Charlie Wilson", "age": 20, "grade": "B"}
                ],
                "row_count": 5
            }
        elif "users" in query_clean and "active" in query_clean:
            return {
                "columns": ["id", "username", "email", "status"],
                "data": [
                    {"id": 1, "username": "john_doe", "email": "john@example.com", "status": "active"},
                    {"id": 3, "username": "jane_smith", "email": "jane@example.com", "status": "active"}
                ],
                "row_count": 2
            }
        elif "products" in query_clean and "price" in query_clean:
            return {
                "columns": ["id", "name", "price", "category"],
                "data": [
                    {"id": 1, "name": "Laptop", "price": 999.99, "category": "Electronics"},
                    {"id": 2, "name": "Phone", "price": 699.99, "category": "Electronics"},
                    {"id": 3, "name": "Tablet", "price": 399.99, "category": "Electronics"}
                ],
                "row_count": 3
            }
        elif "select" in query_clean:
            # Generic SELECT query response
            return {
                "columns": ["result", "query"],
                "data": [
                    {"result": "Demo query executed successfully", "query": query},
                    {"result": "This is simulated data from demo mode", "query": ""}
                ],
                "row_count": 2
            }
        else:
            # For non-SELECT queries or unknown tables
            return {
                "affected_rows": 1,
                "message": "Query executed successfully in demo mode"
            }