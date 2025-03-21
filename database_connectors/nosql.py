import logging
import json
import os

# Import NoSQL libraries with try/except to handle missing dependencies
try:
    import pymongo
except ImportError:
    pymongo = None

try:
    from cassandra.cluster import Cluster
    from cassandra.auth import PlainTextAuthProvider
except ImportError:
    Cluster = None
    PlainTextAuthProvider = None

try:
    import redis
except ImportError:
    redis = None

try:
    from elasticsearch import Elasticsearch
except ImportError:
    Elasticsearch = None

try:
    import boto3
except ImportError:
    boto3 = None

try:
    from couchbase.cluster import Cluster as CouchbaseCluster
    from couchbase.auth import PasswordAuthenticator
except ImportError:
    CouchbaseCluster = None
    PasswordAuthenticator = None

try:
    from neo4j import GraphDatabase
except ImportError:
    GraphDatabase = None

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class BaseNoSQLConnector:
    """Base class for NoSQL database connectors"""
    
    def __init__(self, credentials):
        self.credentials = credentials
        self.client = None
    
    def connect(self):
        """Connect to the database"""
        raise NotImplementedError("Subclasses must implement connect()")
    
    def disconnect(self):
        """Disconnect from the database"""
        if self.client:
            try:
                self.client.close()
            except Exception as e:
                logger.error(f"Error disconnecting: {str(e)}")
            finally:
                self.client = None
    
    def test_connection(self):
        """Test the connection to the database"""
        try:
            self.connect()
            return True, "Connection successful"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
        finally:
            self.disconnect()
    
    def get_schema(self):
        """Get the schema of the database"""
        return {"message": "Schema retrieval is limited or not available for NoSQL databases"}
    
    def execute_query(self, query):
        """
        Execute a query against the database
        
        Args:
            query (str): The query to execute
            
        Returns:
            tuple: (result, success, error_message)
        """
        raise NotImplementedError("Subclasses must implement execute_query()")

