import logging
import json
import os
import snowflake.connector
from google.cloud import bigquery
import pyodbc

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class BaseDataWarehouseConnector:
    """Base class for data warehouse connectors"""
    
    def __init__(self, credentials):
        self.credentials = credentials
        self.client = None
    
    def connect(self):
        """Connect to the data warehouse"""
        raise NotImplementedError("Subclasses must implement connect()")
    
    def disconnect(self):
        """Disconnect from the data warehouse"""
        if self.client:
            try:
                self.client.close()
            except Exception as e:
                logger.error(f"Error disconnecting: {str(e)}")
            finally:
                self.client = None
    
    def test_connection(self):
        """Test the connection to the data warehouse"""
        try:
            self.connect()
            return True, "Connection successful"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
        finally:
            self.disconnect()
    
    def get_schema(self):
        """Get the schema of the data warehouse"""
        raise NotImplementedError("Subclasses must implement get_schema()")
    
    def execute_query(self, query):
        """
        Execute a query against the data warehouse
        
        Args:
            query (str): The query to execute
            
        Returns:
            tuple: (result, success, error_message)
        """
        raise NotImplementedError("Subclasses must implement execute_query()")

class SnowflakeConnector(BaseDataWarehouseConnector):
    """Connector for Snowflake data warehouses"""
    
    def connect(self):
        """Connect to a Snowflake data warehouse"""
        if not self.client:
            try:
                # Get credentials from credentials dict or environment variables
                account = self.credentials.get("account") or os.environ.get("SNOWFLAKE_ACCOUNT")
                username = self.credentials.get("username") or os.environ.get("SNOWFLAKE_USER")
                password = self.credentials.get("password") or os.environ.get("SNOWFLAKE_PASSWORD")
                warehouse = self.credentials.get("warehouse") or os.environ.get("SNOWFLAKE_WAREHOUSE")
                database = self.credentials.get("db_name") or os.environ.get("SNOWFLAKE_DATABASE")
                
                # Log if using environment variables
                if os.environ.get("SNOWFLAKE_ACCOUNT") and not self.credentials.get("account"):
                    logger.info("Using SNOWFLAKE_ACCOUNT environment variable")
                if os.environ.get("SNOWFLAKE_USER") and not self.credentials.get("username"):
                    logger.info("Using SNOWFLAKE_USER environment variable")
                if os.environ.get("SNOWFLAKE_PASSWORD") and not self.credentials.get("password"):
                    logger.info("Using SNOWFLAKE_PASSWORD environment variable")
                if os.environ.get("SNOWFLAKE_WAREHOUSE") and not self.credentials.get("warehouse"):
                    logger.info("Using SNOWFLAKE_WAREHOUSE environment variable")
                if os.environ.get("SNOWFLAKE_DATABASE") and not self.credentials.get("db_name"):
                    logger.info("Using SNOWFLAKE_DATABASE environment variable")
                
                # Check for required credentials
                if not account or not username or not password:
                    raise ValueError("Account, username, and password are required for Snowflake connection")
                
                self.client = snowflake.connector.connect(
                    account=account,
                    user=username,
                    password=password,
                    warehouse=warehouse,
                    database=database
                )
                
            except Exception as e:
                logger.exception("Error connecting to Snowflake")
                raise Exception(f"Error connecting to Snowflake: {str(e)}")
    
    def get_schema(self):
        """Get the schema of the Snowflake data warehouse"""
        try:
            self.connect()
            
            cursor = self.client.cursor()
            
            # Get schemas
            cursor.execute("SHOW SCHEMAS")
            schemas = cursor.fetchall()
            
            schema_info = {
                "schemas": []
            }
            
            for schema_row in schemas:
                schema_name = schema_row[1]
                
                # Skip system schemas
                if schema_name.startswith('INFORMATION_SCHEMA'):
                    continue
                
                schema_info["schemas"].append({
                    "name": schema_name,
                    "tables": []
                })
                
                # Get tables for this schema
                cursor.execute(f"SHOW TABLES IN SCHEMA {schema_name}")
                tables = cursor.fetchall()
                
                for table_row in tables:
                    table_name = table_row[1]
                    
                    # Get columns for this table
                    cursor.execute(f"DESCRIBE TABLE {schema_name}.{table_name}")
                    columns = cursor.fetchall()
                    
                    table_info = {
                        "name": table_name,
                        "columns": []
                    }
                    
                    for column_row in columns:
                        column_info = {
                            "name": column_row[0],
                            "type": column_row[1],
                            "nullable": column_row[3] == "Y"
                        }
                        
                        table_info["columns"].append(column_info)
                    
                    schema_info["schemas"][-1]["tables"].append(table_info)
            
            return schema_info
            
        except Exception as e:
            logger.exception("Error getting Snowflake schema")
            return {"error": f"Error getting schema: {str(e)}"}
        finally:
            self.disconnect()
    
    def execute_query(self, query):
        """
        Execute a SQL query against Snowflake
        
        Args:
            query (str): A SQL query string
            
        Returns:
            tuple: (result, success, error_message)
        """
        try:
            self.connect()
            
            cursor = self.client.cursor()
            cursor.execute(query)
            
            # Check if the query returns results
            if cursor.description:
                columns = [col[0] for col in cursor.description]
                results = []
                
                for row in cursor.fetchall():
                    results.append(dict(zip(columns, row)))
                
                return results, True, None
            else:
                # For non-query statements (INSERT, UPDATE, etc.)
                self.client.commit()
                return {"affected_rows": cursor.rowcount}, True, None
            
        except Exception as e:
            logger.exception(f"Error executing Snowflake query: {query}")
            return None, False, f"Error executing query: {str(e)}"
        finally:
            self.disconnect()

