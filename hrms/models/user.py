# hrms/models/user.py

from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from bson import ObjectId
from .. import get_db # Use the get_db function from hrms/__init__.py
import logging

# Get a logger instance for this module
log = logging.getLogger(__name__)

class User(UserMixin):
    def __init__(self, username, email, password_hash=None, role='employee', _id=None, is_active=True):
        """Initializes a User object."""
        # Ensure ID is stored as string for Flask-Login compatibility
        self.id = str(_id) if _id else None
        self.username = username
        self.email = email # Expecting already lowercased email from route
        self.password_hash = password_hash
        self.role = role # e.g., 'employee', 'manager', 'hr', 'admin'
        self.is_active = is_active # For Flask-Login

    def set_password(self, password):
        """Hashes the provided password and stores it."""
        if password:
            self.password_hash = generate_password_hash(password)
        else:
            # Handle case where password might be empty if needed
            self.password_hash = None

    def check_password(self, password):
        """Checks if the provided password matches the stored hash."""
        if not self.password_hash or not password:
            return False
        return check_password_hash(self.password_hash, password)

    # --- Database Methods ---
    @staticmethod
    def get_collection():
        """Gets the MongoDB collection for users."""
        try:
            db = get_db()
            return db.users
        except Exception as e:
            log.critical(f"Failed to get database handle in User model: {e}", exc_info=True)
            # Depending on desired behavior, you might raise the error
            # or return None and handle it in calling methods.
            raise RuntimeError("Could not get database handle.") from e


    def save(self):
        """
        Saves the current user object to the database (inserts or updates).
        Returns the user's ID string upon successful save/update, otherwise None.
        """
        try:
            users_collection = User.get_collection()
            user_data = {
                'username': self.username,
                'email': self.email, # Assumes already lowercase
                'password_hash': self.password_hash,
                'role': self.role,
                'is_active': self.is_active
            }

            if self.id: # Update existing user if self.id is set
                 log.debug(f"Attempting to update user with ID: {self.id}")
                 update_result = users_collection.update_one(
                     {'_id': ObjectId(self.id)},
                     {'$set': user_data}
                 )
                 if update_result.matched_count == 0:
                     log.warning(f"Attempted to update user ID {self.id}, but no document matched.")
                     return None # Or maybe return self.id, depending on desired logic
                 log.info(f"Updated user '{self.username}' (ID: {self.id}). Modified count: {update_result.modified_count}")
                 # Return the ID even if modified_count is 0 (if only matched)
                 return self.id
            else: # Insert new user
                log.debug(f"Attempting to insert new user: {self.username}")
                # Ensure required fields are present before inserting
                if not self.username or not self.email or not self.password_hash:
                     log.error(f"Attempted to insert user with missing fields: username='{self.username}', email='{self.email}', hash_present={bool(self.password_hash)}")
                     return None

                insert_result = users_collection.insert_one(user_data)
                new_id = str(insert_result.inserted_id)
                log.info(f"Inserted new user '{self.username}' with ID: {new_id}")
                # ---> Return the new ID as a string <---
                return new_id
        except pymongo.errors.DuplicateKeyError as e:
             log.error(f"Failed to save user '{self.username}': Duplicate key error. Details: {e.details}")
             # This usually means username or email unique index was violated
             return None
        except Exception as e:
            # Log the full error with traceback for debugging
            log.error(f"Error during User.save for user '{self.username}': {e}", exc_info=True)
            return None # Indicate failure


    @staticmethod
    def get_by_id(user_id):
        """Finds a user by their MongoDB ObjectId string."""
        if not user_id: return None
        try:
            user_data = User.get_collection().find_one({'_id': ObjectId(user_id)})
            if user_data:
                return User(
                    _id=user_data['_id'], # Pass the ObjectId itself
                    username=user_data.get('username'),
                    email=user_data.get('email'),
                    password_hash=user_data.get('password_hash'), # Use .get for safety
                    role=user_data.get('role', 'employee'), # Provide default
                    is_active=user_data.get('is_active', True) # Provide default
                )
        except bson.errors.InvalidId:
            log.warning(f"Invalid ObjectId format passed to get_by_id: '{user_id}'")
        except Exception as e:
            log.error(f"Error in get_by_id for ID '{user_id}': {e}", exc_info=True)
        return None


    @staticmethod
    def get_by_username(username):
        """Finds a user by their username (case-sensitive)."""
        if not username: return None
        try:
            # Consider case-insensitive search if desired:
            # user_data = User.get_collection().find_one({'username': {'$regex': f'^{re.escape(username)}$', '$options': 'i'}})
            user_data = User.get_collection().find_one({'username': username})
            if user_data:
                return User(
                    _id=user_data['_id'],
                    username=user_data.get('username'),
                    email=user_data.get('email'),
                    password_hash=user_data.get('password_hash'),
                    role=user_data.get('role', 'employee'),
                    is_active=user_data.get('is_active', True)
                )
        except Exception as e:
            log.error(f"Error in get_by_username for username '{username}': {e}", exc_info=True)
        return None


    @staticmethod
    def get_by_email(email):
        """Finds a user by their email (case-insensitive)."""
        if not email: return None
        try:
            # Searches using the lowercased email
            user_data = User.get_collection().find_one({'email': email.lower()})
            if user_data:
                 return User(
                    _id=user_data['_id'],
                    username=user_data.get('username'),
                    email=user_data.get('email'), # Return stored email
                    password_hash=user_data.get('password_hash'),
                    role=user_data.get('role', 'employee'),
                    is_active=user_data.get('is_active', True)
                )
        except Exception as e:
            log.error(f"Error in get_by_email for email '{email}': {e}", exc_info=True)
        return None


    # --- Flask-Login required properties/methods ---
    # These are mostly handled by UserMixin or simple implementations

    @property
    def is_authenticated(self):
        """Required for Flask-Login. Returns True if the user is considered authenticated."""
        return True # Generally True if the object exists and represents a real user

    # is_active is already a property defined in __init__

    @property
    def is_anonymous(self):
        """Required for Flask-Login. Returns True if this is an anonymous user."""
        return False # Real users are not anonymous

    def get_id(self):
        """Required for Flask-Login. Returns a **unicode** string representing the user ID."""
        return str(self.id) # Ensure it's always a string


    def __repr__(self):
        """String representation of the User object."""
        return f'<User id={self.id} username={self.username}>'