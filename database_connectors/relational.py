import logging
import json
import os
import sqlite3

# Import database libraries with try/except to handle missing dependencies
try:
    import psycopg2
except ImportError:
    psycopg2 = None

try:
    import mysql.connector
except ImportError:
    mysql = type('mysql', (), {'connector': None})

try:
    import pyodbc
except ImportError:
    pyodbc = None

try:
    import cx_Oracle
except ImportError:
    cx_Oracle = None

try:
    import boto3
except ImportError:
    boto3 = None

try:
    import sqlalchemy
    from sqlalchemy import create_engine, inspect
except ImportError:
    sqlalchemy = None

try:
    import ibm_db
except ImportError:
    ibm_db = None

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class BaseRelationalConnector:
    """Base class for relational database connectors"""
    
    def __init__(self, credentials):
        self.credentials = credentials
        self.connection = None
        self.engine = None
    
    def connect(self):
        """Connect to the database"""
        raise NotImplementedError("Subclasses must implement connect()")
    
    def disconnect(self):
        """Disconnect from the database"""
        if self.connection:
            try:
                self.connection.close()
            except Exception as e:
                logger.error(f"Error disconnecting: {str(e)}")
            finally:
                self.connection = None
    
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
        try:
            self.connect()
            
            # For SQLAlchemy-compatible connectors
            if self.engine:
                inspector = inspect(self.engine)
                schema_info = {
                    "tables": []
                }
                
                for table_name in inspector.get_table_names():
                    table_info = {
                        "name": table_name,
                        "columns": []
                    }
                    
                    for column in inspector.get_columns(table_name):
                        column_info = {
                            "name": column["name"],
                            "type": str(column["type"]),
                            "nullable": column.get("nullable", True)
                        }
                        table_info["columns"].append(column_info)
                    
                    schema_info["tables"].append(table_info)
                
                return schema_info
            else:
                # Fallback for non-SQLAlchemy connectors
                return {"error": "Schema retrieval not implemented for this connector"}
                
        except Exception as e:
            logger.exception("Error getting schema")
            return {"error": f"Error getting schema: {str(e)}"}
        finally:
            self.disconnect()
    
    def execute_query(self, query):
        """
        Execute a query against the database
        
        Args:
            query (str): The query to execute
            
        Returns:
            tuple: (result, success, error_message)
        """
        try:
            self.connect()
            
            cursor = self.connection.cursor()
            cursor.execute(query)
            
            # Check if the query is a SELECT query
            if query.strip().upper().startswith("SELECT"):
                columns = [col[0] for col in cursor.description]
                results = []
                
                for row in cursor.fetchall():
                    results.append(dict(zip(columns, row)))
                
                return results, True, None
            else:
                # For non-SELECT queries
                affected_rows = cursor.rowcount
                self.connection.commit()
                return {"affected_rows": affected_rows}, True, None
                
        except Exception as e:
            logger.exception(f"Error executing query: {query}")
            return None, False, f"Error executing query: {str(e)}"
        finally:
            self.disconnect()

