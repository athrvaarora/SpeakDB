import logging
import os
import re

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class NeonConnector:
    """Connector for Neon serverless PostgreSQL databases"""
    
    def __init__(self, credentials):
        self.credentials = credentials
        self.connection = None
        
    def connect(self):
        """Connect to a Neon serverless PostgreSQL database"""
        if not self.connection:
            try:
                # Get credentials
                db_url = self.credentials.get("db_url")
                api_key = self.credentials.get("api_key")
                project_id = self.credentials.get("project_id")
                
                host = self.credentials.get("host")
                port = self.credentials.get("port", "5432")
                database_name = self.credentials.get("database_name")
                username = self.credentials.get("username")
                password = self.credentials.get("password")
                
                # If a full URL is provided, use it
                if db_url:
                    # Parse the database URL to get connection parameters
                    # Expected format: postgres://username:password@hostname:port/database_name
                    try:
                        pattern = r'postgres:\/\/([^:]+):([^@]+)@([^:]+):(\d+)\/(.+)'
                        match = re.match(pattern, db_url)
                        
                        if not match:
                            raise ValueError("Invalid database URL format")
                        
                        username, password, host, port, database_name = match.groups()
                    except Exception as e:
                        raise ValueError(f"Error parsing database URL: {str(e)}")
                else:
                    # Check if individual credentials are provided
                    if not all([host, username, password, database_name]):
                        raise ValueError("Either db_url or all individual credentials (host, username, password, database_name) are required")
                
                # Import psycopg2 for PostgreSQL connection
                try:
                    import psycopg2
                except ImportError:
                    raise ImportError("psycopg2 package is required to connect to Neon PostgreSQL")
                
                # Connect to the database
                self.connection = psycopg2.connect(
                    dbname=database_name,
                    user=username,
                    password=password,
                    host=host,
                    port=port
                )
                
            except Exception as e:
                logger.exception("Error connecting to Neon PostgreSQL")
                raise Exception(f"Error connecting to Neon PostgreSQL: {str(e)}")
    
    def disconnect(self):
        """Disconnect from the Neon PostgreSQL database"""
        if self.connection:
            try:
                self.connection.close()
            except Exception as e:
                logger.error(f"Error disconnecting from Neon PostgreSQL: {str(e)}")
            finally:
                self.connection = None
    
    def test_connection(self):
        """Test the connection to the Neon PostgreSQL database"""
        try:
            self.connect()
            return True, "Connection successful"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
        finally:
            self.disconnect()
    
    def get_schema(self):
        """Get the schema of the Neon PostgreSQL database"""
        try:
            self.connect()
            
            if not self.connection:
                return {"error": "Not connected to Neon PostgreSQL"}
            
            cursor = self.connection.cursor()
            
            # Query to get all tables in the database
            cursor.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            
            tables = [row[0] for row in cursor.fetchall()]
            
            schema_info = {"tables": {}}
            
            # Get columns for each table
            for table in tables:
                cursor.execute(f"""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_schema = 'public' AND table_name = %s 
                    ORDER BY ordinal_position;
                """, (table,))
                
                columns = {row[0]: row[1] for row in cursor.fetchall()}
                schema_info["tables"][table] = columns
            
            cursor.close()
            return schema_info
            
        except Exception as e:
            logger.exception("Error retrieving Neon PostgreSQL schema")
            return {"error": str(e)}
        finally:
            self.disconnect()
    
    def execute_query(self, query):
        """
        Execute a SQL query against Neon PostgreSQL
        
        Args:
            query (str): A SQL query string
            
        Returns:
            tuple: (result, success, error_message)
        """
        try:
            self.connect()
            
            if not self.connection:
                return None, False, "Not connected to Neon PostgreSQL"
            
            cursor = self.connection.cursor()
            
            # Execute the query
            cursor.execute(query)
            
            # If this is a SELECT query or similar, fetch results
            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                results = []
                
                for row in cursor.fetchall():
                    result_dict = {}
                    for i, col in enumerate(columns):
                        result_dict[col] = row[i]
                    results.append(result_dict)
                
                cursor.close()
                return results, True, None
            
            # For non-SELECT queries (INSERT, UPDATE, DELETE, etc.)
            else:
                self.connection.commit()
                affected_rows = cursor.rowcount
                cursor.close()
                return {"affected_rows": affected_rows}, True, None
            
        except Exception as e:
            logger.exception(f"Error executing Neon PostgreSQL query: {query}")
            return None, False, f"Error executing query: {str(e)}"
        finally:
            self.disconnect()