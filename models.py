import uuid
from datetime import datetime

# Note: In a real application, we would use SQLAlchemy or another ORM to define these models
# For this MVP, we'll just define the model classes

class Chat:
    def __init__(self, id=None, db_type=None, db_name=None):
        self.id = id or str(uuid.uuid4())
        self.db_type = db_type
        self.db_name = db_name
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def to_dict(self):
        return {
            'id': self.id,
            'db_type': self.db_type,
            'db_name': self.db_name,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class ChatMessage:
    def __init__(self, id=None, chat_id=None, query=None, generated_query=None, 
                 result=None, error=None, is_error=False):
        self.id = id or str(uuid.uuid4())
        self.chat_id = chat_id
        self.query = query
        self.generated_query = generated_query
        self.result = result
        self.error = error
        self.is_error = is_error
        self.created_at = datetime.now()
    
    def to_dict(self):
        return {
            'id': self.id,
            'chat_id': self.chat_id,
            'query': self.query,
            'generated_query': self.generated_query,
            'result': self.result,
            'error': self.error,
            'is_error': self.is_error,
            'created_at': self.created_at.isoformat()
        }
