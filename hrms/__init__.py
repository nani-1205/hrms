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

# --- Configure logging early ---
# This basic config affects the root logger. More advanced config can be done later.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
# Get a logger specifically for this module (__init__.py)
log = logging.getLogger(__name__)

# --- Initialize Flask Extensions (before app creation) ---
login_manager = LoginManager()
login_manager.login_view = 'auth.login' # Route name (blueprint.view_func) for login page
login_manager.login_message = "Please log in to access this page." # Custom message
login_manager.login_message_category = 'info' # Bootstrap category for flash message

# --- Global Variables for Database (assigned in create_app) ---
mongo_client = None
db = None

# --- Function to get the database instance ---
# Provides controlled access to the db handle after initialization
def get_db():
    """Returns the MongoDB database instance."""
    if db is None:
        log.error("get_db() called before database was initialized successfully.")
        # This indicates a startup problem or incorrect usage order
        raise RuntimeError("Database not initialized. Ensure create_app() completed successfully.")
    return db

# --- Helper function for Database Initialization (Collections & Indexes) ---
def initialize_database(db_instance):
    """
    Ensures required collections and basic indexes exist in the database.
    This function is designed to be idempotent (safe to run multiple times).
    """
    # Define required collections and their essential indexes for query performance and uniqueness
    required_collections = {
        # Collection Name: List of index definitions [ ( (key_spec), {options} ), ... ]
        "users": [
            (("username", pymongo.ASCENDING), {"unique": True, "background": True, "name": "username_uniq_idx"}),
            (("email", pymongo.ASCENDING), {"unique": True, "background": True, "name": "email_uniq_idx"}),
        ],
        "employees": [
            (("employee_code", pymongo.ASCENDING), {"unique": True, "sparse": True, "background": True, "name": "emp_code_uniq_idx"}),
            (("email", pymongo.ASCENDING), {"unique": True, "sparse": True, "background": True, "name": "emp_email_uniq_idx"}),
            (("department", pymongo.ASCENDING), {"background": True, "name": "emp_dept_idx"}), # Example non-unique index
            (("manager_id", pymongo.ASCENDING), {"sparse": True, "background": True, "name": "emp_manager_idx"}), # If storing manager refs
        ],
        "leave_requests": [
            (("user_id", pymongo.ASCENDING), {"background": True, "name": "leave_userid_idx"}),
            (("employee_id", pymongo.ASCENDING), {"sparse": True, "background": True, "name": "leave_empid_idx"}), # If linking directly to employee
            (("status", pymongo.ASCENDING), {"background": True, "name": "leave_status_idx"}),
            (("start_date", pymongo.DESCENDING), {"background": True, "name": "leave_startdate_idx"}),
            (("leave_type", pymongo.ASCENDING), {"background": True, "name": "leave_type_idx"}),
        ],
        # Add definitions for other core collections as needed during startup
        # Example:
        # "departments": [
        #    (("name", pymongo.ASCENDING), {"unique": True, "background": True, "name": "dept_name_uniq_idx"}),
        # ],
    }

    log.info(f"Checking database '{db_instance.name}' for required collections and indexes...")
    try:
        # Get list of collections actually present in the database
        existing_collections = db_instance.list_collection_names()
        log.info(f"Existing collections found: {existing_collections}")
    except OperationFailure as e:
        # User might lack permissions to even list collections
        log.error(f"PERMISSION ERROR listing collections in '{db_instance.name}': {e.details}")
        log.error("Please verify MongoDB user permissions for 'listCollections'. Initialization cannot proceed.")
        return # Stop if we can't even check
    except Exception as e:
        log.error(f"Unexpected error listing collections in '{db_instance.name}': {e}", exc_info=True)
        return # Stop on unexpected errors

    # Iterate through the collections defined as required
    for coll_name, indexes_to_ensure in required_collections.items():
        collection_created = False
        collection_handle = None # Initialize handle

        # --- Ensure Collection Exists ---
        if coll_name not in existing_collections:
            log.info(f"  - Collection '{coll_name}' not found. Attempting creation...")
            try:
                # Explicitly create the collection
                collection_handle = db_instance.create_collection(coll_name)
                log.info(f"  - Successfully CREATED collection: '{coll_name}'")
                collection_created = True
            except CollectionInvalid:
                # Rare case: collection created between list_collection_names and create_collection
                log.warning(f"  - Collection '{coll_name}' already existed or was created concurrently.")
                collection_handle = db_instance[coll_name] # Get handle
            except OperationFailure as e:
                # Log specific permission errors for creating collections
                log.error(f"  - PERMISSION ERROR creating collection '{coll_name}': {e.details}")
                log.error("    Please verify MongoDB user permissions for 'createCollection'.")
                continue # Skip index creation for this collection if creation failed
            except Exception as e:
                log.error(f"  - UNEXPECTED ERROR creating collection '{coll_name}': {e}", exc_info=True)
                continue # Skip index creation
        else:
             # If collection already exists, just get a handle to it
             log.debug(f"  - Collection '{coll_name}' already exists.")
             collection_handle = db_instance[coll_name]

        # --- Ensure Indexes Exist ---
        # Proceed only if we successfully got a collection handle AND indexes are defined for it
        # ---> Corrected Check <---
        if collection_handle is not None and indexes_to_ensure:
        # ------------------------
            created_index_names = []
            log.debug(f"  - Ensuring indexes for collection '{coll_name}'...")
            try:
                # Get info about indexes currently on the collection in the DB
                existing_index_info = collection_handle.index_information()
                existing_index_names = list(existing_index_info.keys())
                log.debug(f"    Existing indexes on '{coll_name}': {existing_index_names}")

                # Iterate through indexes defined as required for this collection
                for index_spec, index_options in indexes_to_ensure:
                    # Ensure background=True for non-blocking builds unless explicitly False
                    if index_options.get("background") is not False:
                        index_options["background"] = True

                    # Ensure the index has a name for easier identification and checking
                    if "name" not in index_options:
                         # Generate a default name based on keys if none provided
                         index_options["name"] = "_".join([f"{k}_{str(v)}" for k, v in index_spec]) + "_idx"
                    idx_name = index_options["name"]

                    # Check if an index with this *name* already exists
                    if idx_name not in existing_index_names:
                        log.info(f"    - Index '{idx_name}' not found on '{coll_name}'. Attempting creation...")
                        try:
                            # Create the index. create_index is generally idempotent based on keys/options,
                            # but checking/creating by name is often clearer and safer.
                            idx_result_name = collection_handle.create_index([index_spec], **index_options)
                            created_index_names.append(idx_result_name)
                            log.info(f"    - Successfully CREATED index '{idx_result_name}' on '{coll_name}'.")
                        except OperationFailure as e:
                            log.error(f"    - PERMISSION ERROR creating index '{idx_name}' on '{coll_name}': {e.details}")
                            log.error("      Please verify MongoDB user permissions for 'createIndex'.")
                        except Exception as e:
                            log.error(f"    - UNEXPECTED ERROR creating index '{idx_name}' on '{coll_name}': {e}", exc_info=True)
                    else:
                       log.debug(f"    - Index '{idx_name}' already exists on '{coll_name}'. Skipping creation.")

            except OperationFailure as e:
                 # Error trying to get index information
                 log.error(f"  - PERMISSION ERROR accessing index info for '{coll_name}': {e.details}")
                 log.error("    Please verify MongoDB user permissions for 'listIndexes'.")
            except Exception as e:
                # Catch other errors during index processing for this collection
                log.error(f"  - ERROR ensuring indexes for collection '{coll_name}': {e}", exc_info=True)

    log.info("Database initialization check complete.")


