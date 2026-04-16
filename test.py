import firebase_admin
from firebase_admin import credentials, firestore
import json
import tempfile
import os
from datetime import datetime

# Paste your Firebase JSON key locally (not online)
firebase_json = {
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "your-private-key-id",
  "private_key": "-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY_HERE\n-----END PRIVATE KEY-----\n",
  "client_email": "firebase-adminsdk-xxx@your-project.iam.gserviceaccount.com",
  "client_id": "your-client-id",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-xxx%40your-project.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}


# --- Helper function to convert non-serializable objects ---
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

# Write JSON to a temp file
with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w") as temp_json:
    json.dump(firebase_json, temp_json)
    temp_json_path = temp_json.name

try:
    # Initialize Firebase
    cred = credentials.Certificate(temp_json_path)
    firebase_admin.initialize_app(cred)

    # Initialize Firestore client
    db = firestore.client()

    # Fetch all collections and documents
    all_data = {}
    for collection in db.collections():
        col_name = collection.id
        all_data[col_name] = {}
        for doc in collection.stream():
            all_data[col_name][doc.id] = clean_for_json(doc.to_dict())

    # Print and save safely
    print("🔥 Firestore Database Schema & Data:")
    print(json.dumps(all_data, indent=4, ensure_ascii=False))

    with open("firestore_schema.json", "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=4, ensure_ascii=False)
    print("\n✅ Schema saved to firestore_schema.json")

finally:
    os.remove(temp_json_path)