class MongoDBConnector(BaseNoSQLConnector):
    """Connector for MongoDB databases"""
    
    def connect(self):
        """Connect to a MongoDB database"""
        if not self.client:
            try:
                # Check if direct connection string is provided
                if self.credentials.get("connection_string"):
                    logger.info("Using provided connection string")
                    connection_string = self.credentials.get("connection_string")
                    self.client = pymongo.MongoClient(connection_string)
                # Check if individual credentials are provided
                elif self.credentials.get("host"):
                    logger.info("Using individual credentials")
                    host = self.credentials.get("host", "localhost")
                    port = self.credentials.get("port", 27017)
                    username = self.credentials.get("username")
                    password = self.credentials.get("password")
                    auth_db = self.credentials.get("auth_db", "admin")
                    
                    connection_string = f"mongodb://"
                    if username and password:
                        connection_string += f"{username}:{password}@"
                    
                    connection_string += f"{host}:{port}/{auth_db}"
                    
                    self.client = pymongo.MongoClient(connection_string)
                # Check for MongoDB URI environment variable
                elif os.environ.get("MONGO_URI"):
                    logger.info("Using MONGO_URI environment variable")
                    connection_string = os.environ.get("MONGO_URI")
                    self.client = pymongo.MongoClient(connection_string)
                # Check for standard MongoDB environment variables
                elif all(os.environ.get(key) for key in ["MONGO_HOST", "MONGO_USER", "MONGO_PASSWORD", "MONGO_DATABASE"]):
                    logger.info("Using MongoDB environment variables")
                    host = os.environ.get("MONGO_HOST")
                    port = os.environ.get("MONGO_PORT", "27017")
                    user = os.environ.get("MONGO_USER")
                    password = os.environ.get("MONGO_PASSWORD")
                    db_name = os.environ.get("MONGO_DATABASE")
                    
                    connection_string = f"mongodb://{user}:{password}@{host}:{port}/{db_name}"
                    self.client = pymongo.MongoClient(connection_string)
                else:
                    logger.error("No valid MongoDB credentials provided")
                    raise Exception("No valid MongoDB credentials provided")
                
                # Force connection to verify it works
                self.client.server_info()
                
            except Exception as e:
                logger.exception("Error connecting to MongoDB")
                raise Exception(f"Error connecting to MongoDB: {str(e)}")
    
    def get_schema(self):
        """Get a list of databases and collections"""
        try:
            self.connect()
            
            schema_info = {
                "databases": []
            }
            
            for db_name in self.client.list_database_names():
                db = self.client[db_name]
                db_info = {
                    "name": db_name,
                    "collections": []
                }
                
                for collection_name in db.list_collection_names():
                    collection = db[collection_name]
                    # Sample one document to infer fields
                    sample_doc = collection.find_one()
                    fields = list(sample_doc.keys()) if sample_doc else []
                    
                    collection_info = {
                        "name": collection_name,
                        "fields": fields
                    }
                    
                    db_info["collections"].append(collection_info)
                
                schema_info["databases"].append(db_info)
            
            return schema_info
            
        except Exception as e:
            logger.exception("Error getting MongoDB schema")
            return {"error": f"Error getting schema: {str(e)}"}
        finally:
            self.disconnect()
    
    def execute_query(self, query):
        """
        Execute a MongoDB query
        
        Args:
            query (str): A string representing a MongoDB query in JSON format
            
        Returns:
            tuple: (result, success, error_message)
        """
        try:
            self.connect()
            
            # Parse the query string as JSON
            query_obj = json.loads(query)
            
            db_name = query_obj.get("database")
            collection_name = query_obj.get("collection")
            operation = query_obj.get("operation")
            
            if not db_name or not collection_name or not operation:
                return None, False, "Query must specify database, collection, and operation"
            
            db = self.client[db_name]
            collection = db[collection_name]
            
            if operation == "find":
                filter_criteria = query_obj.get("filter", {})
                projection = query_obj.get("projection", {})
                limit = query_obj.get("limit", 0)
                
                cursor = collection.find(filter_criteria, projection)
                if limit > 0:
                    cursor = cursor.limit(limit)
                
                results = list(cursor)
                # Convert ObjectId to string for JSON serialization
                for doc in results:
                    if "_id" in doc:
                        doc["_id"] = str(doc["_id"])
                
                return results, True, None
                
            elif operation == "insert":
                documents = query_obj.get("documents", [])
                result = collection.insert_many(documents)
                return {"inserted_ids": [str(id) for id in result.inserted_ids]}, True, None
                
            elif operation == "update":
                filter_criteria = query_obj.get("filter", {})
                update_obj = query_obj.get("update", {})
                
                result = collection.update_many(filter_criteria, update_obj)
                return {"matched_count": result.matched_count, "modified_count": result.modified_count}, True, None
                
            elif operation == "delete":
                filter_criteria = query_obj.get("filter", {})
                
                result = collection.delete_many(filter_criteria)
                return {"deleted_count": result.deleted_count}, True, None
                
            else:
                return None, False, f"Unsupported operation: {operation}"
                
        except json.JSONDecodeError:
            return None, False, "Invalid JSON query format"
        except Exception as e:
            logger.exception(f"Error executing MongoDB query: {query}")
            return None, False, f"Error executing query: {str(e)}"
        finally:
            self.disconnect()

