# SpeakDB: AI-Powered Natural Language Database Interface

<div align="center">
  <img src="static/images/speakdb-logo.svg" alt="SpeakDB Logo" width="180" />
  <h3>Speak to your database like a human.</h3>
  <p>Revolutionizing database access through natural language.</p>
</div>

<p align="center">
  <a href="#key-features">Key Features</a> •
  <a href="#supported-databases">Supported Databases</a> •
  <a href="#requirements">Requirements</a> •
  <a href="#installation">Installation</a> •
  <a href="#usage">Usage</a> •
  <a href="#building">Building</a> •
  <a href="#architecture">Architecture</a>
</p>

---

SpeakDB is a revolutionary cross-platform application that transforms database querying through advanced AI-powered natural language processing. It enables intuitive and intelligent database interactions across multiple database systems without requiring knowledge of SQL or specialized query languages.

<img src="static/images/speakdb-hero.svg" alt="SpeakDB Hero" width="100%" />

## Key Features

- **💬 Natural Language Queries**: Ask questions in plain English and receive accurate database results.
  
- **🔄 Multi-database Support**: Seamlessly connect to 30+ database types with a unified interface.
  
- **🧠 AI-Powered Schema Intelligence**: Automatic analysis of your database structure to improve query accuracy and provide context-aware responses.
  
- **📊 Intelligent Data Visualization**: Automatically visualize query results with the most appropriate chart types (bar, line, pie, scatter).
  
- **📤 Advanced Export Options**: Export results to CSV or JSON formats with a single click.
  
- **🔍 Interactive Schema Explorer**: Browse and understand your database structure through an intuitive visual interface.

- **📱 Responsive UI**: Modern, user-friendly interface that works across devices.

- **🔐 Secure Credential Management**: End-to-end encryption for database credentials with no persistent storage of database contents.

- **🧩 Query History & Management**: Save, organize, and reuse queries for quick access to common data requests.

## Supported Databases

SpeakDB provides seamless connectivity to over 30 database systems across multiple categories:

<table>
  <tr>
    <td width="33%">
      <h4>🔶 Relational</h4>
      <ul>
        <li>PostgreSQL</li>
        <li>MySQL</li>
        <li>SQL Server</li>
        <li>Oracle</li>
        <li>SQLite</li>
        <li>MariaDB</li>
        <li>DB2</li>
      </ul>
    </td>
    <td width="33%">
      <h4>🔷 NoSQL</h4>
      <ul>
        <li>MongoDB</li>
        <li>Cassandra</li>
        <li>Redis</li>
        <li>Elasticsearch</li>
        <li>DynamoDB</li>
        <li>Couchbase</li>
      </ul>
    </td>
    <td width="33%">
      <h4>🔶 Graph</h4>
      <ul>
        <li>Neo4j</li>
        <li>TigerGraph</li>
      </ul>
    </td>
  </tr>
  <tr>
    <td width="33%">
      <h4>🔷 Time-series</h4>
      <ul>
        <li>InfluxDB</li>
        <li>TimescaleDB</li>
        <li>Prometheus</li>
        <li>KDB+</li>
      </ul>
    </td>
    <td width="33%">
      <h4>🔶 Data Warehouse</h4>
      <ul>
        <li>Snowflake</li>
        <li>BigQuery</li>
        <li>Redshift</li>
        <li>Azure Synapse</li>
      </ul>
    </td>
    <td width="33%">
      <h4>🔷 Cloud Native</h4>
      <ul>
        <li>Azure Cosmos DB</li>
        <li>Firestore</li>
        <li>Supabase</li>
        <li>Neon</li>
        <li>Crunchy Bridge</li>
      </ul>
    </td>
  </tr>
</table>

## Requirements

<table>
  <tr>
    <td width="50%" valign="top">
      <h4>🛠️ Core Requirements</h4>
      <ul>
        <li>Python 3.8+</li>
        <li>Flask and related dependencies</li>
        <li>PostgreSQL (for user accounts & chat history)</li>
        <li>OpenAI API key</li>
      </ul>
    </td>
    <td width="50%" valign="top">
      <h4>🔌 Optional Requirements</h4>
      <ul>
        <li>Database client libraries (based on databases you connect to)</li>
        <li>CUDA support for improved performance</li>
        <li>Windows, macOS, or Linux operating system</li>
      </ul>
    </td>
  </tr>
</table>

## Installation

### Quick Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/speakdb.git
   cd speakdb
   ```

2. **Create and activate a virtual environment (recommended):**
   ```bash
   # On Windows
   python -m venv venv
   venv\Scripts\activate
   
   # On macOS/Linux
   python -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   ```bash
   # For OpenAI API (required)
   export OPENAI_API_KEY=your_openai_api_key
   
   # For PostgreSQL database (optional but recommended)
   export DATABASE_URL=postgresql://username:password@localhost:5432/speakdb
   ```

