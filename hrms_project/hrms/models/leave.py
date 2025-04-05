from bson import ObjectId
from datetime import datetime
from .. import get_db

class LeaveRequest:
    # Fields: user_id (ObjectId), employee_id (ObjectId, if different from user),
    # leave_type (e.g., 'Annual', 'Sick', 'Unpaid'),
    # start_date (datetime), end_date (datetime), reason (string),
    # status ('Pending', 'Approved', 'Rejected', 'Cancelled'),
    # requested_on (datetime), approved_by (ObjectId, optional), approved_on (datetime, optional),
    # comments (string, optional)

    @staticmethod
    def get_collection():
        db = get_db()
        return db.leave_requests

    @staticmethod
    def create(data):
        """ Creates a new leave request. """
        collection = LeaveRequest.get_collection()
        # Add validation! Ensure dates are valid, user exists, etc.
        data['requested_on'] = datetime.utcnow()
        data['status'] = 'Pending' # Initial status
        # Convert date strings to datetime objects if needed
        # data['start_date'] = datetime.strptime(data['start_date'], '%Y-%m-%d')
        # data['end_date'] = datetime.strptime(data['end_date'], '%Y-%m-%d')
        result = collection.insert_one(data)
        return str(result.inserted_id)

    @staticmethod
    def find_by_user(user_id, sort=None):
        """ Finds leave requests for a specific user. """
        collection = LeaveRequest.get_collection()
        query = {'user_id': ObjectId(user_id)}
        cursor = collection.find(query)
        if sort:
             cursor = cursor.sort(sort)
        return list(cursor)

    @staticmethod
    def find_pending_approvals(manager_id=None):
        """ Finds leave requests needing approval. """
        # This logic depends on your org structure (who approves?)
        # Simplistic: Find all 'Pending' requests
        collection = LeaveRequest.get_collection()
        query = {'status': 'Pending'}
        # If manager specific approval needed, query based on manager_id associated with the requesting employee
        # Add logic here based on Employee model structure (e.g., employee['manager_id'] == manager_id)
        cursor = collection.find(query).sort([('requested_on', 1)]) # Sort by oldest first
        return list(cursor)

    @staticmethod
    def find_by_id(request_id):
        """ Finds a single request by its MongoDB _id. """
        collection = LeaveRequest.get_collection()
        try:
            return collection.find_one({'_id': ObjectId(request_id)})
        except Exception:
            return None

    @staticmethod
    def update_status(request_id, status, approver_id=None, comments=None):
        """ Updates the status of a leave request (Approve/Reject). """
        collection = LeaveRequest.get_collection()
        update_data = {
            'status': status,
            'approved_on': datetime.utcnow(),
            'approved_by': ObjectId(approver_id) if approver_id else None
        }
        if comments:
            update_data['comments'] = comments

        try:
            result = collection.update_one(
                {'_id': ObjectId(request_id)},
                {'$set': update_data}
            )
            return result.modified_count > 0
        except Exception:
             return False

    # Add method to cancel a request (by employee, if status is 'Pending')
    # Add method to calculate leave days, check balance etc. (more complex)