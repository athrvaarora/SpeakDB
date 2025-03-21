import os
from app import app
from models import db

print("Creating database tables...")

# This is necessary to create the tables in the PostgreSQL database
with app.app_context():
    # Create all tables
    db.create_all()
    print("Tables created successfully!")