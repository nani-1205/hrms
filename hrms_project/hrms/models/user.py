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
        # Use bcrypt or werkzeug for hashing
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # --- Database Methods ---
    @staticmethod
    def get_collection():
        db = get_db()
        return db.users

    def save(self):
        users_collection = User.get_collection()
        user_data = {
            'username': self.username,
            'email': self.email,
            'password_hash': self.password_hash,
            'role': self.role,
            'is_active': self.is_active
        }
        if self.id: # Update existing user
             users_collection.update_one({'_id': ObjectId(self.id)}, {'$set': user_data})
        else: # Insert new user
            result = users_collection.insert_one(user_data)
            self.id = str(result.inserted_id) # Update the instance id
        return self

    @staticmethod
    def get_by_id(user_id):
        try:
            user_data = User.get_collection().find_one({'_id': ObjectId(user_id)})
            if user_data:
                return User(
                    _id=user_data['_id'],
                    username=user_data['username'],
                    email=user_data['email'],
                    password_hash=user_data['password_hash'],
                    role=user_data.get('role', 'employee'), # Default role if missing
                    is_active=user_data.get('is_active', True)
                )
        except Exception: # Handle invalid ObjectId format etc.
             pass
        return None

    @staticmethod
    def get_by_username(username):
        user_data = User.get_collection().find_one({'username': username})
        if user_data:
            return User(
                _id=user_data['_id'],
                username=user_data['username'],
                email=user_data['email'],
                password_hash=user_data['password_hash'],
                role=user_data.get('role', 'employee'),
                is_active=user_data.get('is_active', True)
            )
        return None

    @staticmethod
    def get_by_email(email):
        user_data = User.get_collection().find_one({'email': email})
        if user_data:
             return User(
                _id=user_data['_id'],
                username=user_data['username'],
                email=user_data['email'],
                password_hash=user_data['password_hash'],
                role=user_data.get('role', 'employee'),
                is_active=user_data.get('is_active', True)
            )
        return None

    # Required properties/methods for Flask-Login
    @property
    def is_authenticated(self):
        return True # Assuming if the object exists, the user is authenticated

    # is_active is already a property

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id) # Must return a string

    def __repr__(self):
        return f'<User {self.username}>'