class BigQueryConnector(BaseDataWarehouseConnector):
    """Connector for Google BigQuery data warehouses"""
    
    def connect(self):
        """Connect to a Google BigQuery data warehouse"""
        if not self.client:
            try:
                # Get credentials from credentials or environment variables
                project_id = self.credentials.get("project_id") or os.environ.get("GCP_PROJECT_ID")
                
                # Check if credentials file is specified in environment
                if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") and not self.credentials.get("project_id"):
                    logger.info("Using GOOGLE_APPLICATION_CREDENTIALS environment variable")
                    # When GOOGLE_APPLICATION_CREDENTIALS is set, the client will use it automatically
                
                if os.environ.get("GCP_PROJECT_ID") and not self.credentials.get("project_id"):
                    logger.info("Using GCP_PROJECT_ID environment variable")
                
                if not project_id:
                    raise ValueError("Project ID is required (either in credentials or as GCP_PROJECT_ID environment variable)")
                
                # Initialize BigQuery client
                self.client = bigquery.Client(project=project_id)
                
            except Exception as e:
                logger.exception("Error connecting to BigQuery")
                raise Exception(f"Error connecting to BigQuery: {str(e)}")
    
    def get_schema(self):
        """Get the schema of the BigQuery data warehouse"""
        try:
            self.connect()
            
            # Get dataset_id from credentials or environment variables
            dataset_id = self.credentials.get("dataset") or os.environ.get("GCP_DATASET_ID")
            
            if not dataset_id:
                raise ValueError("Dataset ID is required (either in credentials or as GCP_DATASET_ID environment variable)")
            
            schema_info = {
                "dataset": dataset_id,
                "tables": []
            }
            
            # Get list of tables in the dataset
            tables = self.client.list_tables(dataset_id)
            
            for table in tables:
                table_ref = self.client.get_table(table)
                
                table_info = {
                    "name": table.table_id,
                    "columns": []
                }
                
                for field in table_ref.schema:
                    column_info = {
                        "name": field.name,
                        "type": field.field_type,
                        "mode": field.mode
                    }
                    
                    table_info["columns"].append(column_info)
                
                schema_info["tables"].append(table_info)
            
            return schema_info
            
        except Exception as e:
            logger.exception("Error getting BigQuery schema")
            return {"error": f"Error getting schema: {str(e)}"}
        finally:
            self.disconnect()
    
    def execute_query(self, query):
        """
        Execute a SQL query against BigQuery
        
        Args:
            query (str): A SQL query string
            
        Returns:
            tuple: (result, success, error_message)
        """
        try:
            self.connect()
            
            # Execute the query
            query_job = self.client.query(query)
            result = query_job.result()
            
            # Convert rows to dictionaries
            results = []
            for row in result:
                row_dict = {}
                for key, value in row.items():
                    row_dict[key] = value
                results.append(row_dict)
            
            return results, True, None
            
        except Exception as e:
            logger.exception(f"Error executing BigQuery query: {query}")
            return None, False, f"Error executing query: {str(e)}"
        finally:
            self.disconnect()

