# hrms/__init__.py

import os
import datetime
import pymongo
from pymongo import MongoClient
from pymongo.errors import CollectionInvalid, ConnectionFailure, OperationFailure
from flask import Flask # <--- Ensure this import is present
from flask_login import LoginManager
from .config import get_config
import logging # Import Python's logging module

# --- Configure logging ---
# Basic configuration - adjust level and format as needed
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__) # Get a logger instance for this module

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
        # This case should ideally not happen after app initialization succeeds
        log.error("get_db() called before database was initialized.")
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
            (("username", pymongo.ASCENDING), {"unique": True, "background": True, "name": "username_uniq_idx"}),
            (("email", pymongo.ASCENDING), {"unique": True, "background": True, "name": "email_uniq_idx"}),
        ],
        "employees": [
            # Sparse=True allows multiple docs without the field, but if the field exists, it must be unique.
            (("employee_code", pymongo.ASCENDING), {"unique": True, "sparse": True, "background": True, "name": "emp_code_uniq_idx"}),
            (("email", pymongo.ASCENDING), {"unique": True, "sparse": True, "background": True, "name": "emp_email_uniq_idx"}), # May conflict with users.email if same email used
            (("department", pymongo.ASCENDING), {"background": True, "name": "emp_dept_idx"}),
        ],
        "leave_requests": [
            (("user_id", pymongo.ASCENDING), {"background": True, "name": "leave_userid_idx"}),
            (("status", pymongo.ASCENDING), {"background": True, "name": "leave_status_idx"}),
            (("start_date", pymongo.DESCENDING), {"background": True, "name": "leave_startdate_idx"}),
        ],
        # Add other collections and their desired indexes here:
        # "departments": [ ... ],
        # "attendance_records": [ ... ],
    }

    log.info(f"Checking database '{db_instance.name}' for required collections and indexes...")
    try:
        existing_collections = db_instance.list_collection_names()
        log.info(f"Existing collections found: {existing_collections}")
    except OperationFailure as e:
        log.error(f"PERMISSION ERROR listing collections in '{db_instance.name}': {e.details}")
        log.error("Please check MongoDB user permissions for 'listCollections'.")
        return # Stop initialization if basic listing fails
    except Exception as e:
        log.error(f"Unexpected error listing collections in '{db_instance.name}': {e}", exc_info=True)
        return

    for coll_name, indexes in required_collections.items():
        collection_created = False
        collection_handle = None # Define handle outside try block

        # --- Ensure Collection Exists ---
        if coll_name not in existing_collections:
            try:
                # Create collection explicitly
                collection_handle = db_instance.create_collection(coll_name)
                log.info(f"  - Successfully CREATED collection: '{coll_name}'")
                collection_created = True
            except CollectionInvalid:
                log.warning(f"  - Collection '{coll_name}' already exists (or created concurrently).")
                collection_handle = db_instance[coll_name] # Get handle if it exists
            except OperationFailure as e:
                log.error(f"  - PERMISSION ERROR creating collection '{coll_name}': {e.details}")
                log.error("    Please check MongoDB user permissions for 'createCollection'.")
                continue # Skip index creation if collection creation failed
            except Exception as e:
                log.error(f"  - UNEXPECTED ERROR creating collection '{coll_name}': {e}", exc_info=True)
                continue
        else:
             collection_handle = db_instance[coll_name] # Get handle if it already exists

        # --- Create Indexes ---
        # Proceed only if we have a valid collection handle
        if collection_handle and indexes:
            created_index_names = []
            log.debug(f"  - Ensuring indexes for collection '{coll_name}'...")
            try:
                existing_index_info = collection_handle.index_information()
                existing_index_names = list(existing_index_info.keys())
                log.debug(f"    Existing indexes: {existing_index_names}")

                for index_spec, index_options in indexes:
                    # Ensure background=True is added if not specified by developer
                    if "background" not in index_options:
                        index_options["background"] = True
                    # Ensure index has a name for easier management and checking
                    if "name" not in index_options:
                         index_options["name"] = "_".join([f"{k}_{v}" for k, v in index_spec]) + "_idx"
                    idx_name = index_options["name"]

                    # Check if an index with the desired *name* already exists
                    if idx_name not in existing_index_names:
                        try:
                            idx_result_name = collection_handle.create_index([index_spec], **index_options)
                            created_index_names.append(idx_result_name)
                            log.info(f"    - Created index '{idx_result_name}' on '{coll_name}'.")
                        except OperationFailure as e:
                            log.error(f"    - PERMISSION ERROR creating index '{idx_name}' on '{coll_name}': {e.details}")
                            log.error("      Please check MongoDB user permissions for 'createIndex'.")
                        except Exception as e:
                            log.error(f"    - UNEXPECTED ERROR creating index '{idx_name}' on '{coll_name}': {e}", exc_info=True)
                    # else: # Optional: Log if index already exists
                    #    log.debug(f"    - Index '{idx_name}' already exists on '{coll_name}'.")

                if collection_created:
                    if created_index_names: # Log only if new indexes were actually created
                        log.info(f"    - Finished creating specified indexes for new collection '{coll_name}'.")
                # else: # Optional: Log check completion for existing collections
                    # log.info(f"  - Finished ensuring indexes for existing collection '{coll_name}'.")

            except OperationFailure as e:
                 log.error(f"  - PERMISSION ERROR accessing index info for '{coll_name}': {e.details}")
                 log.error("    Please check MongoDB user permissions for 'listIndexes'.")
            except Exception as e:
                # Catch errors getting the collection handle or index info
                log.error(f"  - ERROR ensuring indexes for collection '{coll_name}': {e}", exc_info=True)

    log.info("Database initialization check complete.")