class CassandraConnector(BaseNoSQLConnector):
    """Connector for Cassandra databases"""
    
    def connect(self):
        """Connect to a Cassandra database"""
        if not self.client:
            try:
                # Get credentials from credentials dict or environment variables
                host = self.credentials.get("host") or os.environ.get("CASSANDRA_HOST", "localhost")
                port = self.credentials.get("port") or os.environ.get("CASSANDRA_PORT", "9042")
                username = self.credentials.get("username") or os.environ.get("CASSANDRA_USERNAME")
                password = self.credentials.get("password") or os.environ.get("CASSANDRA_PASSWORD")
                keyspace = self.credentials.get("keyspace") or os.environ.get("CASSANDRA_KEYSPACE")
                
                # Log if using environment variables
                if os.environ.get("CASSANDRA_HOST") and not self.credentials.get("host"):
                    logger.info("Using CASSANDRA_HOST environment variable")
                if os.environ.get("CASSANDRA_PORT") and not self.credentials.get("port"):
                    logger.info("Using CASSANDRA_PORT environment variable")
                if os.environ.get("CASSANDRA_USERNAME") and not self.credentials.get("username"):
                    logger.info("Using CASSANDRA_USERNAME environment variable")
                if os.environ.get("CASSANDRA_PASSWORD") and not self.credentials.get("password"):
                    logger.info("Using CASSANDRA_PASSWORD environment variable")
                if os.environ.get("CASSANDRA_KEYSPACE") and not self.credentials.get("keyspace"):
                    logger.info("Using CASSANDRA_KEYSPACE environment variable")
                
                # Convert port to integer if it's a string
                if isinstance(port, str):
                    port = int(port)
                
                auth_provider = None
                if username and password:
                    auth_provider = PlainTextAuthProvider(username=username, password=password)
                
                self.client = Cluster([host], port=port, auth_provider=auth_provider)
                
                # Connect with keyspace if provided, otherwise connect without keyspace
                if keyspace:
                    self.session = self.client.connect(keyspace)
                else:
                    self.session = self.client.connect()
                
            except Exception as e:
                logger.exception("Error connecting to Cassandra")
                raise Exception(f"Error connecting to Cassandra: {str(e)}")
    
    def disconnect(self):
        """Disconnect from the Cassandra database"""
        if self.client:
            try:
                self.client.shutdown()
            except Exception as e:
                logger.error(f"Error disconnecting from Cassandra: {str(e)}")
            finally:
                self.client = None
    
    def get_schema(self):
        """Get the keyspaces and tables in the Cassandra database"""
        try:
            self.connect()
            
            schema_info = {
                "keyspaces": []
            }
            
            # Query system tables to get keyspace information
            keyspace_query = "SELECT keyspace_name FROM system_schema.keyspaces"
            keyspace_rows = self.session.execute(keyspace_query)
            
            for keyspace_row in keyspace_rows:
                keyspace_name = keyspace_row.keyspace_name
                
                # Skip system keyspaces
                if keyspace_name.startswith("system"):
                    continue
                
                keyspace_info = {
                    "name": keyspace_name,
                    "tables": []
                }
                
                # Query tables for this keyspace
                table_query = f"SELECT table_name FROM system_schema.tables WHERE keyspace_name = '{keyspace_name}'"
                table_rows = self.session.execute(table_query)
                
                for table_row in table_rows:
                    table_name = table_row.table_name
                    
                    table_info = {
                        "name": table_name,
                        "columns": []
                    }
                    
                    # Query columns for this table
                    column_query = f"SELECT column_name, type FROM system_schema.columns WHERE keyspace_name = '{keyspace_name}' AND table_name = '{table_name}'"
                    column_rows = self.session.execute(column_query)
                    
                    for column_row in column_rows:
                        column_info = {
                            "name": column_row.column_name,
                            "type": column_row.type
                        }
                        
                        table_info["columns"].append(column_info)
                    
                    keyspace_info["tables"].append(table_info)
                
                schema_info["keyspaces"].append(keyspace_info)
            
            return schema_info
            
        except Exception as e:
            logger.exception("Error getting Cassandra schema")
            return {"error": f"Error getting schema: {str(e)}"}
        finally:
            self.disconnect()
    
    def execute_query(self, query):
        """
        Execute a CQL query
        
        Args:
            query (str): A CQL query string
            
        Returns:
            tuple: (result, success, error_message)
        """
        try:
            self.connect()
            
            # Execute the query
            result = self.session.execute(query)
            
            # Convert rows to dictionaries
            rows = []
            for row in result:
                row_dict = {}
                for column in row._fields:
                    row_dict[column] = getattr(row, column)
                rows.append(row_dict)
            
            return rows, True, None
            
        except Exception as e:
            logger.exception(f"Error executing CQL query: {query}")
            return None, False, f"Error executing query: {str(e)}"
        finally:
            self.disconnect()

