import logging
import json
import os

# Import cloud database libraries with try/except to handle missing dependencies
try:
    from azure.cosmos import CosmosClient
except ImportError:
    CosmosClient = None

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
except ImportError:
    firebase_admin = None
    credentials = None
    firestore = None

try:
    from supabase import create_client, Client
except ImportError:
    create_client = None
    Client = None

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class BaseCloudConnector:
    """Base class for cloud database connectors"""
    
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
        return {"message": "Schema retrieval is limited or not available for cloud databases"}
    
    def execute_query(self, query):
        """
        Execute a query against the database
        
        Args:
            query (str): The query to execute
            
        Returns:
            tuple: (result, success, error_message)
        """
        raise NotImplementedError("Subclasses must implement execute_query()")

class CosmosDBConnector(BaseCloudConnector):
    """Connector for Azure Cosmos DB databases"""
    
    def connect(self):
        """Connect to an Azure Cosmos DB database"""
        if not self.client:
            try:
                # Get credentials from provided credentials or environment variables
                account_uri = self.credentials.get("account_uri") or os.environ.get("COSMOS_ACCOUNT_URI")
                primary_key = self.credentials.get("primary_key") or os.environ.get("COSMOS_PRIMARY_KEY")
                
                # Log if using environment variables
                if os.environ.get("COSMOS_ACCOUNT_URI") and not self.credentials.get("account_uri"):
                    logger.info("Using COSMOS_ACCOUNT_URI environment variable")
                    
                if os.environ.get("COSMOS_PRIMARY_KEY") and not self.credentials.get("primary_key"):
                    logger.info("Using COSMOS_PRIMARY_KEY environment variable")
                
                if not account_uri or not primary_key:
                    raise ValueError("Cosmos DB account URI and primary key are required (either in credentials or as COSMOS_ACCOUNT_URI and COSMOS_PRIMARY_KEY environment variables)")
                
                self.client = CosmosClient(account_uri, credential=primary_key)
                
            except Exception as e:
                logger.exception("Error connecting to Azure Cosmos DB")
                raise Exception(f"Error connecting to Azure Cosmos DB: {str(e)}")
    
    def execute_query(self, query):
        """
        Execute a query against Azure Cosmos DB
        
        Args:
            query (str): A JSON string representing a Cosmos DB operation
            
        Returns:
            tuple: (result, success, error_message)
        """
        try:
            self.connect()
            
            # Parse the query string as JSON
            query_obj = json.loads(query)
            
            operation = query_obj.get("operation")
            database_id = query_obj.get("database")
            container_id = query_obj.get("container")
            
            if not operation or not database_id or not container_id:
                return None, False, "Query must specify operation, database, and container"
            
            database = self.client.get_database_client(database_id)
            container = database.get_container_client(container_id)
            
            if operation == "query":
                query_text = query_obj.get("query_text")
                
                if not query_text:
                    return None, False, "Query operation requires query_text"
                
                items = list(container.query_items(query=query_text, enable_cross_partition_query=True))
                return items, True, None
                
            elif operation == "get":
                item_id = query_obj.get("id")
                partition_key = query_obj.get("partition_key")
                
                if not item_id:
                    return None, False, "Get operation requires id"
                
                item = container.read_item(item=item_id, partition_key=partition_key)
                return item, True, None
                
            elif operation == "create":
                body = query_obj.get("body")
                
                if not body:
                    return None, False, "Create operation requires body"
                
                created_item = container.create_item(body=body)
                return created_item, True, None
                
            elif operation == "replace":
                item_id = query_obj.get("id")
                body = query_obj.get("body")
                partition_key = query_obj.get("partition_key")
                
                if not item_id or not body:
                    return None, False, "Replace operation requires id and body"
                
                replaced_item = container.replace_item(item=item_id, body=body, partition_key=partition_key)
                return replaced_item, True, None
                
            elif operation == "delete":
                item_id = query_obj.get("id")
                partition_key = query_obj.get("partition_key")
                
                if not item_id:
                    return None, False, "Delete operation requires id"
                
                container.delete_item(item=item_id, partition_key=partition_key)
                return {"status": "success"}, True, None
                
            else:
                return None, False, f"Unsupported operation: {operation}"
                
        except json.JSONDecodeError:
            return None, False, "Invalid JSON query format"
        except Exception as e:
            logger.exception(f"Error executing Cosmos DB operation: {query}")
            return None, False, f"Error executing operation: {str(e)}"
        finally:
            self.disconnect()

