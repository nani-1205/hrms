from bson import ObjectId
from datetime import datetime
from .. import get_db

class Employee:
    # Define fields relevant to an employee
    # Basic example:
    # Personal Info: first_name, last_name, dob, gender, contact_no, email, address
    # Job Info: employee_id (unique), department, designation, date_of_joining, manager_id (optional ObjectId)
    # Status: status (active, inactive, terminated)
    # Potentially link to User model: user_id (ObjectId) if employees can log in

    @staticmethod
    def get_collection():
        db = get_db()
        return db.employees

    @staticmethod
    def create(data):
        """ Creates a new employee record. """
        collection = Employee.get_collection()
        # Add validation logic here
        data['date_added'] = datetime.utcnow()
        data['last_updated'] = datetime.utcnow()
        result = collection.insert_one(data)
        return str(result.inserted_id)

    @staticmethod
    def find_all(query={}, projection=None, sort=None):
        """ Finds multiple employees based on query. """
        collection = Employee.get_collection()
        cursor = collection.find(query, projection)
        if sort:
             # sort should be a list of tuples, e.g., [('last_name', 1)]
             cursor = cursor.sort(sort)
        return list(cursor) # Convert cursor to list

    @staticmethod
    def find_by_id(employee_id):
        """ Finds a single employee by their MongoDB _id. """
        collection = Employee.get_collection()
        try:
            return collection.find_one({'_id': ObjectId(employee_id)})
        except Exception: # Handle invalid ObjectId
            return None

    @staticmethod
    def find_by_employee_code(emp_code):
        """ Finds a single employee by their unique employee code (if you have one). """
        collection = Employee.get_collection()
        return collection.find_one({'employee_code': emp_code}) # Assuming 'employee_code' field

    @staticmethod
    def update(employee_id, data):
        """ Updates an existing employee record. """
        collection = Employee.get_collection()
        # Prevent updating _id, maybe date_added
        data.pop('_id', None)
        data.pop('date_added', None)
        data['last_updated'] = datetime.utcnow()
        try:
            result = collection.update_one(
                {'_id': ObjectId(employee_id)},
                {'$set': data}
            )
            return result.modified_count > 0 # Return True if updated, False otherwise
        except Exception:
            return False


    @staticmethod
    def delete(employee_id):
        """ Deletes an employee record. Consider soft delete (setting a status) instead. """
        collection = Employee.get_collection()
        try:
            result = collection.delete_one({'_id': ObjectId(employee_id)})
            return result.deleted_count > 0 # Return True if deleted
        except Exception:
            return False

    # Add methods for specific queries: find_by_department, find_by_manager etc.