class SynapseConnector(BaseDataWarehouseConnector):
    """Connector for Azure Synapse Analytics data warehouses"""
    
    def connect(self):
        """Connect to an Azure Synapse Analytics data warehouse"""
        if not self.client:
            try:
                # Get credentials from credentials dict or environment variables
                server = self.credentials.get("server") or os.environ.get("SYNAPSE_SERVER")
                username = self.credentials.get("username") or os.environ.get("SYNAPSE_USERNAME")
                password = self.credentials.get("password") or os.environ.get("SYNAPSE_PASSWORD")
                database = self.credentials.get("db_name") or os.environ.get("SYNAPSE_DATABASE")
                
                # Log if using environment variables
                if os.environ.get("SYNAPSE_SERVER") and not self.credentials.get("server"):
                    logger.info("Using SYNAPSE_SERVER environment variable")
                if os.environ.get("SYNAPSE_USERNAME") and not self.credentials.get("username"):
                    logger.info("Using SYNAPSE_USERNAME environment variable")
                if os.environ.get("SYNAPSE_PASSWORD") and not self.credentials.get("password"):
                    logger.info("Using SYNAPSE_PASSWORD environment variable")
                if os.environ.get("SYNAPSE_DATABASE") and not self.credentials.get("db_name"):
                    logger.info("Using SYNAPSE_DATABASE environment variable")
                
                # Check for required credentials
                if not server or not username or not password or not database:
                    raise ValueError("Server, username, password, and database are required for Azure Synapse Analytics connection")
                
                # Connect to Synapse using pyodbc
                conn_str = f"Driver={{ODBC Driver 17 for SQL Server}};Server=tcp:{server},1433;Database={database};Uid={username};Pwd={password};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
                self.client = pyodbc.connect(conn_str)
                
            except Exception as e:
                logger.exception("Error connecting to Azure Synapse Analytics")
                raise Exception(f"Error connecting to Azure Synapse Analytics: {str(e)}")
    
    def get_schema(self):
        """Get the schema of the Azure Synapse Analytics data warehouse"""
        try:
            self.connect()
            
            cursor = self.client.cursor()
            
            schema_info = {
                "schemas": []
            }
            
            # Get schemas
            cursor.execute("SELECT name FROM sys.schemas WHERE name NOT IN ('sys', 'INFORMATION_SCHEMA')")
            schemas = cursor.fetchall()
            
            for schema_row in schemas:
                schema_name = schema_row[0]
                
                schema_info["schemas"].append({
                    "name": schema_name,
                    "tables": []
                })
                
                # Get tables for this schema
                cursor.execute(f"SELECT name FROM sys.tables WHERE schema_id = SCHEMA_ID('{schema_name}')")
                tables = cursor.fetchall()
                
                for table_row in tables:
                    table_name = table_row[0]
                    
                    # Get columns for this table
                    cursor.execute(f"""
                        SELECT c.name, t.name AS type, c.is_nullable
                        FROM sys.columns c
                        JOIN sys.types t ON c.user_type_id = t.user_type_id
                        WHERE c.object_id = OBJECT_ID('{schema_name}.{table_name}')
                    """)
                    columns = cursor.fetchall()
                    
                    table_info = {
                        "name": table_name,
                        "columns": []
                    }
                    
                    for column_row in columns:
                        column_info = {
                            "name": column_row[0],
                            "type": column_row[1],
                            "nullable": column_row[2] == 1
                        }
                        
                        table_info["columns"].append(column_info)
                    
                    schema_info["schemas"][-1]["tables"].append(table_info)
            
            return schema_info
            
        except Exception as e:
            logger.exception("Error getting Azure Synapse Analytics schema")
            return {"error": f"Error getting schema: {str(e)}"}
        finally:
            self.disconnect()
    
    def execute_query(self, query):
        """
        Execute a SQL query against Azure Synapse Analytics
        
        Args:
            query (str): A SQL query string
            
        Returns:
            tuple: (result, success, error_message)
        """
        try:
            self.connect()
            
            cursor = self.client.cursor()
            cursor.execute(query)
            
            # Check if the query returns results
            if cursor.description:
                columns = [col[0] for col in cursor.description]
                results = []
                
                for row in cursor.fetchall():
                    results.append(dict(zip(columns, row)))
                
                return results, True, None
            else:
                # For non-query statements (INSERT, UPDATE, etc.)
                self.client.commit()
                return {"affected_rows": cursor.rowcount}, True, None
            
        except Exception as e:
            logger.exception(f"Error executing Azure Synapse Analytics query: {query}")
            return None, False, f"Error executing query: {str(e)}"
        finally:
            self.disconnect()
