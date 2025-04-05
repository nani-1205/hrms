# hrms/__init__.py

import os
import datetime
import pymongo # Import base pymongo for index types
from pymongo import MongoClient
from pymongo.errors import CollectionInvalid, ConnectionFailure, OperationFailure # Import specific errors
from flask import Flask # Ensure Flask is imported
from flask_login import LoginManager
from .config import get_config # Import configuration helper
import logging # Import Python's logging module

# --- Configure logging ---
# Configures basic logging to output INFO level messages and above
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S' # Optional: Customize date format
)
# Get a logger specifically for this module (__init__.py)
log = logging.getLogger(__name__)

# --- Initialize Flask Extensions ---
login_manager = LoginManager()
login_manager.login_view = 'auth.login' # Route name for login page
login_manager.login_message_category = 'info' # Bootstrap category for flash message

# --- Global Variables for Database ---
# These will be assigned within create_app
mongo_client = None
db = None

# --- Function to get the database instance ---
# Ensures other modules can safely get the db handle after initialization
def get_db():
    """Returns the MongoDB database instance."""
    if db is None:
        log.error("get_db() called before database was initialized.")
        raise RuntimeError("Database not initialized. Ensure create_app() was called and DB connection succeeded.")
    return db

# --- Helper function for Database Initialization ---
def initialize_database(db_instance):
    """
    Ensures required collections and basic indexes exist in the database.
    This function is idempotent - safe to run multiple times.
    """
    # Define required collections and their essential indexes
    required_collections = {
        # Collection Name: List of index definitions
        "users": [
            # Each index definition is a tuple: ( (key_spec), {options} )
            (("username", pymongo.ASCENDING), {"unique": True, "background": True, "name": "username_uniq_idx"}),
            (("email", pymongo.ASCENDING), {"unique": True, "background": True, "name": "email_uniq_idx"}),
        ],
        "employees": [
            (("employee_code", pymongo.ASCENDING), {"unique": True, "sparse": True, "background": True, "name": "emp_code_uniq_idx"}),
            (("email", pymongo.ASCENDING), {"unique": True, "sparse": True, "background": True, "name": "emp_email_uniq_idx"}),
            (("department", pymongo.ASCENDING), {"background": True, "name": "emp_dept_idx"}),
        ],
        "leave_requests": [
            (("user_id", pymongo.ASCENDING), {"background": True, "name": "leave_userid_idx"}),
            (("status", pymongo.ASCENDING), {"background": True, "name": "leave_status_idx"}),
            (("start_date", pymongo.DESCENDING), {"background": True, "name": "leave_startdate_idx"}),
        ],
        # Add definitions for other collections as needed:
        # "departments": [ ... ],
        # "attendance_records": [ ... ],
    }

    log.info(f"Checking database '{db_instance.name}' for required collections and indexes...")
    try:
        # Get list of collections actually present in the database
        existing_collections = db_instance.list_collection_names()
        log.info(f"Existing collections found: {existing_collections}")
    except OperationFailure as e:
        # This likely means the user doesn't even have permission to list collections
        log.error(f"PERMISSION ERROR listing collections in '{db_instance.name}': {e.details}")
        log.error("Please check MongoDB user permissions for 'listCollections'. Initialization cannot proceed.")
        return # Stop initialization
    except Exception as e:
        log.error(f"Unexpected error listing collections in '{db_instance.name}': {e}", exc_info=True)
        return # Stop initialization

    # Iterate through the collections defined as required by the application
    for coll_name, indexes in required_collections.items():
        collection_created = False
        collection_handle = None # Initialize handle

        # --- Ensure Collection Exists ---
        if coll_name not in existing_collections:
            log.info(f"  - Collection '{coll_name}' not found. Attempting creation...")
            try:
                # Explicitly create the collection
                # MongoDB also creates collections implicitly on first insert/index creation,
                # but explicit creation allows setting validation rules later if desired.
                collection_handle = db_instance.create_collection(coll_name)
                log.info(f"  - Successfully CREATED collection: '{coll_name}'")
                collection_created = True
            except CollectionInvalid:
                # This might happen in rare concurrent cases or if list_collection_names was stale
                log.warning(f"  - Collection '{coll_name}' already exists (or created concurrently).")
                collection_handle = db_instance[coll_name] # Get handle to existing collection
            except OperationFailure as e:
                # Log specific permission errors for creating collections
                log.error(f"  - PERMISSION ERROR creating collection '{coll_name}': {e.details}")
                log.error("    Please check MongoDB user permissions for 'createCollection'.")
                continue # Skip index creation for this collection if creation failed
            except Exception as e:
                log.error(f"  - UNEXPECTED ERROR creating collection '{coll_name}': {e}", exc_info=True)
                continue # Skip index creation
        else:
             # If collection already exists, just get a handle to it
             log.debug(f"  - Collection '{coll_name}' already exists.")
             collection_handle = db_instance[coll_name]

        # --- Ensure Indexes Exist ---
        # Proceed only if we successfully got a collection handle and indexes are defined
        # ---> CORRECTED THIS LINE <---
        if collection_handle is not None and indexes:
        # -----------------------------
            created_index_names = []
            log.debug(f"  - Ensuring indexes for collection '{coll_name}'...")
            try:
                # Get info about indexes already present on the collection
                existing_index_info = collection_handle.index_information()
                existing_index_names = list(existing_index_info.keys())
                log.debug(f"    Existing indexes on '{coll_name}': {existing_index_names}")

                # Iterate through indexes defined as required for this collection
                for index_spec, index_options in indexes:
                    # Ensure background=True is added for non-blocking builds if not specified
                    if "background" not in index_options:
                        index_options["background"] = True
                    # Ensure the index has a name for easier identification and checking
                    # Generate a default name if one isn't provided in the definition
                    if "name" not in index_options:
                         index_options["name"] = "_".join([f"{k}_{v}" for k, v in index_spec]) + "_idx"
                    idx_name = index_options["name"]

                    # Check if an index with this *name* already exists
                    if idx_name not in existing_index_names:
                        log.info(f"    - Index '{idx_name}' not found on '{coll_name}'. Attempting creation...")
                        try:
                            # Create the index. pymongo's create_index is generally idempotent
                            # based on index keys/options, but checking by name first is clearer.
                            idx_result_name = collection_handle.create_index([index_spec], **index_options)
                            created_index_names.append(idx_result_name)
                            log.info(f"    - Successfully CREATED index '{idx_result_name}' on '{coll_name}'.")
                        except OperationFailure as e:
                            log.error(f"    - PERMISSION ERROR creating index '{idx_name}' on '{coll_name}': {e.details}")
                            log.error("      Please check MongoDB user permissions for 'createIndex'.")
                        except Exception as e:
                            log.error(f"    - UNEXPECTED ERROR creating index '{idx_name}' on '{coll_name}': {e}", exc_info=True)
                    else:
                       log.debug(f"    - Index '{idx_name}' already exists on '{coll_name}'.")

                # Log summary if new indexes were actually added
                # if collection_created and created_index_names:
                #    log.info(f"    - Finished creating specified indexes for new collection '{coll_name}'.")
                # elif created_index_names: # Log if indexes were added to existing collection
                #    log.info(f"  - Finished adding new indexes to existing collection '{coll_name}'.")

            except OperationFailure as e:
                 # Error trying to get index information
                 log.error(f"  - PERMISSION ERROR accessing index info for '{coll_name}': {e.details}")
                 log.error("    Please check MongoDB user permissions for 'listIndexes'.")
            except Exception as e:
                # Catch other errors during index processing for this collection
                log.error(f"  - ERROR ensuring indexes for collection '{coll_name}': {e}", exc_info=True)

    log.info("Database initialization check complete.")


