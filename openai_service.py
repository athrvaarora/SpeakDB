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
        3. When a user wants to see data from multiple tables, use JOIN operations or UNION when appropriate, rather than multiple separate SELECT statements.
        4. For NoSQL databases, ensure the query format matches the database's specific API requirements.
        5. If a user wants "all records from all tables", use UNION ALL with consistent column structures, or generate a query that retrieves one table at a time.
        
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
        result = json.loads(response.choices[0].message.content)
        query = result.get("query")
        explanation = result.get("explanation")
        needs_multiple_queries = result.get("needs_multiple_queries", False)
        additional_queries = result.get("additional_queries", [])
        
        if not query:
            return False, None, "Failed to generate a query from the GPT response", False, []
        
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