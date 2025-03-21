# SpeakDB: Natural Language Database Interface

![SpeakDB Logo](static/images/speakdb-logo.svg)

SpeakDB is a cross-platform application that transforms database querying through AI-powered natural language processing, enabling intuitive and intelligent database interactions across multiple database systems.

## Features

- **Natural Language Queries**: Ask questions in plain English and get database results
- **Multi-database Support**: Connect to 30+ database types including:
  - Relational: PostgreSQL, MySQL, SQL Server, Oracle, SQLite, MariaDB, DB2
  - NoSQL: MongoDB, Cassandra, Redis, Elasticsearch, DynamoDB, Couchbase
  - Graph: Neo4j, TigerGraph
  - Time-series: InfluxDB, TimescaleDB, Prometheus
  - Data Warehouse: Snowflake, BigQuery, Synapse, Redshift
  - Cloud: Azure Cosmos DB, Firestore, Supabase
- **Intelligent Schema Analysis**: AI automatically analyzes your database structure to improve query accuracy
- **Data Visualization**: Visualize query results with charts (bar, line, pie, scatter)
- **Export Options**: Export results to CSV or JSON formats
- **Schema Explorer**: Browse your database structure in an intuitive interface

## Requirements

- Python 3.8+
- PostgreSQL (optional - for storing chat history)
- OpenAI API key

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/speakdb.git
cd speakdb
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
# For OpenAI API
export OPENAI_API_KEY=your_openai_api_key

# For PostgreSQL (optional)
export DATABASE_URL=postgresql://username:password@localhost:5432/speakdb
```

## Building

To build the executable for Windows:
```bash
pyinstaller --onefile --windowed --icon=static/images/speakdb-icon.ico --add-data "templates;templates" --add-data "static;static" main.py
```

The executable will be available in the `dist` directory.

## Running the Application

### Development Mode

```bash
# Start the Flask development server
python main.py
```

### Production Mode

```bash
# Start with Gunicorn (recommended for production)
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
```

Then open your browser and navigate to `http://localhost:5000`

## Usage

1. **Select Database Type**: Choose from the available database types
2. **Enter Connection Details**: Provide the required credentials for your database
3. **Chat Interface**: Ask questions about your data in natural language
4. **Explore Results**: View query results, visualize data, and export as needed

## Example Queries

- "Show me all tables in this database"
- "How many users have signed up in the last 30 days?"
- "What are the top 5 products by revenue?"
- "Find customers who haven't made a purchase in the last 6 months"
- "Show me the monthly sales trends for the past year"

## Architecture

- **Frontend**: HTML, CSS, JavaScript with Bootstrap for styling
- **Backend**: Python/Flask for API and server-side logic
- **AI Engine**: OpenAI GPT for query generation and schema analysis
- **Database Connectors**: Specialized connectors for each database type
- **Visualization**: Chart.js for data visualization

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- OpenAI for GPT APIs
- Chart.js for visualization capabilities
- Bootstrap for UI components