class RedisConnector(BaseNoSQLConnector):
    """Connector for Redis databases"""
    
    def connect(self):
        """Connect to a Redis database"""
        if not self.client:
            try:
                # Get credentials from credentials dict or environment variables
                host = self.credentials.get("host") or os.environ.get("REDIS_HOST", "localhost")
                port = self.credentials.get("port") or os.environ.get("REDIS_PORT", "6379")
                password = self.credentials.get("password") or os.environ.get("REDIS_PASSWORD")
                db = self.credentials.get("db") or os.environ.get("REDIS_DB", "0")
                
                # Log if using environment variables
                if os.environ.get("REDIS_HOST") and not self.credentials.get("host"):
                    logger.info("Using REDIS_HOST environment variable")
                if os.environ.get("REDIS_PORT") and not self.credentials.get("port"):
                    logger.info("Using REDIS_PORT environment variable")
                if os.environ.get("REDIS_PASSWORD") and not self.credentials.get("password"):
                    logger.info("Using REDIS_PASSWORD environment variable")
                if os.environ.get("REDIS_DB") and not self.credentials.get("db"):
                    logger.info("Using REDIS_DB environment variable")
                
                # Convert port and db to integers if they're strings
                if isinstance(port, str):
                    port = int(port)
                if isinstance(db, str):
                    db = int(db)
                
                self.client = redis.Redis(
                    host=host,
                    port=port,
                    password=password,
                    db=db,
                    decode_responses=True
                )
                
                # Test connection
                self.client.ping()
                
            except Exception as e:
                logger.exception("Error connecting to Redis")
                raise Exception(f"Error connecting to Redis: {str(e)}")
    
    def execute_query(self, query):
        """
        Execute a Redis command
        
        Args:
            query (str): A JSON string representing a Redis command
            
        Returns:
            tuple: (result, success, error_message)
        """
        try:
            self.connect()
            
            # Parse the query string as JSON
            query_obj = json.loads(query)
            
            command = query_obj.get("command")
            args = query_obj.get("args", [])
            
            if not command:
                return None, False, "Query must specify a command"
            
            # Execute the command
            result = self.client.execute_command(command, *args)
            
            # Convert bytes to string if needed
            if isinstance(result, bytes):
                result = result.decode('utf-8')
            
            return {"result": result}, True, None
            
        except json.JSONDecodeError:
            return None, False, "Invalid JSON query format"
        except Exception as e:
            logger.exception(f"Error executing Redis command: {query}")
            return None, False, f"Error executing command: {str(e)}"
        finally:
            self.disconnect()

