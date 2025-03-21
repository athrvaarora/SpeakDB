import os
import json
import logging
from openai import OpenAI

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
        tuple: (success, query, explanation)
    """
    try:
        # Create a prompt that includes the database type and schema information
        prompt = f"""
        You are a database query generator. Generate a query for a {db_type} database based on the following natural language request:
        
        "{user_query}"
        
        The database schema is as follows:
        {json.dumps(schema_info, indent=2)}
        
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
                {"role": "system", "content": "You are an expert database query generator."},
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
        # Format raw results as JSON string with nice indentation
        formatted_result = json.dumps(db_result, indent=2)
        
        # Create a markdown-formatted response that just shows the query and raw results
        markdown_response = f"""
## Query Results

```json
{formatted_result}
```
"""
        
        return markdown_response
    except Exception as e:
        logger.exception("Error formatting response")
        return f"Error formatting response: {str(e)}\n\nRaw result: {json.dumps(db_result, indent=2)}"
