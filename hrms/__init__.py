# hrms/__init__.py

import os
import datetime
import pymongo
from pymongo import MongoClient
from pymongo.errors import CollectionInvalid, ConnectionFailure, OperationFailure
from flask import Flask
from flask_login import LoginManager
from .config import get_config
from .utils import format_date, format_datetime # Import specific filters
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger(__name__)

# Initialize Extensions
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = 'info'

# Global DB variables
mongo_client = None
db = None

def get_db():
    """Returns the MongoDB database instance."""
    if db is None:
        log.error("get_db() called before database was initialized successfully.")
        raise RuntimeError("Database not initialized. Ensure create_app() completed successfully.")
    return db

def initialize_database(db_instance):
    """Ensures required collections and basic indexes exist."""
    required_collections = {
        "users": [
            (("username", pymongo.ASCENDING), {"unique": True, "background": True, "name": "username_uniq_idx"}),
            (("email", pymongo.ASCENDING), {"unique": True, "background": True, "name": "email_uniq_idx"}),
        ],
        "employees": [
            (("employee_code", pymongo.ASCENDING), {"unique": True, "sparse": True, "background": True, "name": "emp_code_uniq_idx"}),
            (("email", pymongo.ASCENDING), {"unique": True, "sparse": True, "background": True, "name": "emp_email_uniq_idx"}),
            (("department", pymongo.ASCENDING), {"background": True, "name": "emp_dept_idx"}),
            (("manager_id", pymongo.ASCENDING), {"sparse": True, "background": True, "name": "emp_manager_idx"}),
        ],
        "leave_requests": [
            (("user_id", pymongo.ASCENDING), {"background": True, "name": "leave_userid_idx"}),
            (("employee_id", pymongo.ASCENDING), {"sparse": True, "background": True, "name": "leave_empid_idx"}),
            (("status", pymongo.ASCENDING), {"background": True, "name": "leave_status_idx"}),
            (("start_date", pymongo.DESCENDING), {"background": True, "name": "leave_startdate_idx"}),
            (("leave_type", pymongo.ASCENDING), {"background": True, "name": "leave_type_idx"}),
        ],
    }

    log.info(f"Checking database '{db_instance.name}' for required collections and indexes...")
    try:
        existing_collections = db_instance.list_collection_names()
        log.info(f"Existing collections found: {existing_collections}")
    except OperationFailure as e:
        log.error(f"PERMISSION ERROR listing collections in '{db_instance.name}': {e.details}")
        log.error("Please verify MongoDB user permissions for 'listCollections'. Initialization cannot proceed.")
        return
    except Exception as e:
        log.error(f"Unexpected error listing collections in '{db_instance.name}': {e}", exc_info=True)
        return

    for coll_name, indexes_to_ensure in required_collections.items():
        collection_created = False
        collection_handle = None

        if coll_name not in existing_collections:
            log.info(f"  - Collection '{coll_name}' not found. Attempting creation...")
            try:
                collection_handle = db_instance.create_collection(coll_name)
                log.info(f"  - Successfully CREATED collection: '{coll_name}'")
                collection_created = True
            except CollectionInvalid:
                log.warning(f"  - Collection '{coll_name}' already existed or was created concurrently.")
                collection_handle = db_instance[coll_name]
            except OperationFailure as e:
                log.error(f"  - PERMISSION ERROR creating collection '{coll_name}': {e.details}")
                log.error("    Please verify MongoDB user permissions for 'createCollection'.")
                continue
            except Exception as e:
                log.error(f"  - UNEXPECTED ERROR creating collection '{coll_name}': {e}", exc_info=True)
                continue
        else:
             log.debug(f"  - Collection '{coll_name}' already exists.")
             collection_handle = db_instance[coll_name]

        if collection_handle is not None and indexes_to_ensure:
            created_index_names = []
            log.debug(f"  - Ensuring indexes for collection '{coll_name}'...")
            try:
                existing_index_info = collection_handle.index_information()
                existing_index_names = list(existing_index_info.keys())
                log.debug(f"    Existing indexes on '{coll_name}': {existing_index_names}")

                for index_spec, index_options in indexes_to_ensure:
                    if index_options.get("background") is not False: index_options["background"] = True
                    if "name" not in index_options: index_options["name"] = "_".join([f"{k}_{str(v)}" for k, v in index_spec]) + "_idx"
                    idx_name = index_options["name"]

                    if idx_name not in existing_index_names:
                        log.info(f"    - Index '{idx_name}' not found on '{coll_name}'. Attempting creation...")
                        try:
                            idx_result_name = collection_handle.create_index([index_spec], **index_options)
                            created_index_names.append(idx_result_name)
                            log.info(f"    - Successfully CREATED index '{idx_result_name}' on '{coll_name}'.")
                        except OperationFailure as e: log.error(f"    - PERMISSION ERROR creating index '{idx_name}' on '{coll_name}': {e.details}"); log.error("      Please verify MongoDB user permissions for 'createIndex'.")
                        except Exception as e: log.error(f"    - UNEXPECTED ERROR creating index '{idx_name}' on '{coll_name}': {e}", exc_info=True)
                    # else: # Optional log if index exists
                        # log.debug(f"    - Index '{idx_name}' already exists on '{coll_name}'. Skipping creation.")

            except OperationFailure as e: log.error(f"  - PERMISSION ERROR accessing index info for '{coll_name}': {e.details}"); log.error("    Please verify MongoDB user permissions for 'listIndexes'.")
            except Exception as e: log.error(f"  - ERROR ensuring indexes for collection '{coll_name}': {e}", exc_info=True)

    log.info("Database initialization check complete.")

