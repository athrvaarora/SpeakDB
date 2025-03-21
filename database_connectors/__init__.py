import importlib.util
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create connector cache to avoid redundant imports
_connector_cache = {}

def _import_connector(module_path, class_name):
    """
    Dynamically import a connector class from a module path
    
    Args:
        module_path (str): The module path (e.g., 'database_connectors.relational')
        class_name (str): The class name (e.g., 'PostgreSQLConnector')
        
    Returns:
        class or None: The connector class or None if import fails
    """
    # Check cache first
    cache_key = f"{module_path}.{class_name}"
    if cache_key in _connector_cache:
        return _connector_cache[cache_key]
    
    try:
        module = importlib.import_module(module_path)
        connector_class = getattr(module, class_name, None)
        _connector_cache[cache_key] = connector_class
        return connector_class
    except (ImportError, AttributeError) as e:
        logger.warning(f"Failed to import {class_name} from {module_path}: {str(e)}")
        return None

def get_connector(db_type, credentials):
    """
    Get the appropriate database connector based on the database type
    
    Args:
        db_type (str): The type of database
        credentials (dict): The credentials for connecting to the database
        
    Returns:
        object: An instance of the appropriate database connector
    """
    # Define mappings from database type to module path and class name
    connector_map = {
        # Relational databases
        'postgresql': ('database_connectors.relational', 'PostgreSQLConnector'),
        'mysql': ('database_connectors.relational', 'MySQLConnector'),
        'sqlserver': ('database_connectors.relational', 'SQLServerConnector'),
        'oracle': ('database_connectors.relational', 'OracleConnector'),
        'sqlite': ('database_connectors.relational', 'SQLiteConnector'),
        'redshift': ('database_connectors.relational', 'RedshiftConnector'),
        'cloudsql': ('database_connectors.relational', 'CloudSQLConnector'),
        'mariadb': ('database_connectors.relational', 'MariaDBConnector'),
        'db2': ('database_connectors.relational', 'DB2Connector'),
        
        # NoSQL databases
        'mongodb': ('database_connectors.nosql', 'MongoDBConnector'),
        'cassandra': ('database_connectors.nosql', 'CassandraConnector'),
        'redis': ('database_connectors.nosql', 'RedisConnector'),
        'elasticsearch': ('database_connectors.nosql', 'ElasticsearchConnector'),
        'dynamodb': ('database_connectors.nosql', 'DynamoDBConnector'),
        'couchbase': ('database_connectors.nosql', 'CouchbaseConnector'),
        'neo4j': ('database_connectors.nosql', 'Neo4jConnector'),
        
        # Data warehouse
        'snowflake': ('database_connectors.datawarehouse', 'SnowflakeConnector'),
        'bigquery': ('database_connectors.datawarehouse', 'BigQueryConnector'),
        'synapse': ('database_connectors.datawarehouse', 'SynapseConnector'),
        
        # Cloud databases
        'cosmosdb': ('database_connectors.cloud', 'CosmosDBConnector'),
        'firestore': ('database_connectors.cloud', 'FirestoreConnector'),
        'supabase': ('database_connectors.cloud', 'SupabaseConnector'),
        
        # Time-series databases
        'influxdb': ('database_connectors.timeseries', 'InfluxDBConnector'),
        'timescaledb': ('database_connectors.timescaledb', 'TimescaleDBConnector'),
        'kdb': ('database_connectors.kdb', 'KdbConnector')
    }
    
    if db_type not in connector_map:
        raise ValueError(f"Unsupported database type: {db_type}")
    
    module_path, class_name = connector_map[db_type]
    connector_class = _import_connector(module_path, class_name)
    
    if connector_class is None:
        raise ImportError(f"Failed to import {class_name} from {module_path}. The required dependency may not be installed.")
    
    return connector_class(credentials)

def test_connection(db_type, credentials):
    """
    Test the connection to a database
    
    Args:
        db_type (str): The type of database
        credentials (dict): The credentials for connecting to the database
        
    Returns:
        tuple: (success, message)
    """
    try:
        connector = get_connector(db_type, credentials)
        return connector.test_connection()
    except Exception as e:
        return False, f"Error connecting to {db_type}: {str(e)}"
