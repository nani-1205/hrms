# hrms/__init__.py

import os
from flask import Flask
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from flask_login import LoginManager
from .config import get_config
# Remove the User import from here:
# from .models.user import User

# Initialize extensions
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

mongo_client = None
db = None

# --- Function to get the database instance ---
# Define get_db BEFORE create_app if models might need it globally,
# but ensure it relies on 'db' which is set within create_app.
def get_db():
    """Returns the MongoDB database instance."""
    # This relies on 'db' being initialized by create_app first.
    if db is None:
        raise RuntimeError("Database not initialized. Ensure create_app() was called and DB connection succeeded.")
    return db

def create_app():
    """Application Factory Function"""
    global mongo_client, db

    app = Flask(__name__)
    app_config = get_config()
    app.config.from_object(app_config)

    # --- Initialize MongoDB Client and Database ---
    try:
        # ... (Keep your existing MongoDB connection logic here) ...
        mongo_host = app_config.MONGO_HOST
        mongo_port = app_config.MONGO_PORT
        mongo_dbname = app_config.MONGO_DBNAME
        mongo_username = app_config.MONGO_USERNAME
        mongo_password = app_config.MONGO_PASSWORD
        mongo_auth_source = app_config.MONGO_AUTHSOURCE

        connection_args = {
            'host': mongo_host,
            'port': mongo_port,
        }
        if mongo_username and mongo_password:
            connection_args['username'] = mongo_username
            connection_args['password'] = mongo_password
            connection_args['authSource'] = mongo_auth_source
            connection_args['authMechanism'] = 'SCRAM-SHA-256'
            print(f"Attempting MongoDB connection to {mongo_host}:{mongo_port} DB: '{mongo_dbname}' with user '{mongo_username}' (authSource: {mongo_auth_source})")
        else:
            print(f"Attempting MongoDB connection to {mongo_host}:{mongo_port} DB: '{mongo_dbname}' without authentication")

        mongo_client = MongoClient(**connection_args)
        mongo_client.admin.command('ismaster')
        print("Successfully connected to MongoDB server!")
        db = mongo_client[mongo_dbname] # Assign to the global 'db' variable
        app.db = db

    except ConnectionFailure as e:
        print(f"CRITICAL: Could not connect to MongoDB server at {app_config.MONGO_HOST}:{app_config.MONGO_PORT}. Error: {e}")
        print("Please check your MongoDB server status and connection details in .env")
        exit(1)
    except Exception as e:
        print(f"CRITICAL: An unexpected error occurred during MongoDB initialization: {e}")
        exit(1)

    # --- Initialize Flask-Login ---
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        # ---> Import User model *inside* the function <---
        from .models.user import User
        # This function is only called during requests when a user needs
        # to be loaded, by which time all modules are fully imported.
        return User.get_by_id(user_id)

    # --- Register Blueprints ---
    # Import blueprints *after* db and extensions are initialized if they depend on them
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

# Note: get_db() is defined above create_app now.
# It relies on the global 'db' being set within create_app.