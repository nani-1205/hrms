# hrms/__init__.py

import os
import datetime
import pymongo
from pymongo import MongoClient
# Import more specific errors if needed
from pymongo.errors import CollectionInvalid, ConnectionFailure, OperationFailure
from flask_login import LoginManager
from .config import get_config
import logging # Import Python's logging module

# --- Configure logging ---
# Basic configuration - adjust level and format as needed
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__) # Get a logger instance

# ... (rest of imports, extensions, get_db) ...
# def get_db(): ...


# --- Helper function for initialization ---
def initialize_database(db_instance):
    """
    Ensures required collections and basic indexes exist.
    """
    required_collections = {
        "users": [
            (("username", pymongo.ASCENDING), {"unique": True, "background": True}),
            (("email", pymongo.ASCENDING), {"unique": True, "background": True}),
        ],
        "employees": [
            (("employee_code", pymongo.ASCENDING), {"unique": True, "sparse": True, "background": True}),
            (("email", pymongo.ASCENDING), {"unique": True, "sparse": True, "background": True}),
            (("department", pymongo.ASCENDING), {"background": True}),
        ],
        "leave_requests": [
            (("user_id", pymongo.ASCENDING), {"background": True}),
            (("status", pymongo.ASCENDING), {"background": True}),
            (("start_date", pymongo.DESCENDING), {"background": True}),
        ],
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
        log.error(f"Unexpected error listing collections in '{db_instance.name}': {e}")
        return

    for coll_name, indexes in required_collections.items():
        collection_created = False
        if coll_name not in existing_collections:
            try:
                db_instance.create_collection(coll_name)
                log.info(f"  - Successfully CREATED collection: '{coll_name}'")
                collection_created = True
            except CollectionInvalid:
                log.warning(f"  - Collection '{coll_name}' already exists (or created concurrently).")
            except OperationFailure as e:
                # Log permission errors specifically
                log.error(f"  - PERMISSION ERROR creating collection '{coll_name}': {e.details}")
                log.error("    Please check MongoDB user permissions for 'createCollection'.")
                continue # Skip index creation if collection creation failed
            except Exception as e:
                log.error(f"  - UNEXPECTED ERROR creating collection '{coll_name}': {e}")
                continue

        # --- Create Indexes ---
        if indexes:
            try:
                collection = db_instance[coll_name]
                created_index_names = []
                for index_spec, index_options in indexes:
                    if "background" not in index_options:
                        index_options["background"] = True
                    # Generate a name for logging/debugging if not provided
                    index_name = index_options.get("name", "_".join([f"{k}_{v}" for k, v in index_spec]) + "_idx")
                    index_options["name"] = index_name # Ensure name is set for potential errors

                    try:
                         # Check if index exists before creating (optional, create_index is idempotent)
                         # if index_name not in collection.index_information():
                        idx_result_name = collection.create_index([index_spec], **index_options)
                        created_index_names.append(idx_result_name)
                         # else:
                         #    log.debug(f"    - Index '{index_name}' already exists for '{coll_name}'.")

                    except OperationFailure as e:
                         log.error(f"    - PERMISSION ERROR creating index '{index_name}' on '{coll_name}': {e.details}")
                         log.error("      Please check MongoDB user permissions for 'createIndex'.")
                    except Exception as e:
                         log.error(f"    - UNEXPECTED ERROR creating index '{index_name}' on '{coll_name}': {e}")

                if created_index_names:
                    if collection_created:
                         log.info(f"    - Created specified indexes for new collection '{coll_name}': {created_index_names}")
                    else:
                         log.info(f"  - Ensured specified indexes exist for '{coll_name}'. Created/verified: {created_index_names}")

            except Exception as e:
                # Catch errors getting the collection handle itself
                log.error(f"  - ERROR accessing collection '{coll_name}' for index creation: {e}")

    log.info("Database initialization check complete.")


# --- Main Application Factory ---
def create_app():
    """Application Factory Function"""
    global mongo_client, db

    app = Flask(__name__)
    app_config = get_config()
    app.config.from_object(app_config)

    # Context Processor
    @app.context_processor
    def inject_now():
        return {'now': datetime.datetime.utcnow()}

    # --- Initialize MongoDB Client and Database ---
    try:
        # ... (rest of connection logic remains the same) ...
        mongo_host = app_config.MONGO_HOST
        # ... etc ...
        mongo_client = MongoClient(**connection_args, serverSelectionTimeoutMS=5000)
        log.info("Pinging MongoDB server...") # Added log
        mongo_client.admin.command('ping')
        log.info("Successfully connected to MongoDB server!") # Changed print to log
        db = mongo_client[mongo_dbname]
        app.db = db
        log.info(f"Database handle obtained for '{mongo_dbname}'.") # Added log

        # ---> Call Initialization Function Here <---
        initialize_database(db)

    except ConnectionFailure as e:
        log.critical(f"Could not connect to MongoDB server at {app_config.MONGO_HOST}:{app_config.MONGO_PORT}. Error: {e}") # Changed print to log
        exit(1)
    except OperationFailure as e: # Catch auth errors during initial connection/ping
        log.critical(f"MongoDB operation error during connection (check credentials/permissions): {e.details}")
        exit(1)
    except Exception as e:
        log.critical(f"An unexpected error occurred during MongoDB initialization: {e}", exc_info=True) # Added exc_info for traceback
        exit(1)

    # --- Initialize Flask-Login ---
    # ... (Flask-Login setup) ...

    # --- Register Blueprints ---
    # ... (Blueprint registration) ...

    log.info("Flask app created and configured successfully.") # Changed print to log
    return app

# ... (rest of file, if any) ...