class PostgreSQLConnector(BaseRelationalConnector):
    """Connector for PostgreSQL databases"""
    
    def connect(self):
        """Connect to a PostgreSQL database"""
        if not self.connection:
            try:
                # Check if direct connection string is provided in credentials or environment
                connection_string = self.credentials.get("connection_string") or os.environ.get("DATABASE_URL")
                
                if connection_string:
                    logger.info("Using connection string")
                    if os.environ.get("DATABASE_URL") and not self.credentials.get("connection_string"):
                        logger.info("Using DATABASE_URL environment variable")
                    self.connection = psycopg2.connect(connection_string)
                    self.engine = create_engine(connection_string)
                # Check if individual credentials are provided in dictionary or environment
                else:
                    # Get credentials from credentials dict or environment variables
                    host = self.credentials.get("host") or os.environ.get("PGHOST")
                    port = self.credentials.get("port") or os.environ.get("PGPORT", "5432")
                    username = self.credentials.get("username") or os.environ.get("PGUSER")
                    password = self.credentials.get("password") or os.environ.get("PGPASSWORD")
                    db_name = self.credentials.get("db_name") or os.environ.get("PGDATABASE")
                    
                    # Log if using environment variables
                    if os.environ.get("PGHOST") and not self.credentials.get("host"):
                        logger.info("Using PGHOST environment variable")
                    if os.environ.get("PGPORT") and not self.credentials.get("port"):
                        logger.info("Using PGPORT environment variable")
                    if os.environ.get("PGUSER") and not self.credentials.get("username"):
                        logger.info("Using PGUSER environment variable")
                    if os.environ.get("PGPASSWORD") and not self.credentials.get("password"):
                        logger.info("Using PGPASSWORD environment variable")
                    if os.environ.get("PGDATABASE") and not self.credentials.get("db_name"):
                        logger.info("Using PGDATABASE environment variable")
                    
                    # Check if required credentials are available
                    if host and username and password and db_name:
                        logger.info("Using individual credentials")
                        
                        # Convert port to integer if it's a string
                        if isinstance(port, str):
                            port = int(port)
                        
                        self.connection = psycopg2.connect(
                            host=host,
                            port=port,
                            user=username,
                            password=password,
                            dbname=db_name
                        )
                        
                        # Create SQLAlchemy engine for schema inspection
                        conn_string = f"postgresql://{username}:{password}@{host}:{port}/{db_name}"
                        self.engine = create_engine(conn_string)
                    else:
                        raise ValueError("Missing required PostgreSQL credentials")

                else:
                    logger.error("No valid PostgreSQL credentials provided")
                    raise Exception("No valid PostgreSQL credentials provided")
                
            except Exception as e:
                logger.exception("Error connecting to PostgreSQL")
                raise Exception(f"Error connecting to PostgreSQL: {str(e)}")

class MySQLConnector(BaseRelationalConnector):
    """Connector for MySQL databases"""
    
    def connect(self):
        """Connect to a MySQL database"""
        if not self.connection:
            try:
                # Check if direct connection string is provided
                connection_string = self.credentials.get("connection_string") or os.environ.get("MYSQL_URL")
                
                if connection_string:
                    logger.info("Using connection string")
                    if os.environ.get("MYSQL_URL") and not self.credentials.get("connection_string"):
                        logger.info("Using MYSQL_URL environment variable")
                    # Using SQLAlchemy for both connection and schema inspection
                    self.engine = create_engine(connection_string)
                    self.connection = self.engine.connect().connection
                else:
                    # Get credentials from credentials dict or environment variables
                    host = self.credentials.get("host") or os.environ.get("MYSQL_HOST")
                    port = self.credentials.get("port") or os.environ.get("MYSQL_PORT", "3306")
                    username = self.credentials.get("username") or os.environ.get("MYSQL_USER") 
                    password = self.credentials.get("password") or os.environ.get("MYSQL_PASSWORD")
                    db_name = self.credentials.get("db_name") or os.environ.get("MYSQL_DATABASE")
                    
                    # Log if using environment variables
                    if os.environ.get("MYSQL_HOST") and not self.credentials.get("host"):
                        logger.info("Using MYSQL_HOST environment variable")
                    if os.environ.get("MYSQL_PORT") and not self.credentials.get("port"):
                        logger.info("Using MYSQL_PORT environment variable")
                    if os.environ.get("MYSQL_USER") and not self.credentials.get("username"):
                        logger.info("Using MYSQL_USER environment variable")
                    if os.environ.get("MYSQL_PASSWORD") and not self.credentials.get("password"):
                        logger.info("Using MYSQL_PASSWORD environment variable")
                    if os.environ.get("MYSQL_DATABASE") and not self.credentials.get("db_name"):
                        logger.info("Using MYSQL_DATABASE environment variable")
                    
                    # Check if required credentials are available
                    if host and username and password and db_name:
                        logger.info("Using individual MySQL credentials")
                        
                        # Convert port to integer if it's a string
                        if isinstance(port, str):
                            port = int(port)
                            
                        self.connection = mysql.connector.connect(
                            host=host,
                            port=port,
                            user=username,
                            password=password,
                            database=db_name
                        )
                        
                        # Create SQLAlchemy engine for schema inspection
                        conn_string = f"mysql+mysqlconnector://{username}:{password}@{host}:{port}/{db_name}"
                        self.engine = create_engine(conn_string)
                    else:
                        logger.error("No valid MySQL credentials provided")
                        raise Exception("No valid MySQL credentials provided")
                
            except Exception as e:
                logger.exception("Error connecting to MySQL")
                raise Exception(f"Error connecting to MySQL: {str(e)}")

