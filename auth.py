import os
import json
import firebase_admin
from firebase_admin import credentials, auth
from flask import session, redirect, url_for, request, g
from flask_login import LoginManager, current_user, login_user, logout_user
from models import db, User, Subscription
from functools import wraps

# Initialize Firebase Admin SDK
cred = credentials.Certificate({
    "type": "service_account",
    "project_id": os.environ.get("FIREBASE_PROJECT_ID"),
    "private_key_id": "", # This is optional since we're using environment variables
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvwIBADANBgkqhkiG9w0BAQEFAASCBKkwggSlAgEAAoIBAQC7VJTUt9Us8cKj\nMzEfYyjiWA4R4/M2bS1GB4t7NXp98C3SC6dVMvDuictGeurT8jNbvJZHtCSuYEvu\nNMoSfm76oqFvAp8Gy0iz5sxjZmSnXyCdPEovGhLa0VzMaQ8s+CLOyS56YyCFGeJZ\ngAOr4kPrvZzvDg+PJm5iR5TAAKFyvQ0gMD8Ybc9/4pCdzcBzYSkkUkdUDqaq3++m\n----END PRIVATE KEY-----\n",
    "client_email": f"firebase-adminsdk@{os.environ.get('FIREBASE_PROJECT_ID')}.iam.gserviceaccount.com",
    "client_id": "",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk%40{os.environ.get('FIREBASE_PROJECT_ID')}.iam.gserviceaccount.com",
    "universe_domain": "googleapis.com"
})

default_app = firebase_admin.initialize_app(cred)

# Initialize Flask-Login
login_manager = LoginManager()

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID."""
    return db.session.get(User, user_id)

def init_app(app):
    """Initialize authentication for the Flask app."""
    login_manager.init_app(app)
    
    # Set up login view
    login_manager.login_view = 'login'
    
    @app.before_request
    def before_request():
        g.user = current_user
        
    @app.route('/logout')
    def logout():
        """Log out a user."""
        logout_user()
        return redirect(url_for('index'))
    
    # Route for Firebase authentication callback
    @app.route('/auth/firebase/callback')
    def firebase_callback():
        id_token = request.args.get('idToken')
        if not id_token:
            return redirect(url_for('login', error='Missing ID token'))
        
        try:
            # Verify the ID token with Firebase
            decoded_token = auth.verify_id_token(id_token)
            firebase_uid = decoded_token['uid']
            
            # Look up the user by Firebase UID
            user = User.query.filter_by(firebase_uid=firebase_uid).first()
            
            if not user:
                # Create a new user record
                email = decoded_token.get('email', '')
                name = decoded_token.get('name', '')
                profile_picture = decoded_token.get('picture', '')
                
                user = User(
                    firebase_uid=firebase_uid,
                    email=email,
                    name=name,
                    profile_picture=profile_picture
                )
                db.session.add(user)
                
                # Create a free subscription by default
                subscription = Subscription(user_id=user.id, plan_type='free')
                db.session.add(subscription)
                
                db.session.commit()
            
            # Log in the user with Flask-Login
            login_user(user)
            
            # Redirect to the next page or dashboard
            next_page = request.args.get('next')
            return redirect(next_page or url_for('select_database'))
            
        except Exception as e:
            print(f"Firebase auth error: {e}")
            return redirect(url_for('login', error='Authentication failed'))

def login_required(f):
    """Decorator for views that require login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def enterprise_required(f):
    """Decorator for views that require enterprise subscription."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login', next=request.url))
            
        if not (current_user.subscription and 
                current_user.subscription.is_active() and 
                current_user.subscription.plan_type == 'enterprise'):
            return redirect(url_for('pricing', next=request.url))
            
        return f(*args, **kwargs)
    return decorated_function

def check_query_limit(f):
    """Decorator to check if user has reached their daily free query limit."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login', next=request.url))
            
        # Enterprise users have unlimited queries
        if current_user.subscription and current_user.subscription.is_active() and current_user.subscription.plan_type == 'enterprise':
            return f(*args, **kwargs)
            
        # Free users have a limit of 10 queries per day
        remaining = current_user.get_remaining_free_queries()
        if remaining <= 0:
            return redirect(url_for('pricing', limit_reached=True))
            
        return f(*args, **kwargs)
    return decorated_function