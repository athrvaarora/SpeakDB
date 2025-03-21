import logging
import json
import os
import requests
from requests.auth import HTTPBasicAuth
from decimal import Decimal
from urllib.parse import urljoin

# Import time-series database libraries with try/except to handle missing dependencies
try:
    from influxdb_client import InfluxDBClient
    from influxdb_client.client.write_api import SYNCHRONOUS
except ImportError:
    InfluxDBClient = None

try:
    import psycopg2
    from sqlalchemy import create_engine
except ImportError:
    psycopg2 = None

try:
    import qpython
    from qpython import qconnection
except ImportError:
    qpython = None

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
                # Get URL from credentials
                url = self.credentials.get("url", "http://localhost:8086")
                
                # Use token authentication if provided (InfluxDB 2.x)
                token = self.credentials.get("token")
                org = self.credentials.get("org")
                bucket = self.credentials.get("bucket")
                
                # Fall back to username/password auth if token not provided (InfluxDB 1.x)
                username = self.credentials.get("username")
                password = self.credentials.get("password")
                
                if token:
                    self.client = InfluxDBClient(url=url, token=token, org=org)
                elif username and password:
                    # For InfluxDB 1.x compatibility
                    self.client = InfluxDBClient(url=url, username=username, password=password, org=org)
                else:
                    raise Exception("Either token or username/password must be provided")
                
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


class PrometheusConnector(BaseTimeSeriesConnector):
    """Connector for Prometheus monitoring system"""
    
    def __init__(self, credentials):
        super().__init__(credentials)
        self.base_url = None
        self.auth = None
    
    def connect(self):
        """Connect to a Prometheus server"""
        try:
            # Support both URL field and hostname/port fields
            if self.credentials.get("url"):
                self.base_url = self.credentials.get("url")
            else:
                hostname = self.credentials.get("hostname", "localhost")
                port = self.credentials.get("port", 9090)
                self.base_url = f"http://{hostname}:{port}"
            
            # Set up authentication if provided
            username = self.credentials.get("username")
            password = self.credentials.get("password")
            if username and password:
                self.auth = HTTPBasicAuth(username, password)
            
            # Test connection
            url = urljoin(self.base_url, "/api/v1/status/config")
            response = requests.get(url, auth=self.auth)
            response.raise_for_status()
            
            self.client = True  # Just a flag to indicate connection is established
            return True
            
        except Exception as e:
            logger.exception("Error connecting to Prometheus")
            raise Exception(f"Error connecting to Prometheus: {str(e)}")
    
    def disconnect(self):
        """Disconnect from Prometheus"""
        self.client = None
        self.base_url = None
        self.auth = None
    
    def get_schema(self):
        """Get metadata from Prometheus"""
        try:
            self.connect()
            
            # Get list of metrics
            url = urljoin(self.base_url, "/api/v1/label/__name__/values")
            response = requests.get(url, auth=self.auth)
            response.raise_for_status()
            data = response.json()
            
            metrics = data.get("data", [])
            
            return {
                "metrics": metrics,
                "message": f"Found {len(metrics)} metrics"
            }
            
        except Exception as e:
            logger.exception("Error getting Prometheus schema")
            return {"error": f"Error getting schema: {str(e)}"}
        finally:
            self.disconnect()
    
    def execute_query(self, query):
        """
        Execute a PromQL query against Prometheus
        
        Args:
            query (str): A PromQL query string or JSON with query details
            
        Returns:
            tuple: (result, success, error_message)
        """
        try:
            self.connect()
            
            # Check if query is a JSON with operation details
            try:
                query_obj = json.loads(query)
                promql_query = query_obj.get("query")
                time = query_obj.get("time")
                timeout = query_obj.get("timeout")
                
                # Use the query field if provided, otherwise use the raw query string
                if promql_query:
                    query = promql_query
                
            except json.JSONDecodeError:
                # If not JSON, assume it's a direct PromQL query
                pass
            
            # Build query parameters
            params = {"query": query}
            if time:
                params["time"] = time
            if timeout:
                params["timeout"] = timeout
            
            # Execute query
            url = urljoin(self.base_url, "/api/v1/query")
            response = requests.get(url, params=params, auth=self.auth)
            response.raise_for_status()
            
            result = response.json()
            
            # Check for errors
            if result.get("status") != "success":
                error_msg = result.get("error", "Unknown error")
                error_type = result.get("errorType", "")
                return None, False, f"{error_type}: {error_msg}"
            
            return result.get("data", {}), True, None
            
        except Exception as e:
            logger.exception(f"Error executing Prometheus query: {query}")
            return None, False, f"Error executing query: {str(e)}"
        finally:
            self.disconnect()
