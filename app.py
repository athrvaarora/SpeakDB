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
        
        # Format just the query and result without extra text
        formatted_result = f"""
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
        # Relational Databases
        'postgresql': {
            'fields': ['host', 'port', 'username', 'password', 'database_name'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'postgresql://username:password@host:5432/database_name',
            'terminal_command': 'psql -h host -p 5432 -U username -d database_name'
        },
        'mysql': {
            'fields': ['host', 'port', 'username', 'password', 'database_name'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'mysql://username:password@host:3306/database_name',
            'terminal_command': 'mysql -h host -P 3306 -u username -p database_name'
        },
        'mariadb': {
            'fields': ['host', 'port', 'username', 'password', 'database_name'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'mysql://username:password@host:3306/database_name',
            'terminal_command': 'mysql -h host -P 3306 -u username -p database_name'
        },
        'sqlserver': {
            'fields': ['server_address', 'username', 'password', 'database_name'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'mssql://username:password@server_address/database_name',
            'terminal_command': 'sqlcmd -S server_address -U username -P password -d database_name'
        },
        'oracle': {
            'fields': ['host', 'port', 'service_name', 'username', 'password'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'oracle://username:password@host:1521/service_name',
            'terminal_command': 'sqlplus username/password@//host:1521/service_name'
        },
        'sqlite': {
            'fields': ['path_to_database_file'],
            'url_option': False,
            'terminal_command': 'sqlite3 path_to_database_file'
        },
        'redshift': {
            'fields': ['cluster_address', 'username', 'password', 'database_name'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'redshift://username:password@cluster_address:5439/database_name',
            'terminal_command': 'psql -h cluster_address -p 5439 -U username -d database_name'
        },
        'cloudsql': {
            'fields': ['instance_name', 'username', 'password'],
            'url_option': False,
            'terminal_command': 'gcloud sql connect instance-name --user=username'
        },
        'db2': {
            'fields': ['username', 'password', 'database_name'],
            'url_option': False,
            'terminal_command': 'db2 connect to database_name user username using password'
        },
        'teradata': {
            'fields': ['hostname', 'username', 'password'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'teradatasql://username:password@hostname',
            'terminal_command': 'bteq .logon hostname/username,password'
        },
        'saphana': {
            'fields': ['host', 'port', 'username', 'password', 'database_name'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'hdb://host:port/?databaseName=database_name',
            'terminal_command': 'hdbsql -n host:port -u username -p password -d database_name'
        },
        'planetscale': {
            'fields': ['database_name', 'branch_name'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'mysql://username:password@aws.connect.psdb.cloud/database_name',
            'terminal_command': 'pscale connect database_name branch_name'
        },
        'vertica': {
            'fields': ['hostname', 'port', 'username', 'password', 'database_name'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'vertica://username:password@hostname:5433/database_name',
            'terminal_command': 'vsql -h hostname -p port -U username -w password -d database_name'
        },
        
        # NoSQL Databases
        'mongodb': {
            'fields': ['hostname', 'port', 'username', 'password', 'database_name'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'mongodb://username:password@hostname:port/database_name',
            'terminal_command': 'mongo "mongodb://username:password@hostname:port/database_name"'
        },
        'cassandra': {
            'fields': ['hostname', 'port', 'username', 'password'],
            'url_option': False,
            'terminal_command': 'cqlsh hostname port -u username -p password'
        },
        'redis': {
            'fields': ['hostname', 'port', 'password'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'redis://:password@hostname:port',
            'terminal_command': 'redis-cli -h hostname -p port -a password'
        },
        'elasticsearch': {
            'fields': ['hostname', 'port', 'username', 'password'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'https://username:password@hostname:port',
            'terminal_command': 'curl -X GET "hostname:port/_search" -H "Content-Type: application/json" -d\'{"query": {"match_all": {}}}\''
        },
        'dynamodb': {
            'fields': ['access_key', 'secret_key', 'region', 'endpoint_url'],
            'url_option': False,
            'terminal_command': 'aws dynamodb list-tables --endpoint-url endpoint_url'
        },
        'couchbase': {
            'fields': ['hostname', 'username', 'password', 'bucket_name'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'couchbase://username:password@hostname/bucket_name',
            'terminal_command': 'cbc-pillowfight -U couchbase://hostname/bucket_name -u username -P password'
        },
        'neo4j': {
            'fields': ['bolt_url', 'username', 'password'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'bolt://hostname:7687',
            'terminal_command': 'cypher-shell -a bolt_url -u username -p password'
        },
        
        # Data Warehouses
        'snowflake': {
            'fields': ['account_identifier', 'username', 'password', 'database_name', 'schema_name', 'role_name'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'snowflake://username:password@account_identifier/database_name/schema_name?role=role_name',
            'terminal_command': 'snowsql -a account_identifier -u username -d database_name -s schema_name -r role_name'
        },
        'bigquery': {
            'fields': ['project_id', 'dataset'],
            'url_option': False,
            'terminal_command': 'bq query --use_legacy_sql=false \'SELECT * FROM project_id.dataset.table LIMIT 10\''
        },
        'synapse': {
            'fields': ['server_name', 'database_name', 'username', 'password'],
            'url_option': False,
            'terminal_command': 'sqlcmd -S server_name.sql.azuresynapse.net -d database_name -U username -P password'
        },
        
        # Graph Databases
        'tigergraph': {
            'fields': ['graph_name', 'username', 'password'],
            'url_option': False,
            'terminal_command': 'gsql -g graph_name'
        },
        'neptune': {
            'fields': ['neptune_endpoint', 'aws_credentials'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'wss://your-neptune-endpoint:8182/gremlin',
            'terminal_command': 'curl -X POST https://your-neptune-endpoint:port/sparql -d "query=SELECT ?s ?p ?o WHERE {?s ?p ?o} LIMIT 10"'
        },
        
        # Cloud Databases
        'cosmosdb': {
            'fields': ['account_name', 'database_name', 'container_name'],
            'url_option': False,
            'terminal_command': 'az cosmosdb sql query --account-name account_name --database-name database_name --container-name container_name --query-text "SELECT * FROM c"'
        },
        'firestore': {
            'fields': ['project_id', 'collection'],
            'url_option': False,
            'terminal_command': 'firebase firestore:get --project project_id collections/documents'
        },
        'supabase': {
            'fields': ['supabase_url', 'supabase_key'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'postgres://postgres:[YOUR-PASSWORD]@db.supabase.co:5432/postgres',
            'terminal_command': 'psql "postgres://postgres:password@db.supabase.co:5432/postgres"'
        },
        'heroku': {
            'fields': ['app_name'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'postgres://user:pass@ec2-123.compute-1.amazonaws.com:5432/db',
            'terminal_command': 'heroku pg:psql postgresql-shaped-12345 --app app_name'
        },
        'crunchybridge': {
            'fields': ['connection_string'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'postgresql://username:password@db.crunchybridge.com:5432/database_name',
            'terminal_command': 'psql "postgresql://username:password@db.crunchybridge.com:5432/database_name"'
        },
        'neon': {
            'fields': ['connection_string'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'postgres://username:password@hostname:5432/database_name?sslmode=require',
            'terminal_command': 'psql "postgres://username:password@hostname:5432/database_name?sslmode=require"'
        },
        
        # Time Series Databases
        'influxdb': {
            'fields': ['host', 'port', 'username', 'password'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'http://host:8086?token=xxx&org=yyy',
            'terminal_command': 'influx -host host -port 8086 -username username -password password'
        },
        'timescaledb': {
            'fields': ['host', 'port', 'username', 'password', 'database_name'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'postgresql://username:password@host:5432/database_name',
            'terminal_command': 'psql -h host -p 5432 -U username -d database_name'
        },
        'kdb': {
            'fields': ['path_to_script', 'port'],
            'url_option': False,
            'terminal_command': 'q path_to_script.q -p port'
        },
        
        # Specialized Systems
        'prometheus': {
            'fields': ['hostname', 'port'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'http://hostname:9090',
            'terminal_command': 'curl -G \'http://hostname:9090/api/v1/query\' --data-urlencode \'query=up\''
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
