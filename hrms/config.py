# hrms/config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a_default_fallback_secret_key'

    # MongoDB Configuration from individual variables
    MONGO_HOST = os.environ.get('MONGO_HOST', 'localhost')
    MONGO_PORT = int(os.environ.get('MONGO_PORT', 27017)) # Ensure port is an integer
    MONGO_DBNAME = os.environ.get('MONGO_DBNAME', 'hrms_db')
    MONGO_USERNAME = os.environ.get('MONGO_USERNAME') # Returns None if not set
    MONGO_PASSWORD = os.environ.get('MONGO_PASSWORD') # Returns None if not set
    MONGO_AUTHSOURCE = os.environ.get('MONGO_AUTHSOURCE', 'admin') # Default to 'admin' is common

    # You might add other configs here later
    # e.g., ALLOW_REGISTRATION = os.environ.get('ALLOW_REGISTRATION', 'False').lower() in ('true', '1', 't')


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    # Add development-specific settings if needed


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    # Ensure SECRET_KEY is set securely in production environment
    if Config.SECRET_KEY == 'a_default_fallback_secret_key':
        # You might want to raise an error or log a critical warning in production
        # if a proper secret key isn't set via environment variables.
        print("WARNING: Using default SECRET_KEY in production is insecure!")
    # Add production-specific settings


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config():
    env = os.getenv('FLASK_ENV', 'default')
    return config[env]()