class ElasticsearchConnector(BaseNoSQLConnector):
    """Connector for Elasticsearch databases"""
    
    def connect(self):
        """Connect to an Elasticsearch database"""
        if not self.client:
            try:
                # Get credentials from credentials dict or environment variables
                host = self.credentials.get("host") or os.environ.get("ELASTICSEARCH_HOST", "localhost")
                port = self.credentials.get("port") or os.environ.get("ELASTICSEARCH_PORT", "9200")
                username = self.credentials.get("username") or os.environ.get("ELASTICSEARCH_USERNAME")
                password = self.credentials.get("password") or os.environ.get("ELASTICSEARCH_PASSWORD")
                cloud_id = self.credentials.get("cloud_id") or os.environ.get("ELASTICSEARCH_CLOUD_ID")
                api_key = self.credentials.get("api_key") or os.environ.get("ELASTICSEARCH_API_KEY")
                
                # Log if using environment variables
                if os.environ.get("ELASTICSEARCH_HOST") and not self.credentials.get("host"):
                    logger.info("Using ELASTICSEARCH_HOST environment variable")
                if os.environ.get("ELASTICSEARCH_PORT") and not self.credentials.get("port"):
                    logger.info("Using ELASTICSEARCH_PORT environment variable")
                if os.environ.get("ELASTICSEARCH_USERNAME") and not self.credentials.get("username"):
                    logger.info("Using ELASTICSEARCH_USERNAME environment variable")
                if os.environ.get("ELASTICSEARCH_PASSWORD") and not self.credentials.get("password"):
                    logger.info("Using ELASTICSEARCH_PASSWORD environment variable")
                if os.environ.get("ELASTICSEARCH_CLOUD_ID") and not self.credentials.get("cloud_id"):
                    logger.info("Using ELASTICSEARCH_CLOUD_ID environment variable")
                if os.environ.get("ELASTICSEARCH_API_KEY") and not self.credentials.get("api_key"):
                    logger.info("Using ELASTICSEARCH_API_KEY environment variable")
                
                # Convert port to integer if it's a string
                if isinstance(port, str):
                    port = int(port)
                
                # Use cloud_id if provided
                if cloud_id:
                    if api_key:
                        self.client = Elasticsearch(
                            cloud_id=cloud_id,
                            api_key=api_key
                        )
                    elif username and password:
                        self.client = Elasticsearch(
                            cloud_id=cloud_id,
                            basic_auth=(username, password)
                        )
                    else:
                        self.client = Elasticsearch(
                            cloud_id=cloud_id
                        )
                else:
                    # Use regular host/port configuration
                    hosts = [f"http://{host}:{port}"]
                    http_auth = None
                    
                    if username and password:
                        http_auth = (username, password)
                    
                    self.client = Elasticsearch(
                        hosts=hosts,
                        http_auth=http_auth
                    )
                
                # Test connection
                self.client.info()
                
            except Exception as e:
                logger.exception("Error connecting to Elasticsearch")
                raise Exception(f"Error connecting to Elasticsearch: {str(e)}")
    
    def get_schema(self):
        """Get the indices and mappings in the Elasticsearch database"""
        try:
            self.connect()
            
            schema_info = {
                "indices": []
            }
            
            # Get all indices
            indices = self.client.indices.get("*")
            
            for index_name, index_data in indices.items():
                index_info = {
                    "name": index_name,
                    "mappings": index_data.get("mappings", {})
                }
                
                schema_info["indices"].append(index_info)
            
            return schema_info
            
        except Exception as e:
            logger.exception("Error getting Elasticsearch schema")
            return {"error": f"Error getting schema: {str(e)}"}
        finally:
            self.disconnect()
    
    def execute_query(self, query):
        """
        Execute an Elasticsearch query
        
        Args:
            query (str): A JSON string representing an Elasticsearch query
            
        Returns:
            tuple: (result, success, error_message)
        """
        try:
            self.connect()
            
            # Parse the query string as JSON
            query_obj = json.loads(query)
            
            operation = query_obj.get("operation")
            index = query_obj.get("index")
            
            if not operation or not index:
                return None, False, "Query must specify operation and index"
            
            if operation == "search":
                body = query_obj.get("body", {})
                size = query_obj.get("size", 10)
                
                result = self.client.search(index=index, body=body, size=size)
                return result, True, None
                
            elif operation == "count":
                body = query_obj.get("body", {})
                
                result = self.client.count(index=index, body=body)
                return result, True, None
                
            elif operation == "index":
                document = query_obj.get("document", {})
                doc_id = query_obj.get("id")
                
                if doc_id:
                    result = self.client.index(index=index, id=doc_id, body=document)
                else:
                    result = self.client.index(index=index, body=document)
                
                return result, True, None
                
            elif operation == "update":
                doc_id = query_obj.get("id")
                document = query_obj.get("document", {})
                
                if not doc_id:
                    return None, False, "Update operation requires document ID"
                
                result = self.client.update(index=index, id=doc_id, body={"doc": document})
                return result, True, None
                
            elif operation == "delete":
                doc_id = query_obj.get("id")
                
                if not doc_id:
                    return None, False, "Delete operation requires document ID"
                
                result = self.client.delete(index=index, id=doc_id)
                return result, True, None
                
            else:
                return None, False, f"Unsupported operation: {operation}"
                
        except json.JSONDecodeError:
            return None, False, "Invalid JSON query format"
        except Exception as e:
            logger.exception(f"Error executing Elasticsearch query: {query}")
            return None, False, f"Error executing query: {str(e)}"
        finally:
            self.disconnect()

