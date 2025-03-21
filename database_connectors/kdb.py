import logging
import json
import os
from decimal import Decimal

# Import Kdb+ database libraries with try/except to handle missing dependencies
try:
    import qpython
    from qpython import qconnection
except ImportError:
    qpython = None
    qconnection = None

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class KdbConnector:
    """Connector for Kdb+ time-series databases"""
    
    def __init__(self, credentials):
        self.credentials = credentials
        self.client = None
    
    def connect(self):
        """Connect to a Kdb+ database"""
        if not self.client:
            try:
                host = self.credentials.get("host", "localhost")
                port = int(self.credentials.get("port", 5000))
                username = self.credentials.get("username")
                password = self.credentials.get("password")
                
                # Create qconnection
                self.client = qconnection.QConnection(
                    host=host, 
                    port=port,
                    username=username,
                    password=password
                )
                self.client.open()
                
                # Check if script_path is provided and execute it
                script_path = self.credentials.get("script_path")
                if script_path and os.path.exists(script_path):
                    with open(script_path, 'r') as script_file:
                        script = script_file.read()
                        self.client(script)
                
            except Exception as e:
                logger.exception("Error connecting to Kdb+")
                raise Exception(f"Error connecting to Kdb+: {str(e)}")
    
    def disconnect(self):
        """Disconnect from the Kdb+ database"""
        if self.client:
            try:
                self.client.close()
            except Exception as e:
                logger.error(f"Error disconnecting from Kdb+: {str(e)}")
            finally:
                self.client = None
    
    def test_connection(self):
        """Test the connection to the Kdb+ database"""
        try:
            self.connect()
            # Simple query to test connection
            self.client('1+1')
            return True, "Connection successful"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
        finally:
            self.disconnect()
    
    def get_schema(self):
        """Get the schema of the Kdb+ database"""
        try:
            self.connect()
            
            # Get tables using .Q.tables[]
            tables_result = self.client('.Q.tables[]')
            tables = []
            
            if tables_result:
                for table in tables_result:
                    # Get column info for each table
                    columns_result = self.client(f"{{`name`type!(key flip value x)@\\:where not key[x]like\"*#\"}}`:{table}")
                    
                    columns = []
                    if isinstance(columns_result, dict):
                        names = columns_result.get('name', [])
                        types = columns_result.get('type', [])
                        
                        for i in range(len(names)):
                            columns.append({
                                "name": names[i],
                                "type": types[i] if i < len(types) else "unknown"
                            })
                    
                    tables.append({
                        "name": table,
                        "columns": columns
                    })
            
            schema_info = {
                "tables": tables
            }
            
            return schema_info
            
        except Exception as e:
            logger.exception("Error getting Kdb+ schema")
            return {"error": f"Error getting schema: {str(e)}"}
        finally:
            self.disconnect()
    
    def execute_query(self, query):
        """
        Execute a q query against Kdb+
        
        Args:
            query (str): A q query string
            
        Returns:
            tuple: (result, success, error_message)
        """
        try:
            self.connect()
            
            # Execute the q query
            result = self.client(query)
            
            # Convert result to Python objects
            if hasattr(result, 'tolist'):
                result = result.tolist()
            elif hasattr(result, 'items'):
                # Convert dict-like objects
                result = {str(k): self._convert_kdb_value(v) for k, v in result.items()}
            
            return result, True, None
                
        except Exception as e:
            logger.exception(f"Error executing Kdb+ query: {query}")
            return None, False, f"Error executing query: {str(e)}"
        finally:
            self.disconnect()
    
    def _convert_kdb_value(self, value):
        """Helper to convert Kdb+ values to Python objects"""
        if hasattr(value, 'tolist'):
            return value.tolist()
        elif hasattr(value, 'items'):
            return {str(k): self._convert_kdb_value(v) for k, v in value.items()}
        elif isinstance(value, Decimal):
            return float(value)
        else:
            return value