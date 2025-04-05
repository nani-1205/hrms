# hrms/__init__.py

import os
import datetime
from flask import Flask
import pymongo # <--- Import pymongo for index types
from pymongo import MongoClient
from pymongo.errors import CollectionInvalid, ConnectionFailure # Import CollectionInvalid
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

# --- Helper function for initialization ---
def initialize_database(db_instance):
    """
    Ensures required collections and basic indexes exist.
    Call this function *after* successfully connecting to the database.
    """
    required_collections = {
        "users": [
            # Index definitions: list of tuples (key, direction). Add options dict if needed.
            (("username", pymongo.ASCENDING), {"unique": True, "background": True}),
            (("email", pymongo.ASCENDING), {"unique": True, "background": True}),
        ],
        "employees": [
            # Sparse=True allows multiple docs without the field, but if the field exists, it must be unique.
            (("employee_code", pymongo.ASCENDING), {"unique": True, "sparse": True, "background": True}),
            (("email", pymongo.ASCENDING), {"unique": True, "sparse": True, "background": True}),
            (("department", pymongo.ASCENDING), {"background": True}),
        ],
        "leave_requests": [
            (("user_id", pymongo.ASCENDING), {"background": True}),
            (("status", pymongo.ASCENDING), {"background": True}),
            (("start_date", pymongo.DESCENDING), {"background": True}),
        ],
        # Add other collections and their desired indexes here as you build modules:
        # "departments": [ ... ],
        # "attendance_records": [ ... ],
    }

    print(f"Checking database '{db_instance.name}' for required collections and indexes...")
    existing_collections = db_instance.list_collection_names()

    for coll_name, indexes in required_collections.items():
        collection_created = False
        if coll_name not in existing_collections:
            try:
                # Create collection explicitly (optional, insert/index creation does it too)
                # Using create_collection allows setting validation rules later if needed.
                db_instance.create_collection(coll_name)
                print(f"  - Created collection: '{coll_name}'")
                collection_created = True
            except CollectionInvalid:
                # Collection might have been created between list_collection_names and create_collection
                print(f"  - Collection '{coll_name}' already exists (or created concurrently).")
            except Exception as e:
                print(f"  - ERROR creating collection '{coll_name}': {e}")
                continue # Skip index creation if collection creation failed

        # --- Create Indexes ---
        # It's generally safe to call create_index even if the index exists.
        # MongoDB handles it idempotently (won't duplicate or error).
        # Only create indexes specified for *this* collection.
        if indexes:
            try:
                collection = db_instance[coll_name]
                # create_indexes takes a list of IndexModel objects, but
                # create_index is simpler for single index creation.
                for index_spec, index_options in indexes:
                     # Ensure background=True is in options if provided
                    if "background" not in index_options:
                        index_options["background"] = True
                    collection.create_index([index_spec], **index_options)

                if collection_created:
                     print(f"    - Created specified indexes for '{coll_name}'.")
                else:
                     print(f"  - Ensured specified indexes exist for '{coll_name}'.")

            except Exception as e:
                print(f"  - ERROR creating indexes for collection '{coll_name}': {e}")

    print("Database initialization check complete.")


# --- Main Application Factory ---
def create_app():
    """Application Factory Function"""
    global mongo_client, db

    app = Flask(__name__)
    app_config = get_config()
    app.config.from_object(app_config)

    # Context Processor (keep this)
    @app.context_processor
    def inject_now():
        return {'now': datetime.datetime.utcnow()}

    # --- Initialize MongoDB Client and Database ---
    try:
        mongo_host = app_config.MONGO_HOST
        mongo_port = app_config.MONGO_PORT
        mongo_dbname = app_config.MONGO_DBNAME
        mongo_username = app_config.MONGO_USERNAME
        mongo_password = app_config.MONGO_PASSWORD
        mongo_auth_source = app_config.MONGO_AUTHSOURCE

        connection_args = { 'host': mongo_host, 'port': mongo_port }
        if mongo_username and mongo_password:
            connection_args.update({
                'username': mongo_username,
                'password': mongo_password,
                'authSource': mongo_auth_source,
                'authMechanism': 'SCRAM-SHA-256'
            })
            print(f"Attempting MongoDB connection to {mongo_host}:{mongo_port} DB: '{mongo_dbname}' with user '{mongo_username}' (authSource: {mongo_auth_source})")
        else:
            print(f"Attempting MongoDB connection to {mongo_host}:{mongo_port} DB: '{mongo_dbname}' without authentication")

        mongo_client = MongoClient(**connection_args, serverSelectionTimeoutMS=5000) # Added timeout
        mongo_client.admin.command('ping') # Use ping for modern MongoDB
        print("Successfully connected to MongoDB server!")
        db = mongo_client[mongo_dbname]
        app.db = db

        # ---> Call Initialization Function Here <---
        initialize_database(db)
        # ------------------------------------------

    except ConnectionFailure as e:
        print(f"CRITICAL: Could not connect to MongoDB server at {app_config.MONGO_HOST}:{app_config.MONGO_PORT}. Error: {e}")
        exit(1)
    except Exception as e:
        print(f"CRITICAL: An unexpected error occurred during MongoDB initialization: {e}")
        exit(1)

    # --- Initialize Flask-Login ---
    login_manager.init_app(app)
    @login_manager.user_loader
    def load_user(user_id):
        from .models.user import User
        return User.get_by_id(user_id)

    # --- Register Blueprints ---
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