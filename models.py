import uuid
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, String, DateTime, Text, Boolean, ForeignKey, Integer
from sqlalchemy.orm import relationship
from flask_login import UserMixin

# Initialize SQLAlchemy
db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    firebase_uid = Column(String(128), unique=True)
    email = Column(String(128), unique=True, nullable=False)
    name = Column(String(128))
    profile_picture = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    subscription = relationship("Subscription", back_populates="user", uselist=False)
    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")
    
    def __init__(self, firebase_uid=None, email=None, name=None, profile_picture=None):
        self.id = str(uuid.uuid4())
        self.firebase_uid = firebase_uid
        self.email = email
        self.name = name
        self.profile_picture = profile_picture
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'profile_picture': self.profile_picture,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'subscription': self.subscription.to_dict() if self.subscription else None
        }
    
    @property
    def is_authenticated(self):
        return True
    
    @property
    def is_active(self):
        return True
    
    @property
    def is_anonymous(self):
        return False
    
    def get_id(self):
        return str(self.id)
    
    def get_remaining_free_queries(self):
        """Get remaining free queries for the day"""
        if self.subscription and self.subscription.is_active() and self.subscription.plan_type == 'enterprise':
            return float('inf')
            
        # Check usage for free plan
        today = datetime.utcnow().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        
        from app import db
        query_count = db.session.query(ChatMessage).join(Chat).filter(
            Chat.user_id == self.id,
            ChatMessage.created_at >= today_start,
            ChatMessage.created_at <= today_end
        ).count()
        
        return max(10 - query_count, 0)  # 10 free queries per day


class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    stripe_customer_id = Column(String(128))
    stripe_subscription_id = Column(String(128))
    plan_type = Column(String(20), nullable=False, default='free')  # 'free' or 'enterprise'
    status = Column(String(20), nullable=False, default='active')
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with user
    user = relationship("User", back_populates="subscription")
    
    def __init__(self, user_id=None, plan_type='free', stripe_customer_id=None, 
                 stripe_subscription_id=None, status='active', end_date=None):
        self.id = str(uuid.uuid4())
        self.user_id = user_id
        self.plan_type = plan_type
        self.stripe_customer_id = stripe_customer_id
        self.stripe_subscription_id = stripe_subscription_id
        self.status = status
        
        # For free plan, set end date to 1 year from now (will be renewed)
        if plan_type == 'free' and not end_date:
            self.end_date = datetime.utcnow() + timedelta(days=365)
        else:
            self.end_date = end_date
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'plan_type': self.plan_type,
            'status': self.status,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def is_active(self):
        """Check if subscription is active"""
        if self.status != 'active':
            return False
            
        if self.end_date and self.end_date < datetime.utcnow():
            return False
            
        return True

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
