# hrms/__init__.py

import os
from flask import Flask
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure # Import specific error
from flask_login import LoginManager
from .config import get_config
from .models.user import User

# Initialize extensions
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

mongo_client = None
db = None

def create_app():
    """Application Factory Function"""
    global mongo_client, db

    app = Flask(__name__)
    app_config = get_config()
    app.config.from_object(app_config)

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
            # Optional: Add TLS/SSL settings if needed for cloud DBs like Atlas
            # 'tls': True,
            # 'tlsCAFile': '/path/to/ca.pem',
        }

        # Add authentication arguments only if username and password are provided
        if mongo_username and mongo_password:
            connection_args['username'] = mongo_username
            connection_args['password'] = mongo_password
            connection_args['authSource'] = mongo_auth_source
            connection_args['authMechanism'] = 'SCRAM-SHA-256' # Or 'SCRAM-SHA-1' or 'MONGODB-CR' depending on server version
            print(f"Attempting MongoDB connection to {mongo_host}:{mongo_port} DB: '{mongo_dbname}' with user '{mongo_username}' (authSource: {mongo_auth_source})")
        else:
            print(f"Attempting MongoDB connection to {mongo_host}:{mongo_port} DB: '{mongo_dbname}' without authentication")

        mongo_client = MongoClient(**connection_args)

        # The ismaster command is cheap and does not require auth.
        mongo_client.admin.command('ismaster')
        print("Successfully connected to MongoDB server!")

        db = mongo_client[mongo_dbname] # Select the specific database
        app.db = db # Make db accessible via app context if needed

    except ConnectionFailure as e:
        print(f"CRITICAL: Could not connect to MongoDB server at {app_config.MONGO_HOST}:{app_config.MONGO_PORT}. Error: {e}")
        # Consider logging the full traceback here
        print("Please check your MongoDB server status and connection details in .env")
        exit(1) # Exit if database connection fails on startup
    except Exception as e: # Catch other potential errors during connection setup
        print(f"CRITICAL: An unexpected error occurred during MongoDB initialization: {e}")
        # Consider logging the full traceback here
        exit(1)

    # --- Initialize Flask-Login ---
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.get_by_id(user_id)

    # --- Register Blueprints ---
    from .routes.auth import auth_bp
    from .routes.main import main_bp
    from .routes.employee import employee_bp
    from .routes.leave import leave_bp
    # Add other blueprints here

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)
    app.register_blueprint(employee_bp, url_prefix='/employees')
    app.register_blueprint(leave_bp, url_prefix='/leave')
    # Register other blueprints

    print("Flask app created and configured successfully.")
    return app

# --- Function to get the database instance ---
def get_db():
    if db is None:
        # This case should ideally not happen after app initialization
        raise RuntimeError("Database not initialized. Ensure create_app() was called.")
    return db