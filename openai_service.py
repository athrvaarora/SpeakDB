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

# Store the database schema analysis for reference during the session
DATABASE_SCHEMA_ANALYSIS = {}

def generate_query(user_query, db_type, schema_info):
    """
    Generate a database query from a natural language query using OpenAI's GPT
    
    Args:
        user_query (str): The natural language query from the user
        db_type (str): The type of database being queried
        schema_info (dict): Information about the database schema
        
    Returns:
        tuple: (success, query, explanation)
    """
    try:
        # Get or create schema analysis
        schema_analysis = analyze_schema(db_type, schema_info)
        
        # Create a prompt that includes the database type, schema information, and schema analysis
        prompt = f"""
        You are a database query generator. Generate a query for a {db_type} database based on the following natural language request:
        
        "{user_query}"
        
        The database schema is as follows:
        {json.dumps(schema_info, indent=2)}
        
        Schema analysis:
        {json.dumps(schema_analysis, indent=2)}
        
        Use the schema analysis to better understand the data model and relationships.
        
        Respond with JSON in the following format:
        {{
            "query": "the generated query",
            "explanation": "explanation of what the query does and why it satisfies the request"
        }}
        
        Ensure the query is valid for {db_type} syntax.
        """
        
        # Generate the query using OpenAI GPT
        response = openai.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are an expert database query generator with deep understanding of database structures and relationships."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        # Parse the response
        result = json.loads(response.choices[0].message.content)
        query = result.get("query")
        explanation = result.get("explanation")
        
        if not query:
            return False, None, "Failed to generate a query from the GPT response"
        
        return True, query, explanation
    except Exception as e:
        logger.exception("Error generating query with GPT")
        return False, None, f"Error generating query: {str(e)}"

