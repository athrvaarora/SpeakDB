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
                # Check if direct connection string is provided
                if self.credentials.get("connection_string"):
                    logger.info("Using provided connection string")
                    self.connection = psycopg2.connect(self.credentials.get("connection_string"))
                    self.engine = create_engine(self.credentials.get("connection_string"))
                # Check if individual credentials are provided
                elif all(self.credentials.get(key) for key in ["host", "username", "password", "db_name"]):
                    logger.info("Using individual credentials")
                    self.connection = psycopg2.connect(
                        host=self.credentials.get("host"),
                        port=self.credentials.get("port", 5432),
                        user=self.credentials.get("username"),
                        password=self.credentials.get("password"),
                        dbname=self.credentials.get("db_name")
                    )
                    
                    # Create SQLAlchemy engine for schema inspection
                    conn_string = f"postgresql://{self.credentials.get('username')}:{self.credentials.get('password')}@{self.credentials.get('host')}:{self.credentials.get('port', 5432)}/{self.credentials.get('db_name')}"
                    self.engine = create_engine(conn_string)
                # Fall back to environment variables if available
                elif os.environ.get("DATABASE_URL"):
                    logger.info("Using DATABASE_URL from environment variables")
                    self.connection = psycopg2.connect(os.environ["DATABASE_URL"])
                    self.engine = create_engine(os.environ["DATABASE_URL"])
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
                if self.credentials.get("connection_string"):
                    logger.info("Using provided connection string")
                    # Using SQLAlchemy for both connection and schema inspection
                    self.engine = create_engine(self.credentials.get("connection_string"))
                    self.connection = self.engine.connect().connection
                # Check if individual credentials are provided
                elif all(self.credentials.get(key) for key in ["host", "username", "password", "db_name"]):
                    logger.info("Using individual credentials")
                    self.connection = mysql.connector.connect(
                        host=self.credentials.get("host"),
                        user=self.credentials.get("username"),
                        password=self.credentials.get("password"),
                        database=self.credentials.get("db_name")
                    )
                    
                    # Create SQLAlchemy engine for schema inspection
                    conn_string = f"mysql+mysqlconnector://{self.credentials.get('username')}:{self.credentials.get('password')}@{self.credentials.get('host')}/{self.credentials.get('db_name')}"
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
                self.connection = sqlite3.connect(self.credentials.get("file_path"))
                
                # Create SQLAlchemy engine for schema inspection
                conn_string = f"sqlite:///{self.credentials.get('file_path')}"
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