class FirestoreConnector(BaseCloudConnector):
    """Connector for Google Firestore databases"""
    
    def connect(self):
        """Connect to a Google Firestore database"""
        if not self.client:
            try:
                # Get credentials from provided credentials or environment variables
                project_id = self.credentials.get("project_id") or os.environ.get("FIREBASE_PROJECT_ID")
                service_account_key = self.credentials.get("service_account_key") or os.environ.get("FIREBASE_SERVICE_ACCOUNT_KEY")
                
                # Log if using environment variables
                if os.environ.get("FIREBASE_PROJECT_ID") and not self.credentials.get("project_id"):
                    logger.info("Using FIREBASE_PROJECT_ID environment variable")
                    
                if os.environ.get("FIREBASE_SERVICE_ACCOUNT_KEY") and not self.credentials.get("service_account_key"):
                    logger.info("Using FIREBASE_SERVICE_ACCOUNT_KEY environment variable")
                
                # Try different connection methods
                if not firebase_admin:
                    raise ImportError("firebase_admin package is not installed")
                
                if not firebase_admin._apps:
                    # Check if service account key is provided
                    if service_account_key:
                        # If provided as a string, convert to dict
                        if isinstance(service_account_key, str):
                            try:
                                service_account_info = json.loads(service_account_key)
                            except json.JSONDecodeError:
                                raise ValueError("Invalid service account key format: not valid JSON")
                        else:
                            service_account_info = service_account_key
                            
                        cred = credentials.Certificate(service_account_info)
                        firebase_admin.initialize_app(cred, {
                            'projectId': project_id
                        })
                    elif project_id:
                        # Try to initialize with just project ID
                        firebase_admin.initialize_app(options={
                            'projectId': project_id
                        })
                    else:
                        # Try to initialize with default credentials
                        firebase_admin.initialize_app()
                
                self.client = firestore.client()
                
            except Exception as e:
                logger.exception("Error connecting to Firestore")
                raise Exception(f"Error connecting to Firestore: {str(e)}")
    
    def execute_query(self, query):
        """
        Execute a query against Firestore
        
        Args:
            query (str): A JSON string representing a Firestore operation
            
        Returns:
            tuple: (result, success, error_message)
        """
        try:
            self.connect()
            
            # Parse the query string as JSON
            query_obj = json.loads(query)
            
            operation = query_obj.get("operation")
            collection = query_obj.get("collection")
            
            if not operation or not collection:
                return None, False, "Query must specify operation and collection"
            
            collection_ref = self.client.collection(collection)
            
            if operation == "get_all":
                docs = collection_ref.stream()
                result = []
                
                for doc in docs:
                    doc_dict = doc.to_dict()
                    doc_dict["_id"] = doc.id
                    result.append(doc_dict)
                
                return result, True, None
                
            elif operation == "get":
                doc_id = query_obj.get("id")
                
                if not doc_id:
                    return None, False, "Get operation requires document id"
                
                doc = collection_ref.document(doc_id).get()
                
                if not doc.exists:
                    return None, False, f"Document with id {doc_id} does not exist"
                
                result = doc.to_dict()
                result["_id"] = doc.id
                
                return result, True, None
                
            elif operation == "query":
                where_clauses = query_obj.get("where", [])
                order_by = query_obj.get("order_by")
                limit = query_obj.get("limit")
                
                query_ref = collection_ref
                
                for where_clause in where_clauses:
                    field = where_clause.get("field")
                    op = where_clause.get("operator")
                    value = where_clause.get("value")
                    
                    if not field or not op or value is None:
                        return None, False, "Where clause requires field, operator, and value"
                    
                    query_ref = query_ref.where(field, op, value)
                
                if order_by:
                    direction = order_by.get("direction", "ASCENDING")
                    field = order_by.get("field")
                    
                    if not field:
                        return None, False, "Order by requires field"
                    
                    if direction == "DESCENDING":
                        query_ref = query_ref.order_by(field, direction=firestore.Query.DESCENDING)
                    else:
                        query_ref = query_ref.order_by(field)
                
                if limit:
                    query_ref = query_ref.limit(limit)
                
                docs = query_ref.stream()
                result = []
                
                for doc in docs:
                    doc_dict = doc.to_dict()
                    doc_dict["_id"] = doc.id
                    result.append(doc_dict)
                
                return result, True, None
                
            elif operation == "add":
                data = query_obj.get("data")
                
                if not data:
                    return None, False, "Add operation requires data"
                
                doc_ref = collection_ref.add(data)
                
                return {"id": doc_ref[1].id}, True, None
                
            elif operation == "set":
                doc_id = query_obj.get("id")
                data = query_obj.get("data")
                merge = query_obj.get("merge", False)
                
                if not doc_id or not data:
                    return None, False, "Set operation requires document id and data"
                
                doc_ref = collection_ref.document(doc_id)
                doc_ref.set(data, merge=merge)
                
                return {"status": "success"}, True, None
                
            elif operation == "update":
                doc_id = query_obj.get("id")
                data = query_obj.get("data")
                
                if not doc_id or not data:
                    return None, False, "Update operation requires document id and data"
                
                doc_ref = collection_ref.document(doc_id)
                doc_ref.update(data)
                
                return {"status": "success"}, True, None
                
            elif operation == "delete":
                doc_id = query_obj.get("id")
                
                if not doc_id:
                    return None, False, "Delete operation requires document id"
                
                doc_ref = collection_ref.document(doc_id)
                doc_ref.delete()
                
                return {"status": "success"}, True, None
                
            else:
                return None, False, f"Unsupported operation: {operation}"
                
        except json.JSONDecodeError:
            return None, False, "Invalid JSON query format"
        except Exception as e:
            logger.exception(f"Error executing Firestore operation: {query}")
            return None, False, f"Error executing operation: {str(e)}"
        finally:
            self.disconnect()


