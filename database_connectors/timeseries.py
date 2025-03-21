import logging
import json
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class BaseTimeSeriesConnector:
    """Base class for time-series database connectors"""
    
    def __init__(self, credentials):
        self.credentials = credentials
        self.client = None
    
    def connect(self):
        """Connect to the time-series database"""
        raise NotImplementedError("Subclasses must implement connect()")
    
    def disconnect(self):
        """Disconnect from the time-series database"""
        if self.client:
            try:
                self.client.close()
            except Exception as e:
                logger.error(f"Error disconnecting: {str(e)}")
            finally:
                self.client = None
    
    def test_connection(self):
        """Test the connection to the time-series database"""
        try:
            self.connect()
            return True, "Connection successful"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
        finally:
            self.disconnect()
    
    def get_schema(self):
        """Get the schema of the time-series database"""
        return {"message": "Schema retrieval is limited for time-series databases"}
    
    def execute_query(self, query):
        """
        Execute a query against the time-series database
        
        Args:
            query (str): The query to execute
            
        Returns:
            tuple: (result, success, error_message)
        """
        raise NotImplementedError("Subclasses must implement execute_query()")

class InfluxDBConnector(BaseTimeSeriesConnector):
    """Connector for InfluxDB time-series databases"""
    
    def connect(self):
        """Connect to an InfluxDB time-series database"""
        if not self.client:
            try:
                host = self.credentials.get("host", "localhost")
                port = self.credentials.get("port", 8086)
                token = self.credentials.get("token")
                org = self.credentials.get("org")
                
                url = f"http://{host}:{port}"
                
                self.client = InfluxDBClient(url=url, token=token, org=org)
                self.query_api = self.client.query_api()
                self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
                
            except Exception as e:
                logger.exception("Error connecting to InfluxDB")
                raise Exception(f"Error connecting to InfluxDB: {str(e)}")
    
    def get_schema(self):
        """Get the buckets and measurements in the InfluxDB database"""
        try:
            self.connect()
            
            org = self.credentials.get("org")
            
            schema_info = {
                "buckets": []
            }
            
            # Get all buckets
            buckets_api = self.client.buckets_api()
            buckets = buckets_api.find_buckets().buckets
            
            for bucket in buckets:
                bucket_info = {
                    "name": bucket.name,
                    "id": bucket.id,
                    "measurements": []
                }
                
                # For InfluxDB 2.x, we need to use Flux to get measurements
                # This might be resource-intensive for large datasets
                try:
                    query = f'import "influxdata/influxdb/schema"\n\nschema.measurements(bucket: "{bucket.name}")'
                    result = self.query_api.query(query, org=org)
                    
                    measurements = []
                    for table in result:
                        for record in table.records:
                            measurements.append(record.values.get("_value"))
                    
                    bucket_info["measurements"] = measurements
                except Exception as e:
                    logger.warning(f"Error getting measurements for bucket {bucket.name}: {str(e)}")
                
                schema_info["buckets"].append(bucket_info)
            
            return schema_info
            
        except Exception as e:
            logger.exception("Error getting InfluxDB schema")
            return {"error": f"Error getting schema: {str(e)}"}
        finally:
            self.disconnect()
    
    def execute_query(self, query):
        """
        Execute a Flux query against InfluxDB
        
        Args:
            query (str): Either a Flux query string or a JSON string with operation details
            
        Returns:
            tuple: (result, success, error_message)
        """
        try:
            self.connect()
            
            org = self.credentials.get("org")
            
            # Check if the query is a JSON string for write operations
            try:
                query_obj = json.loads(query)
                operation = query_obj.get("operation")
                
                if operation == "write":
                    bucket = query_obj.get("bucket")
                    data = query_obj.get("data")
                    
                    if not bucket or not data:
                        return None, False, "Write operation requires bucket and data"
                    
                    # Data can be a list of points or a single point
                    if isinstance(data, list):
                        self.write_api.write(bucket=bucket, record=data)
                    else:
                        self.write_api.write(bucket=bucket, record=data)
                    
                    return {"status": "success"}, True, None
                    
                elif operation == "query":
                    flux_query = query_obj.get("flux_query")
                    
                    if not flux_query:
                        return None, False, "Query operation requires flux_query"
                    
                    result = self.query_api.query(flux_query, org=org)
                    
                    # Convert result to a list of dictionaries
                    results = []
                    for table in result:
                        for record in table.records:
                            results.append(record.values)
                    
                    return results, True, None
                    
                else:
                    return None, False, f"Unsupported operation: {operation}"
                    
            except json.JSONDecodeError:
                # If not JSON, assume it's a Flux query
                result = self.query_api.query(query, org=org)
                
                # Convert result to a list of dictionaries
                results = []
                for table in result:
                    for record in table.records:
                        results.append(record.values)
                
                return results, True, None
                
        except Exception as e:
            logger.exception(f"Error executing InfluxDB query: {query}")
            return None, False, f"Error executing query: {str(e)}"
        finally:
            self.disconnect()