# --- Main Application Factory ---
def create_app():
    """Application Factory Function"""
    global mongo_client, db

    # Ensure 'Flask' is defined before this line
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

        connection_args = {
            'host': mongo_host,
            'port': mongo_port,
            'serverSelectionTimeoutMS': 5000 # Timeout for server selection
            # Add other options like replicaSet, tls, etc., if needed
            }
        if mongo_username and mongo_password:
            connection_args.update({
                'username': mongo_username,
                'password': mongo_password,
                'authSource': mongo_auth_source,
                'authMechanism': 'SCRAM-SHA-256' # Adjust if needed
            })
            log.info(f"Attempting MongoDB connection to {mongo_host}:{mongo_port} DB: '{mongo_dbname}' with user '{mongo_username}' (authSource: {mongo_auth_source})")
        else:
            log.info(f"Attempting MongoDB connection to {mongo_host}:{mongo_port} DB: '{mongo_dbname}' without authentication")

        mongo_client = MongoClient(**connection_args)
        # The ismaster command is cheap and does not require auth. 'ping' is preferred now.
        log.info("Pinging MongoDB server...")
        mongo_client.admin.command('ping')
        log.info("Successfully connected to MongoDB server!")
        db = mongo_client[mongo_dbname] # Get database handle
        app.db = db # Make db accessible via app context if needed
        log.info(f"Database handle obtained for '{mongo_dbname}'.")

        # ---> Call Initialization Function Here <---
        initialize_database(db)
        # ------------------------------------------

    except ConnectionFailure as e:
        log.critical(f"Could not connect to MongoDB server at {app_config.MONGO_HOST}:{app_config.MONGO_PORT}. Is it running? Check network/firewall. Error: {e}")
        exit(1)
    except OperationFailure as e: # Catch auth errors during initial connection/ping
        log.critical(f"MongoDB authentication/operation error during connection (check credentials/permissions for user '{mongo_username}' on authSource '{mongo_auth_source}'): {e.details}")
        exit(1)
    except Exception as e:
        log.critical(f"An unexpected error occurred during MongoDB initialization: {e}", exc_info=True)
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
    # Register other blueprints...

    log.info("Flask app created and configured successfully.")
    return app