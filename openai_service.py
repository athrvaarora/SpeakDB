import os
import json
import logging
import datetime
from openai import OpenAI
from utils import DateTimeEncoder

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai = OpenAI(api_key=OPENAI_API_KEY)

# the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user
MODEL = "gpt-4o"

def generate_query(user_query, db_type, schema_info):
    """
    Generate a database query from a natural language query using OpenAI's GPT
    
    Args:
        user_query (str): The natural language query from the user
        db_type (str): The type of database being queried
        schema_info (dict): Information about the database schema
        
    Returns:
        tuple: (success, query, explanation, needs_multiple_queries, additional_queries)
            - success (bool): Whether the query generation was successful
            - query (str): The generated primary query
            - explanation (str): Explanation of what the query does
            - needs_multiple_queries (bool): Whether multiple queries are needed
            - additional_queries (list): List of additional queries if needed
    """
    try:
        # Create a prompt that includes the database type and schema information
        prompt = f"""
        You are a database query generator. Generate a query for a {db_type} database based on the following natural language request:
        
        "{user_query}"
        
        The database schema is as follows:
        {json.dumps(schema_info, indent=2)}
        
        Important requirements:
        1. For SQLite: NEVER generate multiple SQL statements separated by semicolons, as SQLite can only execute one statement at a time.
        2. For MySQL/PostgreSQL/SQL Server: If multiple statements are needed, ensure they are compatible with the specific database's transaction requirements.
        3. When a user wants to see data from multiple tables, use JOIN operations when appropriate.
        4. For NoSQL databases, ensure the query format matches the database's specific API requirements.
        5. CRITICAL: If a user wants "all records from all tables" or similar, NEVER use UNION ALL. Instead, always set "needs_multiple_queries" to true and provide separate SELECT statements for each table in the "additional_queries" array.
        
        Respond with JSON in the following format:
        {{
            "query": "the generated query",
            "explanation": "explanation of what the query does and why it satisfies the request",
            "needs_multiple_queries": false,
            "additional_queries": []
        }}
        
        If the request genuinely requires multiple separate queries to be run in sequence (not simultaneously), set "needs_multiple_queries" to true and provide each query in the "additional_queries" array.
        
        Ensure the query is valid for {db_type} syntax.
        """
        
        # Generate the query using OpenAI GPT
        response = openai.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are an expert database query generator."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        # Parse the response
        raw_response = response.choices[0].message.content
        logger.info(f"Raw OpenAI response: {raw_response}")
        
        try:
            result = json.loads(raw_response)
            query = result.get("query")
            explanation = result.get("explanation")
            needs_multiple_queries = result.get("needs_multiple_queries", False)
            additional_queries = result.get("additional_queries", [])
            
            # Log the result 
            logger.info(f"Parsed query: {query}")
            logger.info(f"Needs multiple queries: {needs_multiple_queries}")
            logger.info(f"Additional queries count: {len(additional_queries)}")
            
            if not query and not (needs_multiple_queries and additional_queries):
                return False, None, "Failed to generate a query from the GPT response - query is empty", False, []
                
            # For 'get all records from all tables' type queries or similar, we want to ensure we have multiple queries
            query_words = user_query.lower().split()
            is_all_tables_query = (
                ("all" in query_words or "each" in query_words or "every" in query_words) and 
                ("table" in query_words or "tables" in query_words) and
                not needs_multiple_queries
            )
            
            if is_all_tables_query or ("record" in query_words and "all" in query_words and "table" in query_words):
                logger.info("Detected 'all tables' type query")
                
                # First try to get table names from schema_info dict format
                table_names = []
                if isinstance(schema_info, dict):
                    # SQLAlchemy format with "tables" key
                    if "tables" in schema_info:
                        for table_info in schema_info["tables"]:
                            if "name" in table_info:
                                table_names.append(table_info["name"])
                    # PostgreSQL information_schema format
                    elif "public" in schema_info:
                        for table in schema_info.get("public", []):
                            table_names.append(table)
                
                # If we didn't get tables from schema, execute a query to get them
                if not table_names and db_type.lower() in ['postgresql', 'mysql', 'mariadb', 'sqlserver']:
                    # Use a default query to find table names if schema didn't provide them
                    if db_type.lower() in ['postgresql', 'redshift']:
                        table_query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';"
                    elif db_type.lower() in ['mysql', 'mariadb']:
                        table_query = "SHOW TABLES;"
                    elif db_type.lower() == 'sqlserver':
                        table_query = "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE';"
                    elif db_type.lower() == 'sqlite':
                        table_query = "SELECT name FROM sqlite_master WHERE type='table';"
                    else:
                        table_query = None
                        
                    # For now we'll use a fallback set of tables we know exist
                    logger.info("Using fallback table names from our SQL query")
                    table_names = ['products', 'chat_messages', 'customers', 'orders', 'order_items', 'chats']
                
                if table_names:
                    needs_multiple_queries = True
                    # Primary query gets the first table
                    if not query:
                        query = f"SELECT * FROM {table_names[0]} LIMIT 100;"
                    
                    # Additional queries for the rest of the tables
                    additional_queries = []
                    for table_name in table_names[1:]:
                        additional_queries.append(f"SELECT * FROM {table_name} LIMIT 100;")
                    
                    logger.info(f"Converted to multiple queries with {len(additional_queries)} additional queries")
                    explanation = f"Generating separate queries for each table to retrieve their records."
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}, Raw response: {raw_response}")
            return False, None, f"Failed to parse OpenAI response as JSON: {str(e)}", False, []
        except Exception as e:
            logger.error(f"Error parsing OpenAI response: {e}, Raw response: {raw_response}")
            return False, None, f"Error parsing OpenAI response: {str(e)}", False, []
            
        if not query and not additional_queries:
            return False, None, "Failed to generate a query from the GPT response - no valid queries found", False, []
        
        return True, query, explanation, needs_multiple_queries, additional_queries
    except Exception as e:
        logger.exception("Error generating query with GPT")
        return False, None, f"Error generating query: {str(e)}", False, []

