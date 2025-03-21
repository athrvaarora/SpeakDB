# Project Dependencies

The following packages are required for SpeakDB to function properly:

## Core Dependencies
- flask
- flask-sqlalchemy
- gunicorn
- openai
- psycopg2-binary
- sqlalchemy
- pytz
- email-validator

## Database Connector Dependencies

### Relational Databases
- mysql-connector-python
- pyodbc
- cx-Oracle

### NoSQL Databases
- pymongo
- redis
- cassandra-driver
- elasticsearch
- couchbase

### Graph Databases
- neo4j
- pyTigerGraph

### Time-Series Databases
- influxdb-client

### Data Warehouse
- snowflake-connector-python

### Cloud Services
- boto3 (AWS/DynamoDB)
- firebase-admin
- supabase

## Utility Dependencies
- python-dateutil
- cryptography
- Pillow

## Build Dependencies
- pyinstaller (for creating executable)

## Installation

For development or running from source, you can install these packages using pip:

```bash
# Install using the packager tool in the Replit environment
# or on your local machine:
pip install flask flask-sqlalchemy gunicorn openai psycopg2-binary sqlalchemy pytz email-validator
```

For production use with the executable, these dependencies are bundled with the application.