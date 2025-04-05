# hrms/config.py
import os
from dotenv import load_dotenv
import logging

log = logging.getLogger(__name__)

# Construct the path to the .env file relative to this config file's location
# Assumes config.py is in 'hrms/' and .env is in the parent directory 'hrms_project/'
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')

if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
    log.debug(f"Loaded environment variables from: {dotenv_path}")
else:
    # Use print here as logging might not be fully configured yet during import
    print(f"Warning: .env file not found at expected location: {dotenv_path}. Using system environment variables or defaults.")

class Config:
    """Base configuration settings."""
    # Secret key for session management, CSRF protection, etc.
    # IMPORTANT: Should be overridden by environment variable in production.
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a_very_default_unsafe_secret_key_for_dev_only'

    # MongoDB Configuration
    MONGO_HOST = os.environ.get('MONGO_HOST', 'localhost')
    MONGO_PORT = int(os.environ.get('MONGO_PORT', 27017)) # Ensure port is integer
    MONGO_DBNAME = os.environ.get('MONGO_DBNAME', 'hrms_db')
    MONGO_USERNAME = os.environ.get('MONGO_USERNAME') # Returns None if not set
    MONGO_PASSWORD = os.environ.get('MONGO_PASSWORD') # Returns None if not set
    MONGO_AUTHSOURCE = os.environ.get('MONGO_AUTHSOURCE', 'admin') # Common default

    # Application settings (Examples)
    # Control if self-registration is allowed via the /auth/register route
    ALLOW_SELF_REGISTRATION = os.environ.get('ALLOW_SELF_REGISTRATION', 'True').lower() in ('true', '1', 't')
    # Add other configurations like mail server settings, external API keys etc.
    # MAIL_SERVER = os.environ.get('MAIL_SERVER')
    # MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    # MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ('true', '1', 't')
    # MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    # MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    # MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')


class DevelopmentConfig(Config):
    """Development-specific configuration."""
    DEBUG = True
    # Add any development overrides, e.g., database name suffix
    # MONGO_DBNAME = Config.MONGO_DBNAME + '_dev'


class ProductionConfig(Config):
    """Production-specific configuration."""
    DEBUG = False
    # Ensure SECRET_KEY is definitely set from environment in production
    if Config.SECRET_KEY == 'a_very_default_unsafe_secret_key_for_dev_only':
        print("CRITICAL SECURITY WARNING: Default SECRET_KEY is being used in ProductionConfig. Set a strong SECRET_KEY environment variable.")
        # Consider raising an exception here to prevent startup with default key
        # raise ValueError("Missing or insecure SECRET_KEY in production environment.")

    # Add other production settings:
    # - More robust logging configuration
    # - Different database connection string/credentials if needed
    # - Caching configuration


class TestingConfig(Config):
    """Testing-specific configuration."""
    TESTING = True
    DEBUG = True # Often helpful during testing
    # Use a separate database for testing to avoid affecting dev/prod data
    MONGO_DBNAME = Config.MONGO_DBNAME + '_test'
    # Disable CSRF protection for easier testing of form submissions (use with caution)
    # WTF_CSRF_ENABLED = False
    # Make login easier/faster during tests
    # LOGIN_DISABLED = True # Be careful with this


# Dictionary mapping environment names to config classes
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig # Fallback if FLASK_ENV is not set or unrecognized
}

def get_config():
    """Factory function to get the configuration instance based on FLASK_ENV."""
    env_name = os.getenv('FLASK_ENV', 'default').lower()
    config_class = config_by_name.get(env_name, config_by_name['default'])
    # print(f"Loading configuration: {config_class.__name__}") # Use print before logging might be ready
    return config_class()