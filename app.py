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
            'terminal_command': 'psql -h localhost -p 5432 -U username -d database_name',
            'env_variables': [
                'POSTGRES_HOST=localhost',
                'POSTGRES_PORT=5432',
                'POSTGRES_USER=username',
                'POSTGRES_PASSWORD=your_password',
                'POSTGRES_DB=database_name',
                'DATABASE_URL=postgresql://username:password@localhost:5432/database_name'
            ]
        },
        'mysql': {
            'fields': ['host', 'port', 'username', 'password', 'database_name'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'mysql://username:password@host:3306/database_name',
            'terminal_command': 'mysql -h localhost -P 3306 -u username -p database_name',
            'env_variables': [
                'MYSQL_HOST=localhost',
                'MYSQL_PORT=3306',
                'MYSQL_USER=username',
                'MYSQL_PASSWORD=your_password',
                'MYSQL_DATABASE=database_name',
                'MYSQL_URL=mysql://username:password@localhost:3306/database_name'
            ]
        },
        'mariadb': {
            'fields': ['host', 'port', 'username', 'password', 'database_name'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'mysql://username:password@host:3306/database_name',
            'terminal_command': 'mysql -h localhost -P 3306 -u username -p database_name',
            'env_variables': [
                'MARIADB_HOST=localhost',
                'MARIADB_PORT=3306',
                'MARIADB_USER=username',
                'MARIADB_PASSWORD=your_password',
                'MARIADB_DATABASE=database_name',
                'MARIADB_URL=mysql://username:password@localhost:3306/database_name'
            ]
        },
        'sqlserver': {
            'fields': ['server_address', 'username', 'password', 'database_name'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'mssql://username:password@localhost/database_name',
            'terminal_command': 'sqlcmd -S localhost -U username -P password -d database_name',
            'env_variables': [
                'MSSQL_SERVER=localhost',
                'MSSQL_USER=username',
                'MSSQL_PASSWORD=your_password',
                'MSSQL_DATABASE=database_name',
                'MSSQL_CONNECTION_STRING=mssql://username:password@localhost/database_name'
            ]
        },
        'oracle': {
            'fields': ['host', 'port', 'service_name', 'username', 'password'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'oracle://username:password@localhost:1521/service_name',
            'terminal_command': 'sqlplus username/password@//localhost:1521/service_name',
            'env_variables': [
                'ORACLE_HOST=localhost',
                'ORACLE_PORT=1521',
                'ORACLE_SERVICE_NAME=service_name',
                'ORACLE_USERNAME=username',
                'ORACLE_PASSWORD=your_password',
                'ORACLE_CONNECTION_STRING=oracle://username:password@localhost:1521/service_name'
            ]
        },
        'sqlite': {
            'fields': ['path_to_database_file'],
            'url_option': False,
            'terminal_command': 'sqlite3 path_to_database_file',
            'env_variables': [
                'SQLITE_DATABASE_PATH=/path/to/database_file.db'
            ]
        },
        'redshift': {
            'fields': ['cluster_address', 'username', 'password', 'database_name'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'redshift://username:password@cluster_address:5439/database_name',
            'terminal_command': 'psql -h cluster_address -p 5439 -U username -d database_name',
            'env_variables': [
                'REDSHIFT_CLUSTER=cluster_address',
                'REDSHIFT_USER=username',
                'REDSHIFT_PASSWORD=your_password',
                'REDSHIFT_DATABASE=database_name',
                'REDSHIFT_PORT=5439',
                'REDSHIFT_URL=redshift://username:password@cluster_address:5439/database_name'
            ]
        },
        'cloudsql': {
            'fields': ['instance_name', 'username', 'password'],
            'url_option': False,
            'terminal_command': 'gcloud sql connect instance-name --user=username',
            'env_variables': [
                'CLOUDSQL_INSTANCE=instance-name',
                'CLOUDSQL_USER=username',
                'CLOUDSQL_PASSWORD=your_password',
                'GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json'
            ],
            'auth_popup': True,
            'auth_type': 'google'
        },
        'db2': {
            'fields': ['username', 'password', 'database_name'],
            'url_option': False,
            'terminal_command': 'db2 connect to database_name user username using password',
            'env_variables': [
                'DB2_USERNAME=username',
                'DB2_PASSWORD=your_password',
                'DB2_DATABASE=database_name'
            ]
        },
        'teradata': {
            'fields': ['hostname', 'username', 'password'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'teradatasql://username:password@hostname',
            'terminal_command': 'bteq .logon hostname/username,password',
            'env_variables': [
                'TERADATA_HOST=hostname',
                'TERADATA_USERNAME=username',
                'TERADATA_PASSWORD=your_password',
                'TERADATA_URL=teradatasql://username:password@hostname'
            ]
        },
        'saphana': {
            'fields': ['host', 'port', 'username', 'password', 'database_name'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'hdb://host:port/?databaseName=database_name',
            'terminal_command': 'hdbsql -n host:port -u username -p password -d database_name',
            'env_variables': [
                'SAPHANA_HOST=host',
                'SAPHANA_PORT=port',
                'SAPHANA_USERNAME=username',
                'SAPHANA_PASSWORD=your_password',
                'SAPHANA_DATABASE=database_name',
                'SAPHANA_URL=hdb://host:port/?databaseName=database_name'
            ]
        },
        'planetscale': {
            'fields': ['database_name', 'branch_name'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'mysql://username:password@aws.connect.psdb.cloud/database_name',
            'terminal_command': 'pscale connect database_name branch_name',
            'env_variables': [
                'PLANETSCALE_DATABASE=database_name',
                'PLANETSCALE_BRANCH=branch_name',
                'PLANETSCALE_USERNAME=username',
                'PLANETSCALE_PASSWORD=your_password',
                'PLANETSCALE_URL=mysql://username:password@aws.connect.psdb.cloud/database_name'
            ]
        },
        'vertica': {
            'fields': ['hostname', 'port', 'username', 'password', 'database_name'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'vertica://username:password@hostname:5433/database_name',
            'terminal_command': 'vsql -h hostname -p port -U username -w password -d database_name',
            'env_variables': [
                'VERTICA_HOST=hostname',
                'VERTICA_PORT=5433',
                'VERTICA_USERNAME=username',
                'VERTICA_PASSWORD=your_password',
                'VERTICA_DATABASE=database_name',
                'VERTICA_URL=vertica://username:password@hostname:5433/database_name'
            ]
        },
        
        # NoSQL Databases
        'mongodb': {
            'fields': ['hostname', 'port', 'username', 'password', 'database_name'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'mongodb://username:password@localhost:27017/database_name',
            'terminal_command': 'mongo "mongodb://username:password@localhost:27017/database_name"',
            'env_variables': [
                'MONGO_URI=mongodb://username:password@localhost:27017/database_name',
                'MONGO_HOST=localhost',
                'MONGO_PORT=27017',
                'MONGO_USER=username',
                'MONGO_PASSWORD=your_password',
                'MONGO_DATABASE=database_name'
            ]
        },
        'cassandra': {
            'fields': ['hostname', 'port', 'username', 'password'],
            'url_option': False,
            'terminal_command': 'cqlsh hostname port -u username -p password',
            'env_variables': [
                'CASSANDRA_HOST=hostname',
                'CASSANDRA_PORT=port',
                'CASSANDRA_USERNAME=username',
                'CASSANDRA_PASSWORD=your_password',
                'CASSANDRA_KEYSPACE=your_keyspace'
            ]
        },
        'redis': {
            'fields': ['hostname', 'port', 'password'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'redis://:password@localhost:6379',
            'terminal_command': 'redis-cli -h localhost -p 6379 -a password',
            'env_variables': [
                'REDIS_HOST=localhost',
                'REDIS_PORT=6379',
                'REDIS_PASSWORD=your_password',
                'REDIS_URL=redis://:password@localhost:6379'
            ]
        },
        'elasticsearch': {
            'fields': ['hostname', 'port', 'username', 'password'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'https://username:password@localhost:9200',
            'terminal_command': 'curl -X GET "localhost:9200/_search" -H "Content-Type: application/json" -d\'{"query": {"match_all": {}}}\'',
            'env_variables': [
                'ELASTICSEARCH_HOST=localhost',
                'ELASTICSEARCH_PORT=9200',
                'ELASTICSEARCH_USERNAME=username',
                'ELASTICSEARCH_PASSWORD=your_password',
                'ELASTICSEARCH_URL=https://username:password@localhost:9200'
            ]
        },
        'dynamodb': {
            'fields': ['access_key', 'secret_key', 'region', 'endpoint_url'],
            'url_option': False,
            'terminal_command': '# First configure AWS credentials (interactive)\naws configure\n# Then access DynamoDB\naws dynamodb list-tables --endpoint-url http://localhost:8000',
            'env_variables': [
                'AWS_ACCESS_KEY_ID=your_access_key',
                'AWS_SECRET_ACCESS_KEY=your_secret_key',
                'AWS_REGION=your_region',
                'AWS_DYNAMODB_ENDPOINT=http://localhost:8000'
            ],
            'auth_popup': True,
            'auth_type': 'aws'
        },
        'couchbase': {
            'fields': ['hostname', 'username', 'password', 'bucket_name'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'couchbase://username:password@localhost:8091/bucket_name',
            'terminal_command': 'cbc-pillowfight -U couchbase://localhost:8091/bucket_name -u username -P password',
            'env_variables': [
                'COUCHBASE_HOST=localhost',
                'COUCHBASE_PORT=8091',
                'COUCHBASE_USERNAME=username',
                'COUCHBASE_PASSWORD=your_password',
                'COUCHBASE_BUCKET=bucket_name',
                'COUCHBASE_URL=couchbase://username:password@localhost:8091/bucket_name'
            ]
        },
        'neo4j': {
            'fields': ['bolt_url', 'username', 'password'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'bolt://localhost:7687',
            'terminal_command': 'cypher-shell -a bolt://localhost:7687 -u username -p password',
            'env_variables': [
                'NEO4J_BOLT_URL=bolt://localhost:7687',
                'NEO4J_USERNAME=username',
                'NEO4J_PASSWORD=your_password'
            ]
        },
        
        # Data Warehouses
        'snowflake': {
            'fields': ['account_identifier', 'username', 'password', 'database_name', 'schema_name', 'role_name'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'snowflake://username:password@account_identifier/database_name/schema_name?role=role_name',
            'terminal_command': 'snowsql -a account_identifier -u username -d database_name -s schema_name -r role_name',
            'env_variables': [
                'SNOWFLAKE_ACCOUNT=your_account_identifier',
                'SNOWFLAKE_USER=your_username',
                'SNOWFLAKE_PASSWORD=your_password',
                'SNOWFLAKE_DATABASE=your_database_name',
                'SNOWFLAKE_SCHEMA=your_schema_name',
                'SNOWFLAKE_ROLE=your_role_name'
            ]
        },
        'bigquery': {
            'fields': ['project_id', 'dataset', 'service_account_key_path'],
            'url_option': False,
            'terminal_command': '# First authenticate (interactive)\ngcloud auth login\n# Then query\nbq query --use_legacy_sql=false \'SELECT * FROM dataset.table LIMIT 10\'',
            'env_variables': [
                'GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json',
                'GCP_PROJECT_ID=your_project_id',
                'BIGQUERY_DATASET=your_dataset'
            ],
            'auth_popup': True,
            'auth_type': 'google'
        },
        'synapse': {
            'fields': ['server_name', 'database_name', 'username', 'password'],
            'url_option': False,
            'terminal_command': '# First login (interactive)\naz login\n# Then connect\nsqlcmd -S servername.sql.azuresynapse.net -d database_name -U username -P password',
            'env_variables': [
                'AZURE_SYNAPSE_SERVER=servername.sql.azuresynapse.net',
                'AZURE_SYNAPSE_DATABASE=database_name',
                'AZURE_SYNAPSE_USER=username',
                'AZURE_SYNAPSE_PASSWORD=your_password'
            ],
            'auth_popup': True,
            'auth_type': 'azure'
        },
        
        # Graph Databases
        'neo4j': {
            'fields': ['uri', 'username', 'password', 'database'],
            'url_option': True,
            'url_field': 'uri',
            'url_example': 'bolt://localhost:7687',
            'terminal_command': 'cypher-shell -a bolt://localhost:7687 -u username -p password -d database',
            'notes': 'Neo4j database connection requires the Bolt URL (neo4j:// or bolt://), username, and password. Database name is optional.',
            'env_variables': [
                'NEO4J_URI=bolt://localhost:7687',
                'NEO4J_USERNAME=username',
                'NEO4J_PASSWORD=your_password',
                'NEO4J_DATABASE=your_database_name'
            ]
        },
        'tigergraph': {
            'fields': ['endpoint', 'token', 'graph_name', 'username', 'password', 'secret'],
            'url_option': True,
            'url_field': 'endpoint',
            'url_example': 'https://your-instance.i.tgcloud.io',
            'terminal_command': '# First authenticate\ngadmin config get Authentication.TokenSecret\n# Then connect\ngsql -g graph_name',
            'notes': 'TigerGraph requires an endpoint URL. Provide either a token, username/password, or secret for authentication.',
            'env_variables': [
                'TIGERGRAPH_HOST=hostname',
                'TIGERGRAPH_USERNAME=username',
                'TIGERGRAPH_PASSWORD=your_password',
                'TIGERGRAPH_GRAPH=graph_name',
                'TIGERGRAPH_SECRET=your_auth_token_secret'
            ],
            'auth_popup': False
        },
        'neptune': {
            'fields': ['neptune_endpoint', 'aws_region', 'aws_access_key_id', 'aws_secret_access_key'],
            'url_option': True,
            'url_field': 'neptune_endpoint',
            'url_example': 'wss://your-neptune-endpoint:8182/gremlin',
            'terminal_command': '# First configure AWS credentials (interactive)\naws configure\n# Then query\ncurl -X POST https://your-neptune-endpoint:port/sparql -d "query=SELECT ?s ?p ?o WHERE {?s ?p ?o} LIMIT 10"',
            'env_variables': [
                'AWS_ACCESS_KEY_ID=your_access_key',
                'AWS_SECRET_ACCESS_KEY=your_secret_key',
                'AWS_REGION=your_region',
                'NEPTUNE_ENDPOINT=your-neptune-endpoint:port',
                'NEPTUNE_IAM_AUTH_ENABLED=True'
            ],
            'auth_popup': True,
            'auth_type': 'aws'
        },
        
        # Cloud Databases
        'cosmosdb': {
            'fields': ['endpoint', 'key', 'database', 'container'],
            'url_option': True,
            'url_field': 'endpoint',
            'url_example': 'https://your-account.documents.azure.com:443/',
            'terminal_command': '# First login to Azure (interactive)\naz login\n# Then query Cosmos DB\naz cosmosdb sql query --account-name account_name --database-name database_name --container-name container_name --query-text "SELECT * FROM c"',
            'notes': 'Requires AZURE_COSMOS_ENDPOINT, AZURE_COSMOS_KEY, AZURE_COSMOS_DATABASE, and AZURE_COSMOS_CONTAINER.',
            'env_variables': [
                'AZURE_COSMOS_ENDPOINT=https://your-account.documents.azure.com:443/',
                'AZURE_COSMOS_KEY=your_primary_key',
                'AZURE_COSMOS_DATABASE=database_name',
                'AZURE_COSMOS_CONTAINER=container_name'
            ],
            'auth_popup': True,
            'auth_type': 'azure'
        },
        'firestore': {
            'fields': ['api_key', 'auth_domain', 'project_id', 'storage_bucket', 'messaging_sender_id', 'app_id', 'measurement_id', 'database_url', 'service_account_key_path'],
            'url_option': False,
            'terminal_command': '# First authenticate (interactive Google login)\nfirebase login\n# Then access Firestore\nfirebase firestore:get --project project_id collections/documents',
            'notes': 'Requires Firebase credentials including project ID and service account key.',
            'env_variables': [
                'FIREBASE_API_KEY=your_api_key',
                'FIREBASE_AUTH_DOMAIN=your_project_id.firebaseapp.com',
                'FIREBASE_PROJECT_ID=your_project_id',
                'FIREBASE_STORAGE_BUCKET=your_project_id.appspot.com',
                'FIREBASE_MESSAGING_SENDER_ID=your_messaging_sender_id',
                'FIREBASE_APP_ID=your_app_id',
                'FIREBASE_MEASUREMENT_ID=your_measurement_id',
                'FIREBASE_DATABASE_URL=https://your_project_id.firebaseio.com',
                'FIREBASE_SERVICE_ACCOUNT_KEY_PATH=/path/to/serviceAccountKey.json'
            ],
            'auth_popup': True,
            'auth_type': 'google'
        },
        'supabase': {
            'fields': ['url', 'anon_key', 'service_role_key', 'db_url'],
            'url_option': True,
            'url_field': 'url',
            'url_example': 'https://your-project-id.supabase.co',
            'terminal_command': 'psql "postgres://postgres:password@db.supabase.co:5432/postgres"',
            'notes': 'Requires Supabase URL, anon key, and service role key.',
            'env_variables': [
                'SUPABASE_URL=https://your-project-id.supabase.co',
                'SUPABASE_ANON_KEY=your_anon_key',
                'SUPABASE_SERVICE_ROLE_KEY=your_service_role_key',
                'SUPABASE_DB_URL=postgres://postgres:password@db.supabase.co:5432/postgres'
            ]
        },
        'heroku': {
            'fields': ['api_key', 'app_name', 'database_url'],
            'url_option': True,
            'url_field': 'database_url',
            'url_example': 'postgres://username:password@hostname:port/database_name',
            'terminal_command': '# First login to Heroku (interactive)\nheroku login\n# Then connect\nheroku pg:psql postgresql-shaped-12345 --app your-app-name',
            'notes': 'Requires Heroku API key and app name.',
            'env_variables': [
                'HEROKU_API_KEY=your_api_key',
                'HEROKU_APP_NAME=your_app_name',
                'HEROKU_DATABASE_URL=postgres://username:password@hostname:port/database_name'
            ],
            'auth_popup': True
        },
        'crunchybridge': {
            'fields': ['db_url', 'username', 'password', 'host', 'port', 'database_name'],
            'url_option': True,
            'url_field': 'db_url',
            'url_example': 'postgres://username:password@db.crunchybridge.com:5432/database_name',
            'terminal_command': 'psql "postgres://username:password@db.crunchybridge.com:5432/database_name"',
            'notes': 'Requires a Crunchy Bridge database connection string.',
            'env_variables': [
                'CRUNCHYBRIDGE_DB_URL=postgres://username:password@db.crunchybridge.com:5432/database_name',
                'CRUNCHYBRIDGE_USERNAME=username',
                'CRUNCHYBRIDGE_PASSWORD=your_password',
                'CRUNCHYBRIDGE_HOST=db.crunchybridge.com',
                'CRUNCHYBRIDGE_PORT=5432',
                'CRUNCHYBRIDGE_DATABASE=database_name'
            ]
        },
        'neon': {
            'fields': ['db_url', 'username', 'password', 'host', 'port', 'database_name'],
            'url_option': True,
            'url_field': 'db_url',
            'url_example': 'postgres://username:password@hostname:5432/database_name?sslmode=require',
            'terminal_command': 'psql "postgres://username:password@hostname:5432/database_name?sslmode=require"',
            'notes': 'Requires a Neon.tech database connection string with SSL enabled.',
            'env_variables': [
                'NEON_DB_URL=postgres://username:password@hostname:5432/database_name?sslmode=require',
                'NEON_USERNAME=username',
                'NEON_PASSWORD=your_password',
                'NEON_HOST=hostname',
                'NEON_PORT=5432',
                'NEON_DATABASE=database_name'
            ]
        },
        
        # Time Series Databases
        'influxdb': {
            'fields': ['url', 'token', 'org', 'bucket', 'username', 'password'],
            'url_option': True,
            'url_field': 'url',
            'url_example': 'http://localhost:8086',
            'terminal_command': 'influx -host localhost -port 8086 -username username -password password',
            'notes': 'For InfluxDB 2.x, use token + org + bucket. For InfluxDB 1.x, use username + password.',
            'env_variables': [
                '# For InfluxDB 2.x',
                'INFLUXDB_URL=http://localhost:8086',
                'INFLUXDB_TOKEN=your_api_token',
                'INFLUXDB_ORG=your_organization',
                'INFLUXDB_BUCKET=your_bucket',
                '# For InfluxDB 1.x',
                'INFLUXDB_USERNAME=username',
                'INFLUXDB_PASSWORD=your_password'
            ]
        },
        'timescaledb': {
            'fields': ['host', 'port', 'user', 'password', 'database'],
            'url_option': True,
            'url_field': 'connection_string',
            'url_example': 'postgresql://username:password@localhost:5432/database_name',
            'terminal_command': 'psql -h localhost -p 5432 -U username -d database_name',
            'notes': 'TimescaleDB uses the same connection parameters as PostgreSQL, with added time-series functionality.',
            'env_variables': [
                'TIMESCALEDB_HOST=localhost',
                'TIMESCALEDB_PORT=5432',
                'TIMESCALEDB_USER=username',
                'TIMESCALEDB_PASSWORD=your_password',
                'TIMESCALEDB_DATABASE=database_name',
                'TIMESCALEDB_CONNECTION_STRING=postgresql://username:password@localhost:5432/database_name'
            ]
        },
        'kdb': {
            'fields': ['host', 'port', 'username', 'password', 'script_path'],
            'url_option': False,
            'terminal_command': 'q script_path.q -p 5000',
            'notes': 'Kdb+ is a column-oriented database optimized for time-series data. The script_path is required.',
            'env_variables': [
                'KDB_HOST=localhost',
                'KDB_PORT=5000',
                'KDB_USERNAME=username',
                'KDB_PASSWORD=your_password',
                'KDB_SCRIPT_PATH=/path/to/script.q'
            ]
        },
        
        # Specialized Systems
        'prometheus': {
            'fields': ['hostname', 'port', 'username', 'password'],
            'url_option': True,
            'url_field': 'url',
            'url_example': 'http://localhost:9090',
            'terminal_command': 'curl -G \'http://localhost:9090/api/v1/query\' --data-urlencode \'query=up\'',
            'notes': 'If authentication is enabled, include username and password. URL is in format: http://localhost:9090',
            'env_variables': [
                'PROMETHEUS_URL=http://localhost:9090',
                'PROMETHEUS_USERNAME=username',
                'PROMETHEUS_PASSWORD=your_password'
            ]
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
