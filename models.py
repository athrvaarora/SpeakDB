import uuid
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, String, DateTime, Text, Boolean, ForeignKey, Integer
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

# Initialize SQLAlchemy
db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(120))
    email = Column(String(120), unique=True, nullable=False)
    profile_picture = Column(String(256), nullable=True)
    firebase_uid = Column(String(128), nullable=True)
    # Note: password_hash removed as it doesn't exist in the actual database schema
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Note: Chat relationship removed as it doesn't match the database schema
    
    def __init__(self, email=None, name=None, password=None, profile_picture=None, firebase_uid=None):
        self.id = str(uuid.uuid4())
        self.email = email
        self.name = name
        self.profile_picture = profile_picture
        self.firebase_uid = firebase_uid
        # Note: password handling removed as the column doesn't exist in database
    
    # Note: Firebase authentication should be used instead of password auth
    # These methods are kept as stubs but will always return False for now
    def set_password(self, password):
        # Method retained for compatibility but does nothing as password_hash column doesn't exist
        pass
        
    def check_password(self, password):
        # Always return False as we can't store passwords
        return False
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'profile_picture': self.profile_picture,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Chat(db.Model):
    __tablename__ = 'chats'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    db_type = Column(String(50), nullable=False)
    db_name = Column(String(100))
    db_credentials = Column(Text)  # JSON string of database credentials
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    messages = relationship("ChatMessage", back_populates="chat", cascade="all, delete-orphan")
    # Note: user relationship removed as it's not in the database schema
    
    def __init__(self, id=None, db_type=None, db_name=None, db_credentials=None):
        self.id = id or str(uuid.uuid4())
        self.db_type = db_type
        self.db_name = db_name
        self.db_credentials = db_credentials
    
    def to_dict(self):
        return {
            'id': self.id,
            'db_type': self.db_type,
            'db_name': self.db_name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'message_count': len(self.messages) if self.messages else 0
        }


class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    chat_id = Column(String(36), ForeignKey('chats.id'), nullable=False)
    query = Column(Text, nullable=False)
    generated_query = Column(Text)
    result = Column(Text)
    explanation = Column(Text)
    error = Column(Text)
    is_error = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship with chat
    chat = relationship("Chat", back_populates="messages")
    
    def __init__(self, id=None, chat_id=None, query=None, generated_query=None, 
                 result=None, explanation=None, error=None, is_error=False):
        self.id = id or str(uuid.uuid4())
        self.chat_id = chat_id
        self.query = query
        self.generated_query = generated_query
        self.result = result
        self.explanation = explanation
        self.error = error
        self.is_error = is_error
    
    def to_dict(self):
        return {
            'id': self.id,
            'chat_id': self.chat_id,
            'query': self.query,
            'generated_query': self.generated_query,
            'result': self.result,
            'explanation': self.explanation,
            'error': self.error,
            'is_error': self.is_error,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