### Docker Installation

For containerized deployment:

```bash
# Build the Docker image
docker build -t speakdb .

# Run the container
docker run -p 5000:5000 \
  -e OPENAI_API_KEY=your_openai_api_key \
  -e DATABASE_URL=postgresql://username:password@host:5432/speakdb \
  speakdb
```

## Running SpeakDB

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

## Building Executable

### Windows Executable

To build a standalone Windows executable:

```bash
pyinstaller --onefile --windowed --icon=static/images/speakdb-icon.ico --add-data "templates;templates" --add-data "static;static" main.py
```

The executable will be available in the `dist` directory.

### macOS Application

To build a macOS application bundle:

```bash
pyinstaller --windowed --icon=static/images/speakdb-icon.icns --add-data "templates:templates" --add-data "static:static" main.py
```

## Usage Guide

<table>
  <tr>
    <td width="50%" valign="top">
      <h4>🚀 Getting Started</h4>
      <ol>
        <li><b>Create an account</b> or continue as guest</li>
        <li><b>Select your database type</b> from over 30 supported systems</li>
        <li><b>Provide connection credentials</b> (securely encrypted)</li>
        <li><b>Start chatting</b> with your database in natural language</li>
      </ol>
    </td>
    <td width="50%" valign="top">
      <h4>💡 Advanced Features</h4>
      <ul>
        <li>Use the <b>Schema Explorer</b> to browse your database structure</li>
        <li>Switch between <b>different visualizations</b> of your data</li>
        <li><b>Export results</b> in CSV or JSON formats</li>
        <li>Save and <b>revisit previous chat sessions</b></li>
      </ul>
    </td>
  </tr>
</table>

## Example Queries

SpeakDB supports a wide range of natural language queries across all supported database types. Here are some examples:

### Data Exploration
- "Show me all tables in this database"
- "What columns are in the customers table?"
- "What are the primary keys for each table?"

### Business Intelligence
- "How many users have signed up in the last 30 days?"
- "What are the top 5 products by revenue?"
- "Show me the monthly sales trends for the past year"
- "What's the average order value by customer segment?"

### Customer Analysis
- "Find customers who haven't made a purchase in the last 6 months"
- "Which customers have spent more than $1000 in total?"
- "What's the customer retention rate over time?"

### Complex Operations
- "Join products and categories and show me the best-selling category"
- "Calculate the moving average of daily sales for the last 30 days"
- "Find anomalies in transaction data from the past week"

## Architecture

SpeakDB employs a modern, scalable architecture designed for performance and flexibility:

<div align="center">
  <table>
    <tr>
      <td align="center"><b>🎨 Frontend</b></td>
      <td align="center"><b>⚙️ Backend</b></td>
      <td align="center"><b>🧠 AI Engine</b></td>
      <td align="center"><b>🔌 Connectors</b></td>
    </tr>
    <tr>
      <td>
        • HTML5/CSS3<br>
        • JavaScript<br>
        • Bootstrap 5<br>
        • Chart.js<br>
        • D3.js
      </td>
      <td>
        • Python 3.8+<br>
        • Flask<br>
        • SQLAlchemy<br>
        • PostgreSQL<br>
        • Gunicorn
      </td>
      <td>
        • OpenAI GPT-4<br>
        • NLP Processing<br>
        • Schema Analysis<br>
        • Query Generation<br>
        • Result Formatting
      </td>
      <td>
        • SQL Adapters<br>
        • NoSQL Clients<br>
        • Graph DB APIs<br>
        • Cloud Services<br>
        • Time-series Engines
      </td>
    </tr>
  </table>
</div>

## Security

SpeakDB takes security seriously:

- **Credential Encryption**: All database credentials are encrypted in transit and at rest
- **No Data Storage**: Database content is never persistently stored in SpeakDB
- **Access Controls**: User authentication and permission management for enterprise deployments
- **Audit Logging**: Comprehensive logging of operations for compliance requirements
- **Sanitized Inputs**: Protection against injection attacks and other security vulnerabilities

## Contributing

We welcome contributions to SpeakDB! Here's how you can help:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Commit your changes**: `git commit -m 'Add some amazing feature'`
4. **Push to the branch**: `git push origin feature/amazing-feature`
5. **Open a Pull Request**

See our [Contributing Guidelines](CONTRIBUTING.md) for more details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **OpenAI** for the powerful GPT API that makes natural language understanding possible
- **PostgreSQL** for the reliable database backend
- **Chart.js and D3.js** for the visualization capabilities
- **Bootstrap** for the responsive UI components
- **All contributors** who have helped make SpeakDB better

---

<div align="center">
  <p>SpeakDB - Making data speak your language.</p>
  <p>
    <a href="https://github.com/yourusername/speakdb/issues">Report Bug</a> •
    <a href="https://github.com/yourusername/speakdb/issues">Request Feature</a>
  </p>
</div>