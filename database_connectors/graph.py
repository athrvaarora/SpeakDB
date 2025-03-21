import logging
import json
import os
import requests
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class BaseGraphConnector:
    """Base class for graph database connectors"""
    
    def __init__(self, credentials):
        self.credentials = credentials
        self.connection = None
        
    def connect(self):
        """Connect to the graph database"""
        pass
        
    def disconnect(self):
        """Disconnect from the graph database"""
        pass
        
    def test_connection(self):
        """Test the connection to the graph database"""
        try:
            self.connect()
            return True, "Connection successful"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"
        finally:
            self.disconnect()
        
    def get_schema(self):
        """Get the schema of the graph database"""
        return {"error": "Not implemented"}
        
    def execute_query(self, query):
        """
        Execute a query against the graph database
        
        Args:
            query (str): The query to execute
            
        Returns:
            tuple: (result, success, error_message)
        """
        return None, False, "Not implemented"

class TigerGraphConnector(BaseGraphConnector):
    """Connector for TigerGraph databases"""
    
    def __init__(self, credentials):
        super().__init__(credentials)
        self.endpoint = self.credentials.get("endpoint")
        self.token = self.credentials.get("token")
        self.graph_name = self.credentials.get("graph_name")
        self.username = self.credentials.get("username")
        self.password = self.credentials.get("password")
        self.secret = self.credentials.get("secret")
    
    def connect(self):
        """Connect to a TigerGraph database"""
        try:
            # Try importing pyTigerGraph
            try:
                import pyTigerGraph as tg
            except ImportError:
                raise ImportError("pyTigerGraph package is required to connect to TigerGraph")
            
            # Validate required credentials
            if not self.endpoint:
                raise ValueError("TigerGraph endpoint URL is required")
            
            # Initialize connection
            if self.token:
                # Connect using token auth
                self.connection = tg.TigerGraphConnection(
                    host=self.endpoint,
                    graphname=self.graph_name,
                    apiToken=self.token
                )
            elif self.username and self.password:
                # Connect using username/password auth
                self.connection = tg.TigerGraphConnection(
                    host=self.endpoint,
                    graphname=self.graph_name,
                    username=self.username,
                    password=self.password
                )
            elif self.secret:
                # Get token using secret
                self.connection = tg.TigerGraphConnection(
                    host=self.endpoint,
                    graphname=self.graph_name,
                    secret=self.secret
                )
                # Generate a token
                self.token = self.connection.getToken(self.secret, "30d")[0]
                # Reconnect with token
                self.connection = tg.TigerGraphConnection(
                    host=self.endpoint,
                    graphname=self.graph_name,
                    apiToken=self.token
                )
            else:
                raise ValueError("TigerGraph authentication required. Provide either token, username/password, or secret.")
            
        except Exception as e:
            logger.exception("Error connecting to TigerGraph")
            self.connection = None
            raise Exception(f"Error connecting to TigerGraph: {str(e)}")
    
    def disconnect(self):
        """Disconnect from the TigerGraph database"""
        self.connection = None
    
    def get_schema(self):
        """Get the schema of the TigerGraph database"""
        try:
            self.connect()
            
            if not self.connection:
                return {"error": "Not connected to TigerGraph"}
            
            schema_info = {
                "vertices": {},
                "edges": {}
            }
            
            # Get vertex types
            vertex_types = self.connection.getVertexTypes()
            for vertex_type in vertex_types:
                vertex_schema = self.connection.getVertexType(vertex_type)
                schema_info["vertices"][vertex_type] = vertex_schema
            
            # Get edge types
            edge_types = self.connection.getEdgeTypes()
            for edge_type in edge_types:
                edge_schema = self.connection.getEdgeType(edge_type)
                schema_info["edges"][edge_type] = edge_schema
            
            return schema_info
            
        except Exception as e:
            logger.exception("Error retrieving TigerGraph schema")
            return {"error": str(e)}
        finally:
            self.disconnect()
    
    def execute_query(self, query):
        """
        Execute a query against TigerGraph
        
        Args:
            query (str): Either a GSQL query string or a JSON string defining an operation
            
        Returns:
            tuple: (result, success, error_message)
        """
        try:
            self.connect()
            
            if not self.connection:
                return None, False, "Not connected to TigerGraph"
            
            # Check if the query is a JSON string
            try:
                query_json = json.loads(query)
                
                # Determine the operation type
                operation = query_json.get("operation", "").lower()
                
                if operation == "installed_query":
                    # Run an installed query
                    query_name = query_json.get("query_name")
                    params = query_json.get("params", {})
                    
                    if not query_name:
                        return None, False, "Query name is required for installed_query operation"
                    
                    result = self.connection.runInstalledQuery(query_name, params)
                    return result, True, None
                    
                elif operation == "interpret":
                    # Run an interpreted query
                    gsql = query_json.get("gsql")
                    
                    if not gsql:
                        return None, False, "GSQL code is required for interpret operation"
                    
                    result = self.connection.runInterpretedQuery(gsql)
                    return result, True, None
                    
                elif operation == "vertex":
                    # Get vertices
                    vertex_type = query_json.get("type")
                    vertex_id = query_json.get("id")
                    
                    if not vertex_type:
                        return None, False, "Vertex type is required for vertex operation"
                    
                    if vertex_id:
                        # Get a specific vertex
                        result = self.connection.getVerticesById(vertex_type, vertex_id)
                    else:
                        # Get all vertices of a type
                        result = self.connection.getVertices(vertex_type)
                        
                    return result, True, None
                    
                elif operation == "edge":
                    # Get edges
                    edge_type = query_json.get("type")
                    source_type = query_json.get("source_type")
                    source_id = query_json.get("source_id")
                    target_type = query_json.get("target_type")
                    target_id = query_json.get("target_id")
                    
                    if not edge_type or not source_type or not source_id:
                        return None, False, "Edge type, source type, and source ID are required for edge operation"
                    
                    result = self.connection.getEdges(source_type, source_id, edge_type, target_type, target_id)
                    return result, True, None
                    
                else:
                    return None, False, f"Unsupported operation: {operation}"
                    
            except json.JSONDecodeError:
                # If it's not a JSON string, assume it's a GSQL query
                result = self.connection.runInterpretedQuery(query)
                return result, True, None
                
        except Exception as e:
            logger.exception(f"Error executing TigerGraph query: {query}")
            return None, False, f"Error executing query: {str(e)}"
        finally:
            self.disconnect()

