# testfirebase.py

import firebase_admin
from firebase_admin import credentials, firestore
import json
import tempfile
import os
from datetime import datetime

def clean_for_json(obj):
    """Recursively converts Firestore data into JSON-safe format."""
    if isinstance(obj, dict):
        return {k: clean_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_for_json(v) for v in obj]
    elif isinstance(obj, datetime):
        return obj.isoformat()  # convert datetime to string
    else:
        return obj

def connect_and_load_schema(firebase_json):
    """
    Connect to Firebase and load schema using provided JSON credentials
    Returns: (success, message, schema_data)
    """
    temp_file_path = None
    try:
        # Write JSON to a temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w") as temp_json:
            json.dump(firebase_json, temp_json)
            temp_file_path = temp_json.name

        # Initialize Firebase
        cred = credentials.Certificate(temp_file_path)
        firebase_admin.initialize_app(cred)

        # Initialize Firestore client
        db = firestore.client()

        # Fetch all collections and documents
        all_data = {}
        collections = db.collections()
        
        for collection in collections:
            col_name = collection.id
            all_data[col_name] = {}
            try:
                docs = collection.stream()
                for doc in docs:
                    all_data[col_name][doc.id] = clean_for_json(doc.to_dict())
            except Exception as e:
                print(f"Warning: Could not fetch documents from collection {col_name}: {str(e)}")
                all_data[col_name] = {"error": f"Failed to load documents: {str(e)}"}

        # Save schema to file
        with open("firestore_schema.json", "w", encoding="utf-8") as f:
            json.dump(all_data, f, indent=4, ensure_ascii=False)

        return True, "Firebase connection successful and schema loaded", all_data

    except Exception as e:
        return False, f"Connection failed: {str(e)}", None
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except:
                pass
        
        # Clean up Firebase app
        try:
            if firebase_admin._apps:
                firebase_admin.delete_app(firebase_admin.get_app())
        except:
            pass

# For standalone testing
if __name__ == "__main__":
    # This is just for testing - in production, JSON will come from frontend
    sample_firebase_json = {
        "type": "service_account",
        "project_id": "your-project-id",
        "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
        "client_email": "firebase-adminsdk@your-project.iam.gserviceaccount.com",
        # ... other fields
    }
    
    print("🔧 Testing Firebase connection...")
    success, message, schema = connect_and_load_schema(sample_firebase_json)
    if success:
        print("✅ " + message)
        print(f"📊 Loaded {len(schema)} collections")
    else:
        print("❌ " + message)