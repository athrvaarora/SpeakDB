import os
import logging
import json
import uuid
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from openai_service import generate_query, format_response
from database_connectors import get_connector, test_connection
from models import Chat, ChatMessage

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_key")

# Routes
@app.route('/')
def index():
    """Render the landing page with database selection"""
    # Clear any existing session data when landing on homepage
    if 'database_credentials' in session:
        session.pop('database_credentials')
    if 'chat_id' in session:
        session.pop('chat_id')
    return render_template('index.html')

@app.route('/test_connection', methods=['POST'])
def test_db_connection():
    """Test connection to the selected database"""
    try:
        data = request.json
        db_type = data.get('db_type')
        credentials = data.get('credentials')
        
        # Store the credentials in the session for future use
        session['database_credentials'] = {
            'type': db_type,
            'credentials': credentials
        }
        
        # Test the connection
        success, message = test_connection(db_type, credentials)
        
        if success:
            # Generate a new chat ID and store it in the session
            chat_id = str(uuid.uuid4())
            session['chat_id'] = chat_id
            
            # Create a new chat record
            chat = Chat(
                id=chat_id,
                db_type=db_type,
                db_name=credentials.get('db_name', 'N/A')
            )
            # In a real application, we would save this to a database
            
            return jsonify({
                'success': True,
                'message': message,
                'chat_id': chat_id
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            })
    except Exception as e:
        logger.exception("Error testing connection")
        return jsonify({
            'success': False,
            'message': f"Error testing connection: {str(e)}"
        })

@app.route('/chat')
def chat():
    """Render the chat interface"""
    # Ensure we have database credentials and a chat ID
    if 'database_credentials' not in session or 'chat_id' not in session:
        return redirect(url_for('index'))
    
    return render_template('chat.html')

@app.route('/get_chat_history', methods=['GET'])
def get_chat_history():
    """Get the chat history for the current chat session"""
    try:
        # In a real application, we would fetch chat history from a database
        # For this MVP, we'll return an empty history
        return jsonify({
            'success': True,
            'history': []
        })
    except Exception as e:
        logger.exception("Error getting chat history")
        return jsonify({
            'success': False,
            'message': f"Error getting chat history: {str(e)}"
        })

@app.route('/get_previous_chats', methods=['GET'])
def get_previous_chats():
    """Get a list of previous chat sessions"""
    try:
        # In a real application, we would fetch previous chats from a database
        # For this MVP, we'll return an empty list
        return jsonify({
            'success': True,
            'chats': []
        })
    except Exception as e:
        logger.exception("Error getting previous chats")
        return jsonify({
            'success': False,
            'message': f"Error getting previous chats: {str(e)}"
        })

@app.route('/process_query', methods=['POST'])
def process_query():
    """Process a natural language query using GPT and execute it against the database"""
    try:
        if 'database_credentials' not in session:
            return jsonify({
                'success': False,
                'message': "No database connection. Please reconnect."
            })
        
        data = request.json
        user_query = data.get('query')
        db_info = session['database_credentials']
        db_type = db_info['type']
        credentials = db_info['credentials']
        
        # Get the database connector
        connector = get_connector(db_type, credentials)
        
        # Generate a query using OpenAI GPT
        success, query, explanation = generate_query(user_query, db_type, connector.get_schema())
        
        if not success:
            return jsonify({
                'success': False,
                'message': explanation
            })
        
        # Execute the query against the database
        result, execution_success, error_message = connector.execute_query(query)
        
        if not execution_success:
            return jsonify({
                'success': False,
                'message': f"Query generation succeeded, but execution failed: {error_message}",
                'query': query,
                'explanation': explanation
            })
        
        # Format the response
        formatted_result = format_response(result, user_query)
        
        # In a real application, we would save the message to the chat history
        
        return jsonify({
            'success': True,
            'query': query,
            'explanation': explanation,
            'result': formatted_result
        })
    except Exception as e:
        logger.exception("Error processing query")
        return jsonify({
            'success': False,
            'message': f"Error processing query: {str(e)}"
        })

@app.route('/get_required_credentials', methods=['GET'])
def get_required_credentials():
    """Get the required credentials for a specific database type"""
    db_type = request.args.get('db_type')
    
    # Define the credentials required for each database type
    credential_requirements = {
        'postgresql': ['host', 'port', 'username', 'password', 'db_name'],
        'mysql': ['host', 'username', 'password', 'db_name'],
        'sqlserver': ['host', 'instance', 'username', 'password'],
        'oracle': ['host', 'port', 'service_name', 'username', 'password'],
        'sqlite': ['file_path'],
        'redshift': ['cluster_id', 'region', 'username', 'password', 'db_name'],
        'cloudsql': ['project_id', 'region', 'instance', 'username', 'password'],
        'mariadb': ['host', 'username', 'password', 'db_name'],
        'db2': ['host', 'port', 'username', 'password', 'db_name'],
        'mongodb': ['host', 'port', 'username', 'password', 'auth_db'],
        'cassandra': ['host', 'port', 'username', 'password', 'keyspace'],
        'redis': ['host', 'port', 'password'],
        'elasticsearch': ['host', 'port', 'username', 'password'],
        'dynamodb': ['access_key', 'secret_key', 'region'],
        'couchbase': ['host', 'username', 'password', 'bucket'],
        'neo4j': ['uri', 'username', 'password'],
        'snowflake': ['account', 'username', 'password', 'warehouse', 'db_name'],
        'bigquery': ['project_id', 'dataset'],
        'synapse': ['server', 'username', 'password', 'db_name'],
        'cosmosdb': ['account_uri', 'primary_key'],
        'firestore': ['project_id', 'collection'],
        'influxdb': ['host', 'port', 'token', 'org', 'bucket']
    }
    
    if db_type in credential_requirements:
        return jsonify({
            'success': True,
            'credentials': credential_requirements[db_type]
        })
    else:
        return jsonify({
            'success': False,
            'message': f"Unknown database type: {db_type}"
        })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
