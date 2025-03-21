import os
import logging
import json
import uuid
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from openai_service import generate_query, format_response
from database_connectors import get_connector, test_connection
from models import db, Chat, ChatMessage
from utils import DateTimeEncoder

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_key")

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the database
db.init_app(app)

with app.app_context():
    db.create_all()

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

@app.route('/test_env_db')
def test_env_db():
    """Test the connection to the PostgreSQL database using environment variables"""
    try:
        # Create empty credentials dict for PostgreSQL
        credentials = {}
        connector = get_connector('postgresql', credentials)
        connector.connect()
        
        # Test a simple query
        result, success, error = connector.execute_query("SELECT current_database(), current_user;")
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Successfully connected to the database',
                'result': result
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Failed to execute query: {error}'
            })
    except Exception as e:
        logger.exception("Error testing database connection")
        return jsonify({
            'success': False,
            'message': f'Error connecting to database: {str(e)}'
        })

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
                db_name=credentials.get('db_name', db_type.upper()),
                db_credentials=json.dumps(credentials)  # Store credentials as JSON string
            )
            
            # Save the chat to the database
            db.session.add(chat)
            db.session.commit()
            
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
        if 'chat_id' not in session:
            return jsonify({
                'success': False,
                'message': "No active chat session"
            })
        
        chat_id = session['chat_id']
        
        # Query the database for the chat messages
        messages = db.session.query(ChatMessage).filter(ChatMessage.chat_id == chat_id).order_by(ChatMessage.created_at).all()
        
        # Convert the messages to dictionaries
        message_list = [message.to_dict() for message in messages]
        
        # Use the custom DateTimeEncoder to handle datetime objects
        return app.response_class(
            response=json.dumps({
                'success': True,
                'history': message_list
            }, cls=DateTimeEncoder),
            status=200,
            mimetype='application/json'
        )
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
        # Query the database for all chats, ordered by most recent first
        chats = db.session.query(Chat).order_by(Chat.updated_at.desc()).all()
        
        # Convert the chats to dictionaries
        chat_list = [chat.to_dict() for chat in chats]
        
        # Use custom DateTimeEncoder to handle datetime objects
        return app.response_class(
            response=json.dumps({
                'success': True,
                'chats': chat_list
            }, cls=DateTimeEncoder),
            status=200,
            mimetype='application/json'
        )
    except Exception as e:
        logger.exception("Error getting previous chats")
        return jsonify({
            'success': False,
            'message': f"Error getting previous chats: {str(e)}"
        })

