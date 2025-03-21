import os
import json
import functools
from datetime import datetime, timedelta
import uuid

import firebase_admin
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials
from flask import Blueprint, request, redirect, url_for, session, flash, abort
from flask_login import LoginManager, login_user, logout_user, current_user, login_required

from models import db, User, Subscription

# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    # Check if we have the Firebase credentials in environment variables
    firebase_credentials = {
        "type": "service_account",
        "project_id": os.environ.get("FIREBASE_PROJECT_ID"),
        "private_key_id": os.environ.get("FIREBASE_PRIVATE_KEY_ID", ""),
        "private_key": os.environ.get("FIREBASE_PRIVATE_KEY", "").replace("\\n", "\n"),
        "client_email": os.environ.get("FIREBASE_CLIENT_EMAIL", ""),
        "client_id": os.environ.get("FIREBASE_CLIENT_ID", ""),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": os.environ.get("FIREBASE_CLIENT_CERT_URL", "")
    }
    
    try:
        firebase_admin.initialize_app(credentials.Certificate(firebase_credentials))
    except (ValueError, firebase_admin.exceptions.FirebaseError) as e:
        print(f"Firebase initialization error: {e}")
        # Continue without Firebase, will initialize later when credentials are available

login_manager = LoginManager()

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID."""
    return User.query.get(user_id)

def init_app(app):
    """Initialize authentication for the Flask app."""
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # Ensure Firebase configuration is available to templates
    app.config['FIREBASE_API_KEY'] = os.environ.get('FIREBASE_API_KEY')
    app.config['FIREBASE_AUTH_DOMAIN'] = os.environ.get('FIREBASE_AUTH_DOMAIN')
    app.config['FIREBASE_PROJECT_ID'] = os.environ.get('FIREBASE_PROJECT_ID')
    app.config['FIREBASE_STORAGE_BUCKET'] = os.environ.get('FIREBASE_STORAGE_BUCKET')
    app.config['FIREBASE_MESSAGING_SENDER_ID'] = os.environ.get('FIREBASE_MESSAGING_SENDER_ID')
    app.config['FIREBASE_APP_ID'] = os.environ.get('FIREBASE_APP_ID')
    
    @app.before_request
    def before_request():
        """Check if user is authenticated before each request."""
        # Add public routes that don't require authentication
        public_routes = ['index', 'login', 'signup', 'features', 'pricing', 
                        'static', 'firebase_callback', 'payment_success', 
                        'payment_cancel', 'webhook']
        
        # Skip authentication check for public routes
        if request.endpoint in public_routes:
            return
            
        # Skip for webhook endpoints
        if request.path.startswith('/webhook'):
            return
            
        # Require login for protected routes
        if not current_user.is_authenticated:
            return redirect(url_for('login', next=request.url))
    
    @app.route('/logout')
    def logout():
        """Log out a user."""
        logout_user()
        flash('You have been logged out.', 'success')
        return redirect(url_for('index'))
    
    @app.route('/auth/firebase/callback')
    def firebase_callback():
        """Handle Firebase authentication callback."""
        id_token = request.args.get('idToken')
        next_url = request.args.get('next', url_for('select_database'))
        
        if not id_token:
            flash('Authentication failed. Please try again.', 'danger')
            return redirect(url_for('login'))
        
        try:
            # Verify the ID token
            decoded_token = firebase_auth.verify_id_token(id_token)
            firebase_uid = decoded_token['uid']
            email = decoded_token.get('email', '')
            name = decoded_token.get('name', '')
            profile_picture = decoded_token.get('picture', '')
            
            # Check if user exists in our database
            user = User.query.filter_by(firebase_uid=firebase_uid).first()
            
            if not user:
                # Create new user
                user = User(
                    firebase_uid=firebase_uid,
                    email=email,
                    name=name,
                    profile_picture=profile_picture
                )
                db.session.add(user)
                
                # Create free subscription by default
                subscription = Subscription(
                    user_id=user.id,
                    plan_type='free',
                    status='active'
                )
                db.session.add(subscription)
                db.session.commit()
                
                flash('Your account has been created successfully!', 'success')
            else:
                # Update user information
                user.email = email
                user.name = name
                user.profile_picture = profile_picture
                db.session.commit()
            
            # Log in the user
            login_user(user)
            
            # Redirect to the next URL or dashboard
            return redirect(next_url)
            
        except Exception as e:
            flash(f'Authentication error: {str(e)}', 'danger')
            return redirect(url_for('login'))

def login_required(f):
    """Decorator for views that require login."""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def enterprise_required(f):
    """Decorator for views that require enterprise subscription."""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login', next=request.url))
            
        if not current_user.subscription or current_user.subscription.plan_type != 'enterprise' or not current_user.subscription.is_active():
            flash('This feature requires an enterprise subscription.', 'warning')
            return redirect(url_for('pricing'))
            
        return f(*args, **kwargs)
    return decorated_function

def check_query_limit(f):
    """Decorator to check if user has reached their daily free query limit."""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login', next=request.url))
            
        # Skip check for enterprise users
        if current_user.subscription and current_user.subscription.plan_type == 'enterprise' and current_user.subscription.is_active():
            return f(*args, **kwargs)
            
        # Check query limit for free users
        remaining_queries = current_user.get_remaining_free_queries()
        if remaining_queries <= 0:
            return {
                'success': False,
                'error': 'You have reached your daily query limit. Please upgrade to the enterprise plan for unlimited queries.',
                'show_upgrade': True
            }, 429
            
        return f(*args, **kwargs)
    return decorated_function