class SQLServerConnector(BaseRelationalConnector):
    """Connector for SQL Server databases"""
    
    def connect(self):
        """Connect to a SQL Server database"""
        if not self.connection:
            try:
                connection_string = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={self.credentials.get('host')}\\{self.credentials.get('instance')};UID={self.credentials.get('username')};PWD={self.credentials.get('password')}"
                self.connection = pyodbc.connect(connection_string)
                
                # Create SQLAlchemy engine for schema inspection
                conn_string = f"mssql+pyodbc://{self.credentials.get('username')}:{self.credentials.get('password')}@{self.credentials.get('host')}\\{self.credentials.get('instance')}?driver=ODBC+Driver+17+for+SQL+Server"
                self.engine = create_engine(conn_string)
                
            except Exception as e:
                logger.exception("Error connecting to SQL Server")
                raise Exception(f"Error connecting to SQL Server: {str(e)}")

class OracleConnector(BaseRelationalConnector):
    """Connector for Oracle databases"""
    
    def connect(self):
        """Connect to an Oracle database"""
        if not self.connection:
            try:
                dsn = cx_Oracle.makedsn(
                    self.credentials.get("host"),
                    self.credentials.get("port", 1521),
                    service_name=self.credentials.get("service_name")
                )
                self.connection = cx_Oracle.connect(
                    user=self.credentials.get("username"),
                    password=self.credentials.get("password"),
                    dsn=dsn
                )
                
                # Create SQLAlchemy engine for schema inspection
                conn_string = f"oracle+cx_oracle://{self.credentials.get('username')}:{self.credentials.get('password')}@{dsn}"
                self.engine = create_engine(conn_string)
                
            except Exception as e:
                logger.exception("Error connecting to Oracle")
                raise Exception(f"Error connecting to Oracle: {str(e)}")

class SQLiteConnector(BaseRelationalConnector):
    """Connector for SQLite databases"""
    
    def connect(self):
        """Connect to a SQLite database"""
        if not self.connection:
            try:
                # Get database path from credentials dict or environment variables
                db_path = self.credentials.get("file_path") or os.environ.get("SQLITE_DB_PATH")
                
                # Log if using environment variables
                if os.environ.get("SQLITE_DB_PATH") and not self.credentials.get("file_path"):
                    logger.info("Using SQLITE_DB_PATH environment variable")
                
                # Check if we have a database path
                if not db_path:
                    # Try default data directory path as a last resort
                    if os.path.exists("data"):
                        for file in os.listdir("data"):
                            if file.endswith(".db"):
                                db_path = os.path.join("data", file)
                                logger.info(f"Found SQLite database in data directory: {db_path}")
                                break
                
                if not db_path:
                    logger.error("No SQLite database path provided")
                    raise Exception("No SQLite database path provided")
                
                logger.info(f"Connecting to SQLite database at: {db_path}")
                self.connection = sqlite3.connect(db_path)
                
                # Create SQLAlchemy engine for schema inspection
                conn_string = f"sqlite:///{db_path}"
                self.engine = create_engine(conn_string)
                
            except Exception as e:
                logger.exception("Error connecting to SQLite")
                raise Exception(f"Error connecting to SQLite: {str(e)}")