@app.route('/load_chat/<chat_id>', methods=['GET'])
def load_chat(chat_id):
    """Load a specific chat session"""
    try:
        # Check if the chat exists
        chat = db.session.query(Chat).filter(Chat.id == chat_id).first()
        
        if not chat:
            return jsonify({
                'success': False,
                'message': f"Chat with ID {chat_id} not found"
            })
        
        # Store the chat ID in the session
        session['chat_id'] = chat_id
        
        # Restore the database credentials for this chat
        if chat.db_credentials:
            try:
                credentials = json.loads(chat.db_credentials)
                session['database_credentials'] = {
                    'type': chat.db_type,
                    'credentials': credentials
                }
                
                # Test the connection to make sure it's still valid
                success, message = test_connection(chat.db_type, credentials)
                
                if not success:
                    # If the connection fails, we should inform the user but still load the chat
                    logger.warning(f"Failed to reconnect to database: {message}")
                    return app.response_class(
                        response=json.dumps({
                            'success': True,
                            'chat': chat.to_dict(),
                            'warning': f"Could not reconnect to the database: {message}"
                        }, cls=DateTimeEncoder),
                        status=200,
                        mimetype='application/json'
                    )
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in db_credentials for chat {chat_id}")
                return app.response_class(
                    response=json.dumps({
                        'success': True,
                        'chat': chat.to_dict(),
                        'warning': "Could not restore database connection. The stored credentials are invalid."
                    }, cls=DateTimeEncoder),
                    status=200,
                    mimetype='application/json'
                )
        else:
            return app.response_class(
                response=json.dumps({
                    'success': True,
                    'chat': chat.to_dict(),
                    'warning': "No database credentials were stored with this chat."
                }, cls=DateTimeEncoder),
                status=200,
                mimetype='application/json'
            )
        
        return app.response_class(
            response=json.dumps({
                'success': True,
                'chat': chat.to_dict()
            }, cls=DateTimeEncoder),
            status=200,
            mimetype='application/json'
        )
    except Exception as e:
        logger.exception("Error loading chat")
        return jsonify({
            'success': False,
            'message': f"Error loading chat: {str(e)}"
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
        
        if 'chat_id' not in session:
            return jsonify({
                'success': False,
                'message': "No active chat session. Please start a new chat."
            })
        
        data = request.json
        user_query = data.get('query')
        db_info = session['database_credentials']
        db_type = db_info['type']
        credentials = db_info['credentials']
        chat_id = session['chat_id']
        
        # Get the database connector
        connector = get_connector(db_type, credentials)
        
        # Generate a query using OpenAI GPT
        success, query, explanation = generate_query(user_query, db_type, connector.get_schema())
        
        if not success:
            # Save the error message
            error_message = ChatMessage(
                chat_id=chat_id,
                query=user_query,
                error=explanation,
                is_error=True
            )
            db.session.add(error_message)
            db.session.commit()
            
            return app.response_class(
                response=json.dumps({
                    'success': False,
                    'message': explanation
                }, cls=DateTimeEncoder),
                status=400,
                mimetype='application/json'
            )
        
        # Execute the query against the database
        result, execution_success, error_message = connector.execute_query(query)
        
        if not execution_success:
            # Save the error to the database
            error_entry = ChatMessage(
                chat_id=chat_id,
                query=user_query,
                generated_query=query,
                explanation=explanation,
                error=error_message,
                is_error=True
            )
            db.session.add(error_entry)
            db.session.commit()
            
            return app.response_class(
                response=json.dumps({
                    'success': False,
                    'message': f"Query generation succeeded, but execution failed: {error_message}",
                    'query': query,
                    'explanation': explanation
                }, cls=DateTimeEncoder),
                status=400,
                mimetype='application/json'
            )
        
        # Format the response and include the generated query
        formatted_result = f"""
## Generated Query
```sql
{query}
```

{format_response(result, user_query)}
"""
        
        # Save the successful query to the database
        chat_message = ChatMessage(
            chat_id=chat_id,
            query=user_query,
            generated_query=query,
            explanation=explanation,
            result=formatted_result,
            is_error=False
        )
        db.session.add(chat_message)
        
        # Update the timestamp on the chat
        chat = db.session.query(Chat).filter(Chat.id == chat_id).first()
        chat.updated_at = datetime.now()
        
        db.session.commit()
        
        return app.response_class(
            response=json.dumps({
                'success': True,
                'query': query,
                'explanation': explanation,
                'result': formatted_result
            }, cls=DateTimeEncoder),
            status=200,
            mimetype='application/json'
        )
    except Exception as e:
        logger.exception("Error processing query")
        
        # If we have a chat ID, save the error
        if 'chat_id' in session:
            try:
                error_message = ChatMessage(
                    chat_id=session['chat_id'],
                    query=user_query if 'user_query' in locals() else "Unknown query",
                    error=str(e),
                    is_error=True
                )
                db.session.add(error_message)
                db.session.commit()
            except Exception as inner_e:
                logger.exception("Error saving error message")
        
        return app.response_class(
            response=json.dumps({
                'success': False,
                'message': f"Error processing query: {str(e)}"
            }, cls=DateTimeEncoder),
            status=500,
            mimetype='application/json'
        )

@app.route('/get_required_credentials', methods=['GET'])
def get_required_credentials():
    """Get the required credentials for a specific database type"""
    db_type = request.args.get('db_type')
    
    # Define the credentials required for each database type
    credential_requirements = {
        'postgresql': {
            'fields': ['host', 'port', 'username', 'password', 'db_name'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'postgresql://username:password@host:port/db_name'
        },
        'mysql': {
            'fields': ['host', 'username', 'password', 'db_name'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'mysql://username:password@host/db_name'
        },
        'sqlserver': {
            'fields': ['host', 'instance', 'username', 'password'],
            'url_option': False
        },
        'oracle': {
            'fields': ['host', 'port', 'service_name', 'username', 'password'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'oracle://username:password@host:port/service_name'
        },
        'sqlite': {
            'fields': ['file_path'],
            'url_option': False
        },
        'redshift': {
            'fields': ['cluster_id', 'region', 'username', 'password', 'db_name'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'redshift://username:password@cluster_id.region.redshift.amazonaws.com:5439/db_name'
        },
        'cloudsql': {
            'fields': ['project_id', 'region', 'instance', 'username', 'password'],
            'url_option': False
        },
        'mariadb': {
            'fields': ['host', 'username', 'password', 'db_name'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'mariadb://username:password@host/db_name'
        },
        'db2': {
            'fields': ['host', 'port', 'username', 'password', 'db_name'],
            'url_option': False
        },
        'mongodb': {
            'fields': ['host', 'port', 'username', 'password', 'auth_db'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'mongodb://username:password@host:port/auth_db'
        },
        'cassandra': {
            'fields': ['host', 'port', 'username', 'password', 'keyspace'],
            'url_option': False
        },
        'redis': {
            'fields': ['host', 'port', 'password'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'redis://:password@host:port'
        },
        'elasticsearch': {
            'fields': ['host', 'port', 'username', 'password'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'https://username:password@host:port'
        },
        'dynamodb': {
            'fields': ['access_key', 'secret_key', 'region'],
            'url_option': False
        },
        'couchbase': {
            'fields': ['host', 'username', 'password', 'bucket'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'couchbase://username:password@host/bucket'
        },
        'neo4j': {
            'fields': ['uri', 'username', 'password'],
            'url_option': False
        },
        'snowflake': {
            'fields': ['account', 'username', 'password', 'warehouse', 'db_name'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'snowflake://username:password@account/db_name/warehouse'
        },
        'bigquery': {
            'fields': ['project_id', 'dataset'],
            'url_option': False
        },
        'synapse': {
            'fields': ['server', 'username', 'password', 'db_name'],
            'url_option': False
        },
        'cosmosdb': {
            'fields': ['account_uri', 'primary_key'],
            'url_option': False
        },
        'firestore': {
            'fields': ['project_id', 'collection'],
            'url_option': False
        },
        'influxdb': {
            'fields': ['host', 'port', 'token', 'org', 'bucket'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'influxdb://host:port?token=token&org=org&bucket=bucket'
        }
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
