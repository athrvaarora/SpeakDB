import logging
import os
import re

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class HerokuConnector:
    """Connector for Heroku Postgres databases"""
    
    def __init__(self, credentials):
        self.credentials = credentials
        self.connection = None
        
    def connect(self):
        """Connect to a Heroku Postgres database"""
        if not self.connection:
            try:
                # Get credentials
                api_key = self.credentials.get("api_key")
                app_name = self.credentials.get("app_name")
                database_url = self.credentials.get("database_url")
                
                # Validate credentials
                if not database_url:
                    if not api_key or not app_name:
                        raise ValueError("Either database_url or both api_key and app_name are required")
                    
                    # If we have api_key and app_name but no database_url,
                    # we could try to get the database URL from the Heroku API
                    # This would require external API calls which we'll skip for now
                    raise ValueError("Direct database_url is required for connection")
                
                # Parse the database URL to get connection parameters
                # Expected format: postgres://username:password@hostname:port/database_name
                try:
                    pattern = r'postgres:\/\/([^:]+):([^@]+)@([^:]+):(\d+)\/(.+)'
                    match = re.match(pattern, database_url)
                    
                    if not match:
                        raise ValueError("Invalid database URL format")
                    
                    username, password, host, port, database_name = match.groups()
                    
                    # Import psycopg2 for PostgreSQL connection
                    try:
                        import psycopg2
                    except ImportError:
                        raise ImportError("psycopg2 package is required to connect to Heroku Postgres")
                    
                    # Connect to the database
                    self.connection = psycopg2.connect(
                        dbname=database_name,
                        user=username,
                        password=password,
                        host=host,
                        port=port
                    )
                    
                except Exception as e:
                    raise ValueError(f"Error parsing database URL or connecting: {str(e)}")
                
            except Exception as e:
                logger.exception("Error connecting to Heroku Postgres")
                raise Exception(f"Error connecting to Heroku Postgres: {str(e)}")
    
    def disconnect(self):
        """Disconnect from the Heroku Postgres database"""
        if self.connection:
            try:
                self.connection.close()
            except Exception as e:
                logger.error(f"Error disconnecting from Heroku Postgres: {str(e)}")
            finally:
                self.connection = None
    
    def test_connection(self):
        """Test the connection to the Heroku Postgres database"""
        try:
            self.connect()
            return True, "Connection successful"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
        finally:
            self.disconnect()
    
    def get_schema(self):
        """Get the schema of the Heroku Postgres database"""
        try:
            self.connect()
            
            if not self.connection:
                return {"error": "Not connected to Heroku Postgres"}
            
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
            logger.exception("Error retrieving Heroku Postgres schema")
            return {"error": str(e)}
        finally:
            self.disconnect()
    
    def execute_query(self, query):
        """
        Execute a SQL query against Heroku Postgres
        
        Args:
            query (str): A SQL query string
            
        Returns:
            tuple: (result, success, error_message)
        """
        try:
            self.connect()
            
            if not self.connection:
                return None, False, "Not connected to Heroku Postgres"
            
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
            logger.exception(f"Error executing Heroku Postgres query: {query}")
            return None, False, f"Error executing query: {str(e)}"
        finally:
            self.disconnect()