def analyze_schema(db_type, schema_info):
    """
    Analyze the database schema and provide insights for improved query generation
    
    Args:
        db_type (str): The type of database (e.g., 'postgresql', 'mongodb')
        schema_info (dict): Information about the database schema
        
    Returns:
        dict: Analysis results with insights about the schema
    """
    global DATABASE_SCHEMA_ANALYSIS
    
    try:
        # Skip if we already have analysis for this database type
        cache_key = f"{db_type}_{hash(str(schema_info))}"
        if cache_key in DATABASE_SCHEMA_ANALYSIS:
            logger.info(f"Using cached schema analysis for {db_type}")
            return DATABASE_SCHEMA_ANALYSIS[cache_key]
        
        logger.info(f"Analyzing schema for {db_type} database")
        
        # Create a prompt for schema analysis
        prompt = f"""
        You are a database expert. Analyze this {db_type} database schema and provide insights:
        
        {json.dumps(schema_info, indent=2)}
        
        Respond with JSON in the following format:
        {{
            "schema_summary": "brief summary of the database schema",
            "tables": [
                {{
                    "name": "table_name",
                    "purpose": "what this table stores",
                    "key_fields": ["field1", "field2"],
                    "relationships": ["description of relationships"]
                }}
            ],
            "data_domains": ["list of main data domains covered"],
            "recommended_joins": ["suggestions for common table joins"],
            "naming_patterns": "observations about naming conventions",
            "query_recommendations": ["suggestions for efficient queries"]
        }}
        
        For NoSQL databases, adapt the format appropriately (collections instead of tables, etc.).
        Focus on the most important insights that would help in generating accurate queries.
        """
        
        # Generate the schema analysis using OpenAI GPT
        response = openai.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are an expert database analyst."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        # Parse the response
        analysis = json.loads(response.choices[0].message.content)
        
        # Cache the analysis
        DATABASE_SCHEMA_ANALYSIS[cache_key] = analysis
        
        return analysis
    except Exception as e:
        logger.exception(f"Error analyzing schema: {str(e)}")
        # Return a minimal analysis object if there's an error
        return {
            "schema_summary": f"Error analyzing schema: {str(e)}",
            "tables": [],
            "data_domains": [],
            "recommended_joins": [],
            "naming_patterns": "",
            "query_recommendations": []
        }

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
            
            # Add record count
            record_count = len(db_result)
            plural = "s" if record_count != 1 else ""
            markdown_response += f"\n\n<div class='result-footer'>"
            markdown_response += f"<span class='record-count'>{record_count} record{plural} returned</span>"
            markdown_response += "</div>"
            
            # Try to store the original data for export, but continue if it fails
            try:
                json_data = json.dumps(db_result, cls=DateTimeEncoder)
                markdown_response += f"\n\n<div class='export-controls'>"
                markdown_response += f"<button class='btn btn-sm btn-outline-secondary export-csv-btn ms-2'>Export CSV</button>"
                markdown_response += "</div>"
                markdown_response += "\n\n<div class='hidden-data' style='display:none;' data-result='"
                markdown_response += json_data.replace('"', '&quot;')
                markdown_response += "'></div>"
            except Exception as json_err:
                logger.error(f"Error serializing to JSON: {str(json_err)}")
                # Skip export functionality but continue showing the results
            
        # If the result is a dictionary (common for NoSQL databases or aggregation results)
        elif isinstance(db_result, dict):
            try:
                # Format as JSON in a code block
                formatted_result = json.dumps(db_result, indent=2, cls=DateTimeEncoder)
                markdown_response += f"```json\n{formatted_result}\n```"
                
                # Try to add export functionality
                json_data = json.dumps(db_result, cls=DateTimeEncoder)
                markdown_response += f"\n\n<div class='export-controls'>"
                markdown_response += f"<button class='btn btn-sm btn-outline-secondary export-json-btn'>Export JSON</button>"
                markdown_response += "</div>"
                markdown_response += "\n\n<div class='hidden-data' style='display:none;' data-result='"
                markdown_response += json_data.replace('"', '&quot;')
                markdown_response += "'></div>"
            except Exception as json_err:
                logger.error(f"Error serializing dict to JSON: {str(json_err)}")
                # Fall back to just showing the basic string representation
                markdown_response += f"```\n{str(db_result)}\n```"
                
        # If it's a simple list or other data type
        else:
            try:
                # Format as JSON in a code block
                formatted_result = json.dumps(db_result, indent=2, cls=DateTimeEncoder)
                markdown_response += f"```json\n{formatted_result}\n```"
                
                # Add count information for lists
                if isinstance(db_result, list):
                    count = len(db_result)
                    plural = "s" if count != 1 else ""
                    markdown_response += f"\n\n<div class='result-footer'>"
                    markdown_response += f"<span class='record-count'>{count} result{plural} returned</span>"
                    markdown_response += "</div>"
                
                # Try to add export functionality
                try:
                    json_data = json.dumps(db_result, cls=DateTimeEncoder)
                    markdown_response += f"\n\n<div class='export-controls'>"
                    markdown_response += f"<button class='btn btn-sm btn-outline-secondary export-json-btn ms-2'>Export JSON</button>"
                    markdown_response += "</div>"
                    markdown_response += "\n\n<div class='hidden-data' style='display:none;' data-result='"
                    markdown_response += json_data.replace('"', '&quot;')
                    markdown_response += "'></div>"
                except Exception as json_err:
                    logger.error(f"Error serializing list to JSON: {str(json_err)}")
                    # Skip export functionality
            except Exception as format_err:
                logger.error(f"Error formatting as JSON: {str(format_err)}")
                # Fall back to just showing the basic string representation
                markdown_response += f"```\n{str(db_result)}\n```"
        
        markdown_response += "</div>"
        return markdown_response
    except Exception as e:
        logger.error(f"Error formatting response: {str(e)}")
        return f"Error formatting response: {str(e)}\n\nThe query executed correctly but the results couldn't be displayed properly due to formatting issues."