# hrms/models/user.py

from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from bson import ObjectId, errors as bson_errors # Import bson errors specifically
from pymongo import errors as pymongo_errors # Import pymongo errors specifically
from .. import get_db # Use the get_db function from hrms/__init__.py
import logging
# import re # Import if using regex for searches later

# Get a logger instance specifically for this module
log = logging.getLogger(__name__)

class User(UserMixin):
    """
    Represents a user in the HRMS system.
    Includes methods for password management, database interaction,
    and properties required by Flask-Login.
    """

    def __init__(self, username, email, password_hash=None, role='employee', _id=None, is_active=True):
        """
        Initializes a User object.

        Args:
            username (str): The user's chosen username.
            email (str): The user's email address (should be lowercased).
            password_hash (str, optional): The pre-hashed password. Defaults to None.
            role (str, optional): The user's role (e.g., 'employee', 'admin'). Defaults to 'employee'.
            _id (ObjectId, optional): The MongoDB ObjectId if loading an existing user. Defaults to None.
            is_active (bool, optional): Whether the user account is active. Defaults to True.
                                         This value initializes the internal state.
        """
        # Ensure ID is stored as string for Flask-Login compatibility
        self.id = str(_id) if _id else None
        self.username = username
        self.email = email # Expecting already lowercased email from route logic
        self.password_hash = password_hash
        self.role = role

        # ---> Store the active state in an internal attribute <---
        # The 'is_active' property (defined below) will use this.
        # This avoids conflict with the UserMixin property during initialization.
        self._is_active = bool(is_active) # Ensure it's stored as a boolean

    # --- Flask-Login required property: is_active ---
    # This property reads the internal state (_is_active).
    # UserMixin might provide a default, but defining it explicitly ensures our logic is used.
    @property
    def is_active(self):
        """Required by Flask-Login. Returns True if the user account is active."""
        return self._is_active
    # -------------------------------------------------

    def set_password(self, password):
        """Hashes the provided plain-text password and stores the hash."""
        if password:
            self.password_hash = generate_password_hash(password)
        else:
            # Avoid storing hash for empty passwords, explicitly set to None
            self.password_hash = None
            log.warning(f"Attempted to set an empty password for user '{self.username}'")

    def check_password(self, password):
        """Checks if the provided plain-text password matches the stored hash."""
        if not self.password_hash or not password:
            # No stored hash or no provided password means no match
            return False
        return check_password_hash(self.password_hash, password)

    # --- Database Methods ---
    @staticmethod
    def get_collection():
        """Gets the MongoDB collection instance for 'users'."""
        try:
            db = get_db() # Get database handle from application context
            return db.users # Access the 'users' collection
        except Exception as e:
            # Log critical error if database handle cannot be obtained
            log.critical(f"Failed to get database handle in User model: {e}", exc_info=True)
            # Raise a runtime error to indicate a severe problem
            raise RuntimeError("Could not get database handle.") from e


    def save(self):
        """
        Saves the current user object to the MongoDB 'users' collection.
        Performs an insert if the user has no ID, or an update if an ID exists.

        Returns:
            str: The user's ID string upon successful save/update.
            None: If the save operation fails (e.g., duplicate key, DB error).
        """
        try:
            users_collection = User.get_collection()
            # Prepare the data document to be saved, using internal state
            user_data = {
                'username': self.username,
                'email': self.email, # Assumes already lowercase
                'password_hash': self.password_hash,
                'role': self.role,
                # ---> Save the internal state (_is_active) to the database field <---
                'is_active': self._is_active
            }

            if self.id: # Update existing user (self.id was set during __init__)
                log.debug(f"Attempting to update user with ID: {self.id}")
                # Basic check before attempting update
                if not self.username or not self.email:
                    log.error(f"Attempted to update user {self.id} with missing username or email.")
                    return None

                # Perform the update operation using the user's ObjectId
                update_result = users_collection.update_one(
                    {'_id': ObjectId(self.id)}, # Filter by ObjectId
                    {'$set': user_data}         # Set the new data
                )
                # Check if any document was actually found and potentially modified
                if update_result.matched_count == 0:
                    log.warning(f"Attempted to update user ID {self.id}, but no document matched.")
                    return None # Indicate failure if no user found to update
                # Log success, including whether data was actually changed
                log.info(f"Updated user '{self.username}' (ID: {self.id}). Matched: {update_result.matched_count}, Modified: {update_result.modified_count}")
                # Return the existing ID upon successful update attempt
                return self.id
            else: # Insert new user (self.id is None)
                log.debug(f"Attempting to insert new user: {self.username}")
                # Ensure essential fields for a new user are present
                if not self.username or not self.email or not self.password_hash:
                    log.error(f"Attempted to insert user with missing required fields: username='{self.username}', email='{self.email}', hash_present={bool(self.password_hash)}")
                    return None

                # Perform the insert operation
                insert_result = users_collection.insert_one(user_data)
                # Check if insert was acknowledged and retrieve the new ObjectId
                if insert_result.acknowledged:
                    new_id = str(insert_result.inserted_id)
                    log.info(f"Inserted new user '{self.username}' with ID: {new_id}")
                    # Return the newly generated ID as a string
                    return new_id
                else:
                    log.error(f"MongoDB insert for user '{self.username}' was not acknowledged.")
                    return None

        except pymongo_errors.DuplicateKeyError as e:
             # Handle violation of unique indexes (username or email)
             log.error(f"Failed to save user '{self.username}': Duplicate key error. Details: {e.details}")
             return None # Indicate failure due to duplication
        except Exception as e:
            # Catch any other unexpected database errors
            log.error(f"Unexpected error during User.save for user '{self.username}': {e}", exc_info=True)
            return None # Indicate general failure


    @staticmethod
    def _create_user_from_doc(user_data):
        """Internal helper method to create a User object from a MongoDB document."""
        if not user_data or not isinstance(user_data, dict):
            return None
        # Create User instance, passing the 'is_active' field from DB
        # to the 'is_active' parameter of __init__
        try:
            return User(
                _id=user_data.get('_id'), # Pass the ObjectId directly
                username=user_data.get('username'),
                email=user_data.get('email'),
                password_hash=user_data.get('password_hash'),
                role=user_data.get('role', 'employee'), # Provide default role
                # ---> Read the database field into the init parameter <---
                is_active=user_data.get('is_active', True) # Provide default active status
            )
        except Exception as e:
            log.error(f"Error creating User object from document: {e}", exc_info=True)
            return None


    @staticmethod
    def get_by_id(user_id):
        """Finds a user by their MongoDB ObjectId string."""
        if not user_id:
            log.debug("get_by_id called with empty user_id.")
            return None
        try:
            # Find the document matching the ObjectId string
            user_data = User.get_collection().find_one({'_id': ObjectId(user_id)})
            # Use the helper to create the User object
            return User._create_user_from_doc(user_data)
        except bson_errors.InvalidId:
            # Handle cases where the provided user_id string is not a valid ObjectId
            log.warning(f"Invalid ObjectId format passed to get_by_id: '{user_id}'")
        except Exception as e:
            log.error(f"Error in get_by_id for ID '{user_id}': {e}", exc_info=True)
        return None # Return None if not found or error occurs


    @staticmethod
    def get_by_username(username):
        """Finds a user by their username (case-sensitive)."""
        if not username:
            log.debug("get_by_username called with empty username.")
            return None
        try:
            # Perform case-sensitive search for username
            # For case-insensitive, use: {'username': {'$regex': f'^{re.escape(username)}$', '$options': 'i'}}
            user_data = User.get_collection().find_one({'username': username})
            # Use the helper to create the User object
            return User._create_user_from_doc(user_data)
        except Exception as e:
            log.error(f"Error in get_by_username for username '{username}': {e}", exc_info=True)
        return None


    @staticmethod
    def get_by_email(email):
        """Finds a user by their email (case-insensitive search)."""
        if not email:
            log.debug("get_by_email called with empty email.")
            return None
        try:
            # Perform case-insensitive search by converting query email to lowercase
            user_data = User.get_collection().find_one({'email': email.lower()})
            # Use the helper to create the User object
            return User._create_user_from_doc(user_data)
        except Exception as e:
            log.error(f"Error in get_by_email for email '{email}': {e}", exc_info=True)
        return None


    # --- Flask-Login required properties/methods ---
    # These are essential for integrating with Flask-Login session management.

    # is_active property is defined explicitly near the top of the class now.

    @property
    def is_authenticated(self):
        """Required by Flask-Login. Indicates if the user is authenticated."""
        # If this object represents a logged-in user, they are authenticated.
        return True

    @property
    def is_anonymous(self):
        """Required by Flask-Login. Indicates if the user is anonymous."""
        # Real user objects are never anonymous.
        return False

    def get_id(self):
        """Required by Flask-Login. Returns the unique ID for the user as a string."""
        # Flask-Login requires this to be a string (unicode in Python 2).
        return str(self.id)


    def __repr__(self):
        """Provides a developer-friendly string representation of the User object."""
        return f'<User id={self.id} username="{self.username}" email="{self.email}" role="{self.role}" active={self.is_active}>'