class DynamoDBConnector(BaseNoSQLConnector):
    """Connector for Amazon DynamoDB databases"""
    
    def connect(self):
        """Connect to an Amazon DynamoDB database"""
        if not self.client:
            try:
                # Get credentials from credentials dict or environment variables
                access_key = self.credentials.get("access_key") or os.environ.get("AWS_ACCESS_KEY_ID")
                secret_key = self.credentials.get("secret_key") or os.environ.get("AWS_SECRET_ACCESS_KEY")
                region = self.credentials.get("region") or os.environ.get("AWS_REGION", "us-east-1")
                endpoint_url = self.credentials.get("endpoint_url") or os.environ.get("AWS_DYNAMODB_ENDPOINT")
                
                # Log if using environment variables
                if os.environ.get("AWS_ACCESS_KEY_ID") and not self.credentials.get("access_key"):
                    logger.info("Using AWS_ACCESS_KEY_ID environment variable")
                if os.environ.get("AWS_SECRET_ACCESS_KEY") and not self.credentials.get("secret_key"):
                    logger.info("Using AWS_SECRET_ACCESS_KEY environment variable")
                if os.environ.get("AWS_REGION") and not self.credentials.get("region"):
                    logger.info("Using AWS_REGION environment variable")
                if os.environ.get("AWS_DYNAMODB_ENDPOINT") and not self.credentials.get("endpoint_url"):
                    logger.info("Using AWS_DYNAMODB_ENDPOINT environment variable")
                
                # Check for required credentials
                if not access_key or not secret_key:
                    raise ValueError("Access key and secret key are required for DynamoDB connection")
                
                # Create client with endpoint URL if specified
                if endpoint_url:
                    self.client = boto3.resource(
                        'dynamodb',
                        aws_access_key_id=access_key,
                        aws_secret_access_key=secret_key,
                        region_name=region,
                        endpoint_url=endpoint_url
                    )
                else:
                    self.client = boto3.resource(
                        'dynamodb',
                        aws_access_key_id=access_key,
                        aws_secret_access_key=secret_key,
                        region_name=region
                    )
                
                # Test connection by listing tables
                self.client.tables.all()
                
            except Exception as e:
                logger.exception("Error connecting to DynamoDB")
                raise Exception(f"Error connecting to DynamoDB: {str(e)}")
    
    def get_schema(self):
        """Get the tables and their schemas in the DynamoDB database"""
        try:
            self.connect()
            
            schema_info = {
                "tables": []
            }
            
            # Get all tables
            for table in self.client.tables.all():
                table_info = {
                    "name": table.name,
                    "key_schema": table.key_schema,
                    "attribute_definitions": table.attribute_definitions
                }
                
                schema_info["tables"].append(table_info)
            
            return schema_info
            
        except Exception as e:
            logger.exception("Error getting DynamoDB schema")
            return {"error": f"Error getting schema: {str(e)}"}
        finally:
            self.disconnect()
    
    def execute_query(self, query):
        """
        Execute a DynamoDB query
        
        Args:
            query (str): A JSON string representing a DynamoDB operation
            
        Returns:
            tuple: (result, success, error_message)
        """
        try:
            self.connect()
            
            # Parse the query string as JSON
            query_obj = json.loads(query)
            
            operation = query_obj.get("operation")
            table_name = query_obj.get("table")
            
            if not operation or not table_name:
                return None, False, "Query must specify operation and table"
            
            table = self.client.Table(table_name)
            
            if operation == "scan":
                filter_expression = query_obj.get("filter_expression")
                attrs_to_get = query_obj.get("attributes_to_get")
                
                kwargs = {}
                if filter_expression:
                    kwargs["FilterExpression"] = filter_expression
                if attrs_to_get:
                    kwargs["ProjectionExpression"] = ", ".join(attrs_to_get)
                
                result = table.scan(**kwargs)
                return result["Items"], True, None
                
            elif operation == "query":
                key_condition = query_obj.get("key_condition")
                
                if not key_condition:
                    return None, False, "Query operation requires key condition"
                
                result = table.query(KeyConditionExpression=key_condition)
                return result["Items"], True, None
                
            elif operation == "get_item":
                key = query_obj.get("key")
                
                if not key:
                    return None, False, "Get item operation requires key"
                
                result = table.get_item(Key=key)
                return result.get("Item"), True, None
                
            elif operation == "put_item":
                item = query_obj.get("item")
                
                if not item:
                    return None, False, "Put item operation requires item"
                
                result = table.put_item(Item=item)
                return {"status": "success"}, True, None
                
            elif operation == "update_item":
                key = query_obj.get("key")
                update_expression = query_obj.get("update_expression")
                
                if not key or not update_expression:
                    return None, False, "Update item operation requires key and update expression"
                
                result = table.update_item(
                    Key=key,
                    UpdateExpression=update_expression
                )
                return {"status": "success"}, True, None
                
            elif operation == "delete_item":
                key = query_obj.get("key")
                
                if not key:
                    return None, False, "Delete item operation requires key"
                
                result = table.delete_item(Key=key)
                return {"status": "success"}, True, None
                
            else:
                return None, False, f"Unsupported operation: {operation}"
                
        except json.JSONDecodeError:
            return None, False, "Invalid JSON query format"
        except Exception as e:
            logger.exception(f"Error executing DynamoDB operation: {query}")
            return None, False, f"Error executing operation: {str(e)}"
        finally:
            self.disconnect()