class RedshiftConnector(BaseRelationalConnector):
    """Connector for Amazon Redshift databases"""
    
    def connect(self):
        """Connect to an Amazon Redshift database"""
        if not self.connection:
            try:
                # Setup connection using psycopg2
                self.connection = psycopg2.connect(
                    dbname=self.credentials.get("db_name"),
                    user=self.credentials.get("username"),
                    password=self.credentials.get("password"),
                    host=f"{self.credentials.get('cluster_id')}.{self.credentials.get('region')}.redshift.amazonaws.com",
                    port=5439
                )
                
                # Create SQLAlchemy engine for schema inspection
                conn_string = f"redshift+psycopg2://{self.credentials.get('username')}:{self.credentials.get('password')}@{self.credentials.get('cluster_id')}.{self.credentials.get('region')}.redshift.amazonaws.com:5439/{self.credentials.get('db_name')}"
                self.engine = create_engine(conn_string)
                
            except Exception as e:
                logger.exception("Error connecting to Redshift")
                raise Exception(f"Error connecting to Redshift: {str(e)}")

class CloudSQLConnector(BaseRelationalConnector):
    """Connector for Google Cloud SQL databases"""
    
    def connect(self):
        """Connect to a Google Cloud SQL database"""
        if not self.connection:
            try:
                # Assuming MySQL is being used on Google Cloud SQL
                self.connection = mysql.connector.connect(
                    host=f"{self.credentials.get('project_id')}:{self.credentials.get('region')}:{self.credentials.get('instance')}",
                    user=self.credentials.get("username"),
                    password=self.credentials.get("password")
                )
                
                # Create SQLAlchemy engine for schema inspection
                conn_string = f"mysql+mysqlconnector://{self.credentials.get('username')}:{self.credentials.get('password')}@{self.credentials.get('project_id')}:{self.credentials.get('region')}:{self.credentials.get('instance')}"
                self.engine = create_engine(conn_string)
                
            except Exception as e:
                logger.exception("Error connecting to Google Cloud SQL")
                raise Exception(f"Error connecting to Google Cloud SQL: {str(e)}")

class MariaDBConnector(BaseRelationalConnector):
    """Connector for MariaDB databases (using MySQL connector)"""
    
    def connect(self):
        """Connect to a MariaDB database"""
        if not self.connection:
            try:
                self.connection = mysql.connector.connect(
                    host=self.credentials.get("host"),
                    user=self.credentials.get("username"),
                    password=self.credentials.get("password"),
                    database=self.credentials.get("db_name")
                )
                
                # Create SQLAlchemy engine for schema inspection
                conn_string = f"mysql+mysqlconnector://{self.credentials.get('username')}:{self.credentials.get('password')}@{self.credentials.get('host')}/{self.credentials.get('db_name')}"
                self.engine = create_engine(conn_string)
                
            except Exception as e:
                logger.exception("Error connecting to MariaDB")
                raise Exception(f"Error connecting to MariaDB: {str(e)}")

class DB2Connector(BaseRelationalConnector):
    """Connector for IBM Db2 databases"""
    
    def connect(self):
        """Connect to an IBM Db2 database"""
        if not self.connection:
            try:
                conn_string = f"DATABASE={self.credentials.get('db_name')};HOSTNAME={self.credentials.get('host')};PORT={self.credentials.get('port', 50000)};PROTOCOL=TCPIP;UID={self.credentials.get('username')};PWD={self.credentials.get('password')};"
                self.connection = ibm_db.connect(conn_string, "", "")
                
                # Create SQLAlchemy engine for schema inspection
                sqlalchemy_conn_string = f"db2+ibm_db://{self.credentials.get('username')}:{self.credentials.get('password')}@{self.credentials.get('host')}:{self.credentials.get('port', 50000)}/{self.credentials.get('db_name')}"
                self.engine = create_engine(sqlalchemy_conn_string)
                
            except Exception as e:
                logger.exception("Error connecting to IBM Db2")
                raise Exception(f"Error connecting to IBM Db2: {str(e)}")