def create_app():
    """Application Factory Function: Creates and configures the Flask app."""
    global mongo_client, db

    app = Flask(__name__, instance_relative_config=False)
    app_config = get_config()
    app.config.from_object(app_config)
    log.info(f"Flask app created. Running in '{app_config.__class__.__name__}' configuration.")

    @app.context_processor
    def inject_now():
        return {'now': datetime.datetime.utcnow()}

    # --- Register Jinja Filters --- # <--- ADDED FILTER REGISTRATION ---
    app.jinja_env.filters['format_date'] = format_date
    app.jinja_env.filters['format_datetime'] = format_datetime
    log.info("Registered custom Jinja filters (format_date, format_datetime).")
    # ---------------------------------------------------------------------

    # --- Initialize MongoDB ---
    try:
        mongo_host = app.config['MONGO_HOST']
        mongo_port = app.config['MONGO_PORT']
        mongo_dbname = app.config['MONGO_DBNAME']
        mongo_username = app.config.get('MONGO_USERNAME')
        mongo_password = app.config.get('MONGO_PASSWORD')
        mongo_auth_source = app.config.get('MONGO_AUTHSOURCE', 'admin')

        connection_args = {
            'host': mongo_host, 'port': mongo_port, 'serverSelectionTimeoutMS': 5000,
            'connectTimeoutMS': 5000, 'socketTimeoutMS': 10000, 'retryWrites': True
            }
        if mongo_username and mongo_password:
            connection_args.update({
                'username': mongo_username, 'password': mongo_password,
                'authSource': mongo_auth_source, 'authMechanism': 'SCRAM-SHA-256'
            })
            log.info(f"Attempting MongoDB connection to {mongo_host}:{mongo_port} DB: '{mongo_dbname}' with user '{mongo_username}' (authSource: {mongo_auth_source})")
        else:
            log.info(f"Attempting MongoDB connection to {mongo_host}:{mongo_port} DB: '{mongo_dbname}' without authentication")

        mongo_client = MongoClient(**connection_args)
        log.info("Pinging MongoDB server primary to verify connection...")
        mongo_client.admin.command('ping')
        log.info("Successfully connected to MongoDB server!")
        db = mongo_client[mongo_dbname]
        log.info(f"Database handle obtained for '{mongo_dbname}'.")
        initialize_database(db)

    except ConnectionFailure as e: log.critical(f"Could not connect to MongoDB: {e}"); exit(1)
    except OperationFailure as e: log.critical(f"MongoDB authentication/operation error: {e.details}"); exit(1)
    except Exception as e: log.critical(f"Unexpected error during MongoDB init: {e}", exc_info=True); exit(1)

    # --- Initialize Flask-Login ---
    login_manager.init_app(app)
    @login_manager.user_loader
    def load_user(user_id):
        from .models.user import User
        log.debug(f"Flask-Login: Loading user with ID: {user_id}")
        user = User.get_by_id(user_id)
        if not user: log.warning(f"Flask-Login: User ID {user_id} not found.")
        return user

    # --- Register Blueprints ---
    log.info("Registering application blueprints...")
    from .routes.auth import auth_bp
    from .routes.main import main_bp
    from .routes.employee import employee_bp
    from .routes.leave import leave_bp
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

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)
    app.register_blueprint(employee_bp, url_prefix='/employees')
    app.register_blueprint(leave_bp, url_prefix='/leave')
    app.register_blueprint(onboarding_bp, url_prefix='/onboarding')
    app.register_blueprint(attendance_bp, url_prefix='/attendance')
    app.register_blueprint(payroll_bp, url_prefix='/payroll')
    app.register_blueprint(compensation_bp, url_prefix='/compensation')
    app.register_blueprint(documents_bp, url_prefix='/documents')
    app.register_blueprint(training_bp, url_prefix='/training')
    app.register_blueprint(workforce_bp, url_prefix='/workforce')
    app.register_blueprint(talent_bp, url_prefix='/talent')
    app.register_blueprint(ess_bp, url_prefix='/ess')
    app.register_blueprint(analytics_bp, url_prefix='/analytics')
    app.register_blueprint(benefits_bp, url_prefix='/benefits')
    app.register_blueprint(performance_bp, url_prefix='/performance')
    app.register_blueprint(recruitment_bp, url_prefix='/recruitment')
    app.register_blueprint(compliance_bp, url_prefix='/compliance')
    app.register_blueprint(succession_bp, url_prefix='/succession')
    app.register_blueprint(workflow_bp, url_prefix='/workflow')

    log.info("Registered all application blueprints.")
    log.info("Flask app creation and configuration complete. Ready to serve requests.")
    return app