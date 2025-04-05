# hrms/__init__.py

import os
import datetime # <--- Added import
from flask import Flask
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from flask_login import LoginManager
from .config import get_config

# Initialize extensions
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

mongo_client = None
db = None

# --- Function to get the database instance ---
def get_db():
    """Returns the MongoDB database instance."""
    if db is None:
        raise RuntimeError("Database not initialized. Ensure create_app() was called and DB connection succeeded.")
    return db

def create_app():
    """Application Factory Function"""
    global mongo_client, db

    app = Flask(__name__)
    app_config = get_config()
    app.config.from_object(app_config)

    # --- Add Context Processor --- # <--- Added section
    @app.context_processor
    def inject_now():
        """Injects the current UTC datetime into template context."""
        # Use utcnow() for timezone consistency, common in web apps
        return {'now': datetime.datetime.utcnow()}
    # ----------------------------- #

    # --- Initialize MongoDB Client and Database ---
    try:
        mongo_host = app_config.MONGO_HOST
        mongo_port = app_config.MONGO_PORT
        mongo_dbname = app_config.MONGO_DBNAME
        mongo_username = app_config.MONGO_USERNAME
        mongo_password = app_config.MONGO_PASSWORD
        mongo_auth_source = app_config.MONGO_AUTHSOURCE

        connection_args = {
            'host': mongo_host,
            'port': mongo_port,
            # Optional: Add TLS/SSL settings if needed
            # 'tls': True,
        }

        if mongo_username and mongo_password:
            connection_args['username'] = mongo_username
            connection_args['password'] = mongo_password
            connection_args['authSource'] = mongo_auth_source
            connection_args['authMechanism'] = 'SCRAM-SHA-256' # Adjust if needed
            print(f"Attempting MongoDB connection to {mongo_host}:{mongo_port} DB: '{mongo_dbname}' with user '{mongo_username}' (authSource: {mongo_auth_source})")
        else:
            print(f"Attempting MongoDB connection to {mongo_host}:{mongo_port} DB: '{mongo_dbname}' without authentication")

        mongo_client = MongoClient(**connection_args)

        # Test connection
        mongo_client.admin.command('ismaster') # Use ismaster or ping
        print("Successfully connected to MongoDB server!")

        db = mongo_client[mongo_dbname] # Select the specific database
        app.db = db # Make db accessible via app context if needed

    except ConnectionFailure as e:
        print(f"CRITICAL: Could not connect to MongoDB server at {app_config.MONGO_HOST}:{app_config.MONGO_PORT}. Error: {e}")
        print("Please check your MongoDB server status and connection details in .env")
        exit(1) # Exit if database connection fails on startup
    except Exception as e: # Catch other potential errors during connection setup
        print(f"CRITICAL: An unexpected error occurred during MongoDB initialization: {e}")
        exit(1)

    # --- Initialize Flask-Login ---
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        # Import User model *inside* the function to avoid circular imports
        from .models.user import User
        return User.get_by_id(user_id)

    # --- Register Blueprints ---
    # Import blueprints *after* db and extensions might be needed by them
    from .routes.auth import auth_bp
    from .routes.main import main_bp
    from .routes.employee import employee_bp
    from .routes.leave import leave_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)
    app.register_blueprint(employee_bp, url_prefix='/employees')
    app.register_blueprint(leave_bp, url_prefix='/leave')

    print("Flask app created and configured successfully.")
    return app