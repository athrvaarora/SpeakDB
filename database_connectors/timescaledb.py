import logging
import json
import os
from decimal import Decimal

# Import PostgreSQL database libraries with try/except to handle missing dependencies
try:
    import psycopg2
    from sqlalchemy import create_engine
except ImportError:
    psycopg2 = None
    create_engine = None

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TimescaleDBConnector:
    """Connector for TimescaleDB time-series databases"""
    
    def __init__(self, credentials):
        self.credentials = credentials
        self.client = None
        self.engine = None
    
    def connect(self):
        """Connect to a TimescaleDB database"""
        if not self.client:
            try:
                # Support both direct connection string and individual parameters
                if self.credentials.get("connection_string"):
                    self.client = psycopg2.connect(self.credentials.get("connection_string"))
                else:
                    host = self.credentials.get("host", "localhost")
                    port = self.credentials.get("port", 5432)
                    database = self.credentials.get("database")
                    user = self.credentials.get("user") 
                    password = self.credentials.get("password")
                    
                    if not database:
                        raise Exception("No database name provided")
                    
                    self.client = psycopg2.connect(
                        host=host,
                        port=port,
                        dbname=database,
                        user=user,
                        password=password
                    )
                
                # Create SQLAlchemy engine for schema inspection
                if self.credentials.get("connection_string"):
                    conn_string = self.credentials.get("connection_string")
                else:
                    conn_string = f"postgresql://{user}:{password}@{host}:{port}/{database}"
                
                self.engine = create_engine(conn_string)
                
            except Exception as e:
                logger.exception("Error connecting to TimescaleDB")
                raise Exception(f"Error connecting to TimescaleDB: {str(e)}")
    
    def disconnect(self):
        """Disconnect from the TimescaleDB database"""
        if self.client:
            try:
                self.client.close()
            except Exception as e:
                logger.error(f"Error disconnecting: {str(e)}")
            finally:
                self.client = None
                self.engine = None
    
    def test_connection(self):
        """Test the connection to the TimescaleDB database"""
        try:
            self.connect()
            cursor = self.client.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            return True, "Connection successful"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
        finally:
            self.disconnect()
    
    def get_schema(self):
        """Get the schema of the TimescaleDB database"""
        try:
            self.connect()
            
            cursor = self.client.cursor()
            
            # Get all hypertables
            cursor.execute("""
                SELECT hypertable_schema, hypertable_name, time_column_name
                FROM _timescaledb_catalog.hypertable
            """)
            
            hypertables = []
            for row in cursor.fetchall():
                schema, table, time_column = row
                
                # Get columns for this hypertable
                cursor.execute(f"""
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                """, (schema, table))
                
                columns = []
                for col_row in cursor.fetchall():
                    col_name, data_type = col_row
                    columns.append({
                        "name": col_name,
                        "type": data_type,
                        "is_time_column": col_name == time_column
                    })
                
                hypertables.append({
                    "schema": schema,
                    "name": table,
                    "time_column": time_column,
                    "columns": columns
                })
            
            schema_info = {
                "hypertables": hypertables
            }
            
            return schema_info
            
        except Exception as e:
            logger.exception("Error getting TimescaleDB schema")
            return {"error": f"Error getting schema: {str(e)}"}
        finally:
            self.disconnect()
    
    def execute_query(self, query):
        """
        Execute a SQL query against TimescaleDB
        
        Args:
            query (str): A SQL query string
            
        Returns:
            tuple: (result, success, error_message)
        """
        try:
            self.connect()
            
            cursor = self.client.cursor()
            cursor.execute(query)
            
            # Check if the query is a SELECT query
            if query.strip().upper().startswith("SELECT"):
                columns = [col[0] for col in cursor.description]
                results = []
                
                for row in cursor.fetchall():
                    # Create a row dict with proper type conversions
                    row_dict = {}
                    for i, value in enumerate(row):
                        col_name = columns[i]
                        # Handle Decimal values by converting to float
                        if isinstance(value, Decimal):
                            row_dict[col_name] = float(value)
                        else:
                            row_dict[col_name] = value
                    results.append(row_dict)
                
                return results, True, None
            else:
                # For non-SELECT queries
                affected_rows = cursor.rowcount
                self.client.commit()
                return {"affected_rows": affected_rows}, True, None
                
        except Exception as e:
            logger.exception(f"Error executing TimescaleDB query: {query}")
            return None, False, f"Error executing query: {str(e)}"
        finally:
            self.disconnect()