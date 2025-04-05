# hrms/models/user.py

from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from bson import ObjectId
from .. import get_db # Use the get_db function

class User(UserMixin):
    def __init__(self, username, email, password_hash=None, role='employee', _id=None, is_active=True):
        self.id = str(_id) if _id else None # Store id as string for Flask-Login
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.role = role # e.g., 'employee', 'manager', 'hr', 'admin'
        self.is_active = is_active # For Flask-Login

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        # Add a check for password_hash existence
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    # --- Database Methods ---
    @staticmethod
    def get_collection():
        db = get_db()
        return db.users

    def save(self):
        """Saves the user to the database. Returns the user's ID if successful, None otherwise."""
        users_collection = User.get_collection()
        user_data = {
            'username': self.username,
            'email': self.email,
            'password_hash': self.password_hash,
            'role': self.role,
            'is_active': self.is_active
        }
        try:
            if self.id: # Update existing user
                 update_result = users_collection.update_one({'_id': ObjectId(self.id)}, {'$set': user_data})
                 # Return the ID if modification was successful
                 return self.id if update_result.modified_count > 0 else None
            else: # Insert new user
                insert_result = users_collection.insert_one(user_data)
                # ---> Return the new ID as a string <---
                return str(insert_result.inserted_id)
        except Exception as e:
            # Log the error in a real app
            print(f"Error during User.save: {e}")
            return None # Indicate failure

    @staticmethod
    def get_by_id(user_id):
        # ... (keep existing get_by_id) ...
        try:
            user_data = User.get_collection().find_one({'_id': ObjectId(user_id)})
            if user_data:
                return User(
                    _id=user_data['_id'],
                    username=user_data['username'],
                    email=user_data['email'],
                    password_hash=user_data.get('password_hash'), # Use .get for safety
                    role=user_data.get('role', 'employee'),
                    is_active=user_data.get('is_active', True)
                )
        except Exception:
             pass
        return None

    @staticmethod
    def get_by_username(username):
        # ... (keep existing get_by_username) ...
        user_data = User.get_collection().find_one({'username': username})
        if user_data:
            return User(
                _id=user_data['_id'],
                username=user_data['username'],
                email=user_data['email'],
                password_hash=user_data.get('password_hash'),
                role=user_data.get('role', 'employee'),
                is_active=user_data.get('is_active', True)
            )
        return None

    @staticmethod
    def get_by_email(email):
        # ... (keep existing get_by_email) ...
        user_data = User.get_collection().find_one({'email': email.lower()}) # Ensure email check is lowercase too
        if user_data:
             return User(
                _id=user_data['_id'],
                username=user_data['username'],
                email=user_data['email'],
                password_hash=user_data.get('password_hash'),
                role=user_data.get('role', 'employee'),
                is_active=user_data.get('is_active', True)
            )
        return None

    # --- Flask-Login required properties/methods ---
    @property
    def is_authenticated(self):
        return True

    # is_active is already a property

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        # This method provided by UserMixin usually just returns self.id
        return str(self.id)

    def __repr__(self):
        return f'<User {self.username}>'