class SupabaseConnector(BaseCloudConnector):
    """Connector for Supabase"""
    
    def connect(self):
        """Connect to a Supabase project"""
        if not self.client:
            try:
                # Check for direct credentials first
                supabase_url = self.credentials.get("supabase_url")
                supabase_key = self.credentials.get("supabase_key")
                
                # Check for environment variables if credentials not provided
                if not supabase_url:
                    supabase_url = os.environ.get("SUPABASE_URL")
                    logger.info("Using SUPABASE_URL environment variable")
                
                if not supabase_key:
                    supabase_key = os.environ.get("SUPABASE_KEY") 
                    logger.info("Using SUPABASE_KEY environment variable")
                
                # Validate credentials
                if not supabase_url or not supabase_key:
                    raise ValueError("Supabase URL and API key are required (either in credentials or as environment variables SUPABASE_URL and SUPABASE_KEY)")
                
                # Check if supabase package is installed
                if not create_client:
                    raise ImportError("supabase package is not installed")
                
                # Connect to Supabase
                self.client = create_client(supabase_url, supabase_key)
                
            except Exception as e:
                logger.exception("Error connecting to Supabase")
                raise Exception(f"Error connecting to Supabase: {str(e)}")
    
    def get_schema(self):
        """Get the schema of the Supabase project"""
        try:
            self.connect()
            
            # Get a list of tables from Postgres system tables
            # Note: This requires the right permissions for the API key
            result = self.client.rpc('get_schema_info').execute()
            
            if hasattr(result, 'data') and result.data:
                return result.data
            
            return {"message": "Schema retrieval limited with current API key permissions"}
            
        except Exception as e:
            logger.exception("Error getting Supabase schema")
            return {"error": str(e)}
        finally:
            self.disconnect()
    
    def execute_query(self, query):
        """
        Execute a query against Supabase
        
        Args:
            query (str): A JSON string representing a Supabase operation
            
        Returns:
            tuple: (result, success, error_message)
        """
        try:
            self.connect()
            
            # Parse the query string as JSON
            query_obj = json.loads(query)
            
            operation = query_obj.get("operation")
            table = query_obj.get("table")
            
            if not operation:
                return None, False, "Query must specify operation"
                
            if operation in ["select", "insert", "update", "delete"] and not table:
                return None, False, f"Operation '{operation}' requires table name"
            
            # Execute appropriate operation
            if operation == "select":
                # Get filters
                select_columns = query_obj.get("select", "*")
                filters = query_obj.get("filters", {})
                order = query_obj.get("order")
                limit = query_obj.get("limit")
                offset = query_obj.get("offset")
                
                # Build query
                query_builder = self.client.from_(table).select(select_columns)
                
                # Apply filters
                for column, criteria in filters.items():
                    if isinstance(criteria, dict):
                        for operator, value in criteria.items():
                            query_builder = query_builder.filter(column, operator, value)
                    else:
                        query_builder = query_builder.eq(column, criteria)
                
                # Apply ordering
                if order:
                    if isinstance(order, dict):
                        column = order.get("column")
                        ascending = order.get("ascending", True)
                        if column:
                            query_builder = query_builder.order(column, desc=not ascending)
                    elif isinstance(order, str):
                        query_builder = query_builder.order(order)
                
                # Apply pagination
                if limit:
                    query_builder = query_builder.limit(limit)
                if offset:
                    query_builder = query_builder.offset(offset)
                
                # Execute
                result = query_builder.execute()
                return result.data, True, None
                
            elif operation == "insert":
                data = query_obj.get("data")
                
                if not data:
                    return None, False, "Insert operation requires data"
                
                result = self.client.from_(table).insert(data).execute()
                return result.data, True, None
                
            elif operation == "update":
                data = query_obj.get("data")
                filters = query_obj.get("filters", {})
                
                if not data:
                    return None, False, "Update operation requires data"
                
                query_builder = self.client.from_(table).update(data)
                
                # Apply filters
                for column, criteria in filters.items():
                    if isinstance(criteria, dict):
                        for operator, value in criteria.items():
                            query_builder = query_builder.filter(column, operator, value)
                    else:
                        query_builder = query_builder.eq(column, criteria)
                
                result = query_builder.execute()
                return result.data, True, None
                
            elif operation == "delete":
                filters = query_obj.get("filters", {})
                
                if not filters:
                    return None, False, "Delete operation requires filters to avoid accidental deletion of all records"
                
                query_builder = self.client.from_(table).delete()
                
                # Apply filters
                for column, criteria in filters.items():
                    if isinstance(criteria, dict):
                        for operator, value in criteria.items():
                            query_builder = query_builder.filter(column, operator, value)
                    else:
                        query_builder = query_builder.eq(column, criteria)
                
                result = query_builder.execute()
                return result.data, True, None
                
            elif operation == "rpc":
                function_name = query_obj.get("function")
                params = query_obj.get("params", {})
                
                if not function_name:
                    return None, False, "RPC operation requires function name"
                
                result = self.client.rpc(function_name, params).execute()
                return result.data, True, None
                
            elif operation == "storage_list":
                bucket = query_obj.get("bucket")
                path = query_obj.get("path", "")
                
                if not bucket:
                    return None, False, "Storage list operation requires bucket name"
                
                result = self.client.storage.from_(bucket).list(path)
                return result, True, None
                
            else:
                return None, False, f"Unsupported operation: {operation}"
                
        except json.JSONDecodeError:
            return None, False, "Invalid JSON query format"
        except Exception as e:
            logger.exception(f"Error executing Supabase operation: {query}")
            return None, False, f"Error executing operation: {str(e)}"
        finally:
            self.disconnect()