# --- Main Application Factory ---
def create_app():
    """Application Factory Function: Creates and configures the Flask app."""
    global mongo_client, db

    # Create the Flask application instance
    app = Flask(__name__)
    # Load configuration from config.py based on FLASK_ENV
    app_config = get_config()
    app.config.from_object(app_config)
    log.info(f"Flask app created. Running in '{app_config.__class__.__name__}' mode.")

    # Register context processor to make 'now' available in all templates
    @app.context_processor
    def inject_now():
        return {'now': datetime.datetime.utcnow()}

    # --- Initialize MongoDB Client and Database ---
    try:
        # Get connection parameters from Flask config (loaded from .env)
        mongo_host = app_config.MONGO_HOST
        mongo_port = app_config.MONGO_PORT
        mongo_dbname = app_config.MONGO_DBNAME
        mongo_username = app_config.MONGO_USERNAME
        mongo_password = app_config.MONGO_PASSWORD
        mongo_auth_source = app_config.MONGO_AUTHSOURCE

        # Build connection arguments dictionary
        connection_args = {
            'host': mongo_host,
            'port': mongo_port,
            'serverSelectionTimeoutMS': 5000 # Timeout for finding suitable server
            # Add other options like replicaSet, tls, etc., from config if needed
            # 'tls': app_config.MONGO_TLS,
            # 'replicaSet': app_config.MONGO_REPLICASET,
            }
        # Add authentication credentials if provided
        if mongo_username and mongo_password:
            connection_args.update({
                'username': mongo_username,
                'password': mongo_password,
                'authSource': mongo_auth_source,
                'authMechanism': 'SCRAM-SHA-256' # Default mechanism, adjust if necessary
            })
            log.info(f"Attempting MongoDB connection to {mongo_host}:{mongo_port} DB: '{mongo_dbname}' with user '{mongo_username}' (authSource: {mongo_auth_source})")
        else:
            log.info(f"Attempting MongoDB connection to {mongo_host}:{mongo_port} DB: '{mongo_dbname}' without authentication")

        # Create the MongoDB client instance
        mongo_client = MongoClient(**connection_args)

        # Verify connection by pinging the server (preferred over ismaster)
        log.info("Pinging MongoDB server to verify connection...")
        mongo_client.admin.command('ping')
        log.info("Successfully connected to MongoDB server!")

        # Get the specific database handle
        db = mongo_client[mongo_dbname]
        # Optionally make db directly available via app context (less common now with get_db())
        # app.db = db
        log.info(f"Database handle obtained for '{mongo_dbname}'.")

        # ---> Call Initialization Function Here <---
        # Ensure database structure (collections, indexes) is ready
        initialize_database(db)

    except ConnectionFailure as e:
        # Specific error for connection failures (network, server down)
        log.critical(f"Could not connect to MongoDB server at {app_config.MONGO_HOST}:{app_config.MONGO_PORT}. Is it running? Check network/firewall. Error: {e}")
        exit(1) # Stop app startup if DB connection fails
    except OperationFailure as e:
        # Specific error for authentication failures or permission issues during ping
        log.critical(f"MongoDB authentication/operation error during connection (check credentials/permissions for user '{mongo_username}' on authSource '{mongo_auth_source}'): {e.details}")
        exit(1) # Stop app startup
    except Exception as e:
        # Catch any other unexpected errors during DB setup
        log.critical(f"An unexpected error occurred during MongoDB initialization: {e}", exc_info=True) # Log traceback
        exit(1) # Stop app startup

    # --- Initialize Flask-Login ---
    login_manager.init_app(app)
    # Define the user loader function required by Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        """Loads user object from DB based on user_id stored in session."""
        # Import User model *inside* the function to avoid circular imports during startup
        from .models.user import User
        # Delegate loading to the User model's static method
        return User.get_by_id(user_id)

    # --- Register Blueprints ---
    # Import blueprint objects from their respective route files
    from .routes.auth import auth_bp
    from .routes.main import main_bp
    from .routes.employee import employee_bp
    from .routes.leave import leave_bp
    # Register blueprints with the Flask app, potentially adding URL prefixes
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp) # No prefix, routes like '/' or '/dashboard'
    app.register_blueprint(employee_bp, url_prefix='/employees')
    app.register_blueprint(leave_bp, url_prefix='/leave')
    # Register other blueprints as you create them...
    log.info("Registered application blueprints.")

    log.info("Flask app creation and configuration complete.")
    return app # Return the fully configured Flask app instance