class CouchbaseConnector(BaseNoSQLConnector):
    """Connector for Couchbase databases"""
    
    def connect(self):
        """Connect to a Couchbase database"""
        if not self.client:
            try:
                host = self.credentials.get("host", "localhost")
                username = self.credentials.get("username")
                password = self.credentials.get("password")
                bucket = self.credentials.get("bucket")
                
                # Connect to the cluster
                authenticator = PasswordAuthenticator(username, password)
                cluster = CouchbaseCluster(f"couchbase://{host}")
                cluster.authenticate(authenticator)
                
                # Open the bucket
                self.bucket = cluster.open_bucket(bucket)
                self.client = cluster
                
            except Exception as e:
                logger.exception("Error connecting to Couchbase")
                raise Exception(f"Error connecting to Couchbase: {str(e)}")
    
    def execute_query(self, query):
        """
        Execute a Couchbase N1QL query
        
        Args:
            query (str): A N1QL query string
            
        Returns:
            tuple: (result, success, error_message)
        """
        try:
            self.connect()
            
            # Execute N1QL query
            from couchbase.n1ql import N1QLQuery
            n1ql_query = N1QLQuery(query)
            result = self.bucket.n1ql_query(n1ql_query)
            
            # Convert rows to dictionaries
            rows = []
            for row in result:
                rows.append(row)
            
            return rows, True, None
            
        except Exception as e:
            logger.exception(f"Error executing Couchbase query: {query}")
            return None, False, f"Error executing query: {str(e)}"
        finally:
            self.disconnect()

