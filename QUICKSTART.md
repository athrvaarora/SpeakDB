# SpeakDB Quickstart Guide

This guide will help you quickly set up and start using SpeakDB.

## Prerequisites

1. Python 3.8 or higher installed
2. OpenAI API key (required for natural language processing)
3. Database credentials for any database you want to connect to

## Quick Setup

### 1. Get Your OpenAI API Key

If you don't already have an OpenAI API key:
1. Sign up/login at [OpenAI](https://platform.openai.com/)
2. Navigate to API keys section
3. Create a new API key
4. Copy the key for later use

### 2. Start the Application

#### Using the Executable (Windows)
1. Download the latest release from the releases page
2. Unzip the package
3. Run `SpeakDB.exe`
4. When prompted, enter your OpenAI API key

#### From Source Code
1. Clone the repository
2. Install dependencies (see DEPENDENCIES.md)
3. Set your OpenAI API key as an environment variable:
   ```bash
   # Windows
   set OPENAI_API_KEY=your_key_here
   
   # Linux/Mac
   export OPENAI_API_KEY=your_key_here
   ```
4. Start the application:
   ```bash
   # Development mode
   python main.py
   
   # Production mode
   gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
   ```
5. Open your browser and navigate to `http://localhost:5000`

### 3. Connect to a Database

1. From the home screen, select your database type
2. Enter the required connection details:
   - Host/Server name
   - Port
   - Username
   - Password
   - Database name
   - Any additional required credentials
3. Click "Connect" to establish the connection

### 4. Start Querying with Natural Language

Once connected, you'll be taken to the chat interface where you can:
1. Type your question in natural language
2. View the generated SQL query
3. See the results displayed in a table format
4. Visualize data using the visualization options
5. Export results to CSV or JSON formats

## Example Queries to Try

- "Show me all tables in this database"
- "List the first 10 users"
- "How many orders were placed in the last month?"
- "What's the average price of products in each category?"
- "Show me sales by region in descending order"

## Using the Schema Explorer

1. Click the "Schema Explorer" button in the chat interface
2. Browse through tables, collections, or other database objects
3. View field/column details including data types
4. Use this information to formulate more precise queries

## Troubleshooting

- **Connection Issues**: Double-check your database credentials and ensure the database is accessible from your network
- **Query Errors**: Examine the error message and adjust your natural language query to be more specific
- **Visualization Not Working**: Ensure your query returns data in a format suitable for visualization (e.g., numeric values for charts)

For more detailed information, please refer to the full documentation in README.md.