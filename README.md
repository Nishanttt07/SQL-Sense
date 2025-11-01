# SQL-Sense: AI-Powered Universal Database Assistant

SQL-Sense is a full-stack Flask application that transforms natural language into executable SQL and NoSQL queries using Google's Gemini AI.

## 🚀 Features

- **Multi-Database Support**: MySQL, Supabase (PostgreSQL), and Firebase
- **AI-Powered Query Generation**: Uses Google Gemini AI for intelligent query creation
- **Secure Credential Handling**: Database credentials are never stored, only used for temporary connections
- **Schema Discovery**: Automatically detects and uses your database schema
- **Query Review & Editing**: Generated queries are editable before execution
- **Query History**: Keeps track of your recent queries

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd SQL-Sense

**Important**
   please create config.py file in root directory and then add below line
   GEMINI_API_KEY = ""  # Replace with your actual API key