class Neo4jConnector(BaseNoSQLConnector):
    """Connector for Neo4j databases"""
    
    def connect(self):
        """Connect to a Neo4j database"""
        if not self.client:
            try:
                # Get credentials from credentials dict or environment variables
                uri = self.credentials.get("uri") or os.environ.get("NEO4J_URI", "bolt://localhost:7687")
                username = self.credentials.get("username") or os.environ.get("NEO4J_USERNAME")
                password = self.credentials.get("password") or os.environ.get("NEO4J_PASSWORD")
                database = self.credentials.get("database") or os.environ.get("NEO4J_DATABASE")
                
                # Log if using environment variables
                if os.environ.get("NEO4J_URI") and not self.credentials.get("uri"):
                    logger.info("Using NEO4J_URI environment variable")
                if os.environ.get("NEO4J_USERNAME") and not self.credentials.get("username"):
                    logger.info("Using NEO4J_USERNAME environment variable")
                if os.environ.get("NEO4J_PASSWORD") and not self.credentials.get("password"):
                    logger.info("Using NEO4J_PASSWORD environment variable")
                if os.environ.get("NEO4J_DATABASE") and not self.credentials.get("database"):
                    logger.info("Using NEO4J_DATABASE environment variable")
                
                # Connect with auth if credentials are provided
                if username and password:
                    self.client = GraphDatabase.driver(uri, auth=(username, password))
                else:
                    self.client = GraphDatabase.driver(uri)
                
                # Set default database if provided
                self.database = database
                
            except Exception as e:
                logger.exception("Error connecting to Neo4j")
                raise Exception(f"Error connecting to Neo4j: {str(e)}")
    
    def get_schema(self):
        """Get the nodes and relationships in the Neo4j database"""
        try:
            self.connect()
            
            # Use the specified database if available
            session_params = {}
            if hasattr(self, 'database') and self.database:
                session_params['database'] = self.database
            
            with self.client.session(**session_params) as session:
                # Get node labels
                labels_result = session.run("CALL db.labels()")
                labels = [record["label"] for record in labels_result]
                
                # Get relationship types
                rel_types_result = session.run("CALL db.relationshipTypes()")
                rel_types = [record["relationshipType"] for record in rel_types_result]
                
                schema_info = {
                    "node_labels": labels,
                    "relationship_types": rel_types
                }
                
                return schema_info
            
        except Exception as e:
            logger.exception("Error getting Neo4j schema")
            return {"error": f"Error getting schema: {str(e)}"}
        finally:
            self.disconnect()
    
    def execute_query(self, query):
        """
        Execute a Cypher query
        
        Args:
            query (str): A Cypher query string
            
        Returns:
            tuple: (result, success, error_message)
        """
        try:
            self.connect()
            
            # Use the specified database if available
            session_params = {}
            if hasattr(self, 'database') and self.database:
                session_params['database'] = self.database
            
            with self.client.session(**session_params) as session:
                result = session.run(query)
                
                # Convert records to dictionaries
                records = []
                for record in result:
                    record_dict = {}
                    for key, value in record.items():
                        # Neo4j has special node and relationship objects
                        # Convert them to dictionaries
                        record_dict[key] = self._neo4j_to_dict(value)
                    records.append(record_dict)
                
                return records, True, None
            
        except Exception as e:
            logger.exception(f"Error executing Cypher query: {query}")
            return None, False, f"Error executing query: {str(e)}"
        finally:
            self.disconnect()
    
    def _neo4j_to_dict(self, value):
        """Convert Neo4j objects to dictionaries"""
        if hasattr(value, "labels") and callable(getattr(value, "labels")):
            # It's a node
            node_dict = dict(value)
            node_dict["_labels"] = list(value.labels)
            return node_dict
        elif hasattr(value, "type") and callable(getattr(value, "type")):
            # It's a relationship
            rel_dict = dict(value)
            rel_dict["_type"] = value.type
            rel_dict["_start"] = self._neo4j_to_dict(value.start_node)
            rel_dict["_end"] = self._neo4j_to_dict(value.end_node)
            return rel_dict
        elif isinstance(value, (list, tuple)):
            return [self._neo4j_to_dict(item) for item in value]
        elif isinstance(value, dict):
            return {k: self._neo4j_to_dict(v) for k, v in value.items()}
        else:
            return value
