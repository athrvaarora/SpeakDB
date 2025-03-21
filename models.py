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
    username = Column(String(64), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationship with chats
    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")
    
    def __init__(self, username=None, email=None, password=None):
        self.id = str(uuid.uuid4())
        self.username = username
        self.email = email
        if password:
            self.set_password(password)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active
        }

class Chat(db.Model):
    __tablename__ = 'chats'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    db_type = Column(String(50), nullable=False)
    db_name = Column(String(100))
    db_credentials = Column(Text)  # JSON string of database credentials
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    messages = relationship("ChatMessage", back_populates="chat", cascade="all, delete-orphan")
    user = relationship("User", back_populates="chats")
    
    def __init__(self, id=None, user_id=None, db_type=None, db_name=None, db_credentials=None):
        self.id = id or str(uuid.uuid4())
        self.user_id = user_id
        self.db_type = db_type
        self.db_name = db_name
        self.db_credentials = db_credentials
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
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