# --- Main Application Factory ---
def create_app():
    """Application Factory Function: Creates and configures the Flask app."""
    global mongo_client, db # Declare intent to modify globals

    # Create the Flask application instance
    app = Flask(__name__, instance_relative_config=False) # Standard setup

    # Load configuration from config.py using the factory function
    app_config = get_config()
    app.config.from_object(app_config)

    # Use logger instance defined above
    log.info(f"Flask app created. Running in '{app_config.__class__.__name__}' configuration.")

    # Register context processor to make 'now' available in all templates
    @app.context_processor
    def inject_now():
        """Injects the current UTC datetime into template context."""
        return {'now': datetime.datetime.utcnow()}

    # --- Initialize MongoDB Client and Database Connection ---
    try:
        # Get connection parameters from Flask config (loaded from .env)
        mongo_host = app.config['MONGO_HOST']
        mongo_port = app.config['MONGO_PORT']
        mongo_dbname = app.config['MONGO_DBNAME']
        mongo_username = app.config.get('MONGO_USERNAME') # Use .get for optional keys
        mongo_password = app.config.get('MONGO_PASSWORD')
        mongo_auth_source = app.config.get('MONGO_AUTHSOURCE', 'admin') # Default if not set

        # Build connection arguments dictionary
        connection_args = {
            'host': mongo_host,
            'port': mongo_port,
            'serverSelectionTimeoutMS': 5000, # Timeout for finding a suitable server
            'connectTimeoutMS': 5000,        # Timeout for establishing connection
            'socketTimeoutMS': 10000,        # Timeout for socket operations
            'retryWrites': True              # Recommended for replica sets/Atlas
            # Add other options like replicaSet, tls, etc., from config if needed
            # 'tls': app.config.get('MONGO_TLS', False),
            # 'replicaSet': app.config.get('MONGO_REPLICASET'),
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

        # Verify connection by pinging the server's primary node
        log.info("Pinging MongoDB server primary to verify connection...")
        mongo_client.admin.command('ping')
        log.info("Successfully connected to MongoDB server!")

        # Get the specific database handle and assign to global 'db'
        db = mongo_client[mongo_dbname]
        # Optionally make db directly available via app context (less common now with get_db())
        # app.db = db
        log.info(f"Database handle obtained for '{mongo_dbname}'.")

        # ---> Call Initialization Function Here <---
        # Ensure database structure (collections, indexes) is ready AFTER connection
        initialize_database(db)

    except ConnectionFailure as e:
        # Specific error for connection failures (network, server down, DNS issues)
        log.critical(f"Could not connect to MongoDB server at {app_config.MONGO_HOST}:{app_config.MONGO_PORT}. Is it running? Check network/firewall/DNS. Error details: {e}")
        exit(1) # Stop app startup if DB connection fails
    except OperationFailure as e:
        # Specific error for authentication failures or permission issues during ping/connection
        log.critical(f"MongoDB authentication/operation error during connection (verify credentials/permissions for user '{mongo_username}' on authSource '{mongo_auth_source}'): {e.details}")
        exit(1) # Stop app startup
    except Exception as e:
        # Catch any other unexpected errors during DB setup
        log.critical(f"An unexpected error occurred during MongoDB initialization: {e}", exc_info=True) # Log traceback
        exit(1) # Stop app startup

    # --- Initialize Flask-Login (after successful DB connection) ---
    login_manager.init_app(app)
    # Define the user loader function required by Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        """Loads user object from DB based on user_id stored in session."""
        # Import User model *inside* the function to avoid circular imports during startup
        from .models.user import User
        # Delegate loading to the User model's static method
        log.debug(f"Flask-Login: Loading user with ID: {user_id}")
        user = User.get_by_id(user_id)
        if not user:
             log.warning(f"Flask-Login: User ID {user_id} not found in database.")
        return user

    # --- Register Blueprints ---
    log.info("Registering application blueprints...")
    # Import blueprint objects from their respective route files
    # Existing Core Modules
    from .routes.auth import auth_bp
    from .routes.main import main_bp
    from .routes.employee import employee_bp
    from .routes.leave import leave_bp
    # Placeholder Modules
    from .routes.onboarding import onboarding_bp
    from .routes.attendance import attendance_bp
    from .routes.payroll import payroll_bp
    from .routes.compensation import compensation_bp
    from .routes.documents import documents_bp
    from .routes.training import training_bp
    from .routes.workforce import workforce_bp
    from .routes.talent import talent_bp
    from .routes.ess import ess_bp
    from .routes.analytics import analytics_bp
    from .routes.benefits import benefits_bp
    from .routes.performance import performance_bp
    from .routes.recruitment import recruitment_bp
    from .routes.compliance import compliance_bp
    from .routes.succession import succession_bp
    from .routes.workflow import workflow_bp

    # Register blueprints with the Flask app, assigning URL prefixes
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp) # No prefix for main routes like '/'
    app.register_blueprint(employee_bp, url_prefix='/employees')
    app.register_blueprint(leave_bp, url_prefix='/leave')
    # Placeholders
    app.register_blueprint(onboarding_bp, url_prefix='/onboarding')
    app.register_blueprint(attendance_bp, url_prefix='/attendance')
    app.register_blueprint(payroll_bp, url_prefix='/payroll')
    app.register_blueprint(compensation_bp, url_prefix='/compensation')
    app.register_blueprint(documents_bp, url_prefix='/documents')
    app.register_blueprint(training_bp, url_prefix='/training')
    app.register_blueprint(workforce_bp, url_prefix='/workforce')
    app.register_blueprint(talent_bp, url_prefix='/talent')
    app.register_blueprint(ess_bp, url_prefix='/ess') # Employee Self Service
    app.register_blueprint(analytics_bp, url_prefix='/analytics')
    app.register_blueprint(benefits_bp, url_prefix='/benefits')
    app.register_blueprint(performance_bp, url_prefix='/performance')
    app.register_blueprint(recruitment_bp, url_prefix='/recruitment')
    app.register_blueprint(compliance_bp, url_prefix='/compliance')
    app.register_blueprint(succession_bp, url_prefix='/succession')
    app.register_blueprint(workflow_bp, url_prefix='/workflow')
    # Register other blueprints as you create them...

    log.info("Registered all application blueprints.")
    log.info("Flask app creation and configuration complete. Ready to serve requests.")
    return app # Return the fully configured Flask app instance