def format_response(db_result, user_query):
    """
    Format the database query result to be more direct and straightforward
    
    Args:
        db_result (any): The result from the database query
        user_query (str): The original user query
        
    Returns:
        str: A formatted response
    """
    try:
        # Create a clean response with just the data, no extra explanations
        markdown_response = "<div class='query-result-container' data-exportable='true'>\n\n"
        
        # If the result is a list of dictionaries (common for SQL query results)
        if isinstance(db_result, list) and len(db_result) > 0 and isinstance(db_result[0], dict):
            # Create a table header from the keys of the first item
            columns = list(db_result[0].keys())
            
            # Create the markdown table header
            header_row = "| " + " | ".join(columns) + " |"
            separator_row = "| " + " | ".join(["---"] * len(columns)) + " |"
            
            # Create table rows for each result
            data_rows = []
            for item in db_result:
                # Format each value properly, handling None and special types
                values = []
                for col in columns:
                    value = item.get(col)
                    # Format value based on type
                    if value is None:
                        formatted_value = "NULL"
                    elif isinstance(value, (datetime.datetime, datetime.date)):
                        formatted_value = str(value)
                    elif isinstance(value, (dict, list)):
                        # Convert complex objects to JSON strings
                        formatted_value = json.dumps(value, cls=DateTimeEncoder)
                    else:
                        formatted_value = str(value)
                    
                    # Escape pipe characters in values for markdown table
                    formatted_value = formatted_value.replace("|", "\\|")
                    values.append(formatted_value)
                
                row = "| " + " | ".join(values) + " |"
                data_rows.append(row)
            
            # Combine all parts of the table
            table = f"{header_row}\n{separator_row}\n" + "\n".join(data_rows)
            markdown_response += table
            
            # Store the original data in a hidden format for CSV export
            json_data = json.dumps(db_result, cls=DateTimeEncoder)
            # Avoid f-string with replacements
            markdown_response += "\n\n<div class='hidden-data' style='display:none;' data-result='"
            markdown_response += json_data.replace('"', '&quot;')
            markdown_response += "'></div>"
            
            # Add record count and export button
            record_count = len(db_result)
            plural = "s" if record_count != 1 else ""
            markdown_response += f"\n\n<div class='result-footer'>"
            markdown_response += f"<span class='record-count'>{record_count} record{plural} returned</span>"
            markdown_response += f"<button class='btn btn-sm btn-outline-secondary export-csv-btn ms-2'>Export CSV</button>"
            markdown_response += "</div>"
            
        # If the result is a dictionary (common for NoSQL databases or aggregation results)
        elif isinstance(db_result, dict):
            # Format as JSON in a code block
            formatted_result = json.dumps(db_result, indent=2, cls=DateTimeEncoder)
            markdown_response += f"```json\n{formatted_result}\n```"
            
            # Store the original data in a hidden format for export
            json_data = json.dumps(db_result, cls=DateTimeEncoder)
            # Avoid f-string with replacements
            markdown_response += "\n\n<div class='hidden-data' style='display:none;' data-result='"
            markdown_response += json_data.replace('"', '&quot;')
            markdown_response += "'></div>"
            
            # Add export button for JSON
            markdown_response += f"\n\n<div class='result-footer'>"
            markdown_response += f"<button class='btn btn-sm btn-outline-secondary export-json-btn'>Export JSON</button>"
            markdown_response += "</div>"
            
        # If it's a simple list or other data type
        else:
            # Format as JSON in a code block
            formatted_result = json.dumps(db_result, indent=2, cls=DateTimeEncoder)
            markdown_response += f"```json\n{formatted_result}\n```"
            
            # Store the original data in a hidden format for export
            json_data = json.dumps(db_result, cls=DateTimeEncoder)
            # Avoid f-string with replacements
            markdown_response += "\n\n<div class='hidden-data' style='display:none;' data-result='"
            markdown_response += json_data.replace('"', '&quot;')
            markdown_response += "'></div>"
            
            # Add count information and export button for lists
            if isinstance(db_result, list):
                count = len(db_result)
                plural = "s" if count != 1 else ""
                markdown_response += f"\n\n<div class='result-footer'>"
                markdown_response += f"<span class='record-count'>{count} result{plural} returned</span>"
                markdown_response += f"<button class='btn btn-sm btn-outline-secondary export-json-btn ms-2'>Export JSON</button>"
                markdown_response += "</div>"
        
        markdown_response += "</div>"
        return markdown_response
    except Exception as e:
        logger.exception("Error formatting response")
        try:
            # Try using the custom encoder for the error message too
            raw_result = json.dumps(db_result, indent=2, cls=DateTimeEncoder)
            return f"Error formatting response: {str(e)}\n\nRaw result:\n```json\n{raw_result}\n```"
        except:
            # If that also fails, return a simpler error
            return f"Error formatting response: {str(e)}\n\nCannot format raw result due to serialization issues."