class Neo4jConnector(BaseGraphConnector):
    """Connector for Neo4j databases"""
    
    def __init__(self, credentials):
        super().__init__(credentials)
        self.uri = self.credentials.get("uri")
        self.username = self.credentials.get("username")
        self.password = self.credentials.get("password")
        self.database = self.credentials.get("database")
    
    def connect(self):
        """Connect to a Neo4j database"""
        try:
            # Try importing neo4j
            try:
                import neo4j
            except ImportError:
                raise ImportError("neo4j package is required to connect to Neo4j")
            
            # Validate required credentials
            if not self.uri:
                raise ValueError("Neo4j URI is required")
            if not self.username or not self.password:
                raise ValueError("Neo4j username and password are required")
            
            # Initialize connection
            self.driver = neo4j.GraphDatabase.driver(
                self.uri, 
                auth=(self.username, self.password)
            )
            
            # Test connection
            with self.driver.session(database=self.database) as session:
                session.run("RETURN 1")
                
        except Exception as e:
            logger.exception("Error connecting to Neo4j")
            self.driver = None
            raise Exception(f"Error connecting to Neo4j: {str(e)}")
    
    def disconnect(self):
        """Disconnect from the Neo4j database"""
        if self.driver:
            self.driver.close()
            self.driver = None
    
    def get_schema(self):
        """Get the schema of the Neo4j database"""
        try:
            self.connect()
            
            if not self.driver:
                return {"error": "Not connected to Neo4j"}
            
            schema_info = {
                "nodes": {},
                "relationships": {}
            }
            
            with self.driver.session(database=self.database) as session:
                # Get node labels
                result = session.run("""
                    CALL db.schema.nodeTypeProperties()
                    YIELD nodeType, propertyName, propertyTypes
                    RETURN nodeType, collect({name: propertyName, types: propertyTypes}) as properties
                """)
                
                for record in result:
                    node_type = record["nodeType"]
                    properties = record["properties"]
                    schema_info["nodes"][node_type] = properties
                
                # Get relationship types
                result = session.run("""
                    CALL db.schema.relTypeProperties()
                    YIELD relType, propertyName, propertyTypes
                    RETURN relType, collect({name: propertyName, types: propertyTypes}) as properties
                """)
                
                for record in result:
                    rel_type = record["relType"]
                    properties = record["properties"]
                    schema_info["relationships"][rel_type] = properties
            
            return schema_info
            
        except Exception as e:
            logger.exception("Error retrieving Neo4j schema")
            return {"error": str(e)}
        finally:
            self.disconnect()
    
    def _neo4j_to_dict(self, value):
        """Convert Neo4j objects to dictionaries"""
        if hasattr(value, "keys") and callable(value.keys):
            return {k: self._neo4j_to_dict(value[k]) for k in value.keys()}
        elif hasattr(value, "__iter__") and not isinstance(value, (str, bytes, bytearray)):
            return [self._neo4j_to_dict(v) for v in value]
        else:
            return value
    
    def execute_query(self, query):
        """
        Execute a Cypher query against Neo4j
        
        Args:
            query (str): A Cypher query string or JSON representing a query with parameters
            
        Returns:
            tuple: (result, success, error_message)
        """
        try:
            self.connect()
            
            if not self.driver:
                return None, False, "Not connected to Neo4j"
            
            # Check if the query is a JSON string
            try:
                query_json = json.loads(query)
                cypher = query_json.get("cypher")
                params = query_json.get("params", {})
                
                if not cypher:
                    return None, False, "Cypher query is required"
                
            except json.JSONDecodeError:
                # If it's not a JSON string, assume it's a Cypher query
                cypher = query
                params = {}
            
            with self.driver.session(database=self.database) as session:
                result = session.run(cypher, params)
                records = [self._neo4j_to_dict(record) for record in result]
                return records, True, None
                
        except Exception as e:
            logger.exception(f"Error executing Neo4j query: {query}")
            return None, False, f"Error executing query: {str(e)}"
        finally:
            self.disconnect()