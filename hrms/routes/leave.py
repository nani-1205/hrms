from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from ..models.leave import LeaveRequest
from ..models.employee import Employee # May need employee details
from bson import ObjectId
from datetime import datetime

# Import role decorator if needed
# from .employee import role_required

leave_bp = Blueprint('leave', __name__)


@leave_bp.route('/request', methods=['GET', 'POST'])
@login_required
def request_leave():
    """ Allows employees to request leave. """
    if request.method == 'POST':
        # Basic validation - IMPROVE SIGNIFICANTLY
        leave_type = request.form.get('leave_type')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        reason = request.form.get('reason')

        if not leave_type or not start_date_str or not end_date_str or not reason:
             flash('All fields are required.', 'warning')
             return render_template('leave/request_form.html', title="Request Leave")

        try:
            # Convert dates and validate range
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            if start_date > end_date:
                 flash('Start date cannot be after end date.', 'warning')
                 return render_template('leave/request_form.html', title="Request Leave", form_data=request.form)

            # Check leave balance (Requires more logic based on Employee model and leave policies)

            data = {
                'user_id': ObjectId(current_user.get_id()),
                # 'employee_id': find employee id associated with user_id if needed
                'leave_type': leave_type,
                'start_date': start_date,
                'end_date': end_date,
                'reason': reason,
            }
            leave_id = LeaveRequest.create(data)
            flash('Leave request submitted successfully!', 'success')
            return redirect(url_for('leave.view_history'))

        except ValueError:
             flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
             return render_template('leave/request_form.html', title="Request Leave", form_data=request.form)
        except Exception as e:
             flash(f'Error submitting request: {e}', 'danger')
             # Log error
             return render_template('leave/request_form.html', title="Request Leave", form_data=request.form)


    # GET request
    # Fetch leave types from config or DB maybe
    leave_types = ['Annual', 'Sick', 'Unpaid', 'Maternity', 'Paternity'] # Example
    return render_template('leave/request_form.html', title="Request Leave", leave_types=leave_types)


@leave_bp.route('/history')
@login_required
def view_history():
    """ Shows the current user's leave request history. """
    user_id = current_user.get_id()
    requests = LeaveRequest.find_by_user(user_id, sort=[('requested_on', -1)]) # Newest first
    return render_template('leave/history.html', title="My Leave History", requests=requests)


@leave_bp.route('/approvals')
@login_required
# @role_required(['manager', 'hr', 'admin']) # Only relevant roles should access
def view_approvals():
    """ Shows pending leave requests for approval (for managers/HR). """
    # Check role again for safety
    if current_user.role not in ['manager', 'hr', 'admin']:
        flash('You do not have permission to view leave approvals.', 'danger')
        return redirect(url_for('main.dashboard'))

    # Adapt based on approval workflow (e.g., manager approves own team)
    manager_id = None
    if current_user.role == 'manager':
        manager_id = current_user.get_id() # Assuming manager's user_id is used

    pending_requests = LeaveRequest.find_pending_approvals(manager_id=manager_id)

    # Enhance: Fetch employee names for display
    # enriched_requests = []
    # for req in pending_requests:
    #     user = User.get_by_id(req['user_id']) # Fetch user details
    #     req['requester_name'] = user.username if user else 'Unknown User'
    #     enriched_requests.append(req)

    return render_template('leave/approvals.html', title="Leave Approvals", requests=pending_requests)


@leave_bp.route('/approve/<request_id>', methods=['POST'])
@login_required
# @role_required(['manager', 'hr', 'admin'])
def approve_leave(request_id):
    if current_user.role not in ['manager', 'hr', 'admin']:
        flash('Permission denied.', 'danger')
        return redirect(url_for('leave.view_approvals'))

    # Add check: Does this manager ACTUALLY have permission to approve THIS request?

    success = LeaveRequest.update_status(request_id, 'Approved', current_user.get_id())
    if success:
        flash('Leave request approved.', 'success')
        # Add notification logic here (e.g., email employee)
    else:
        flash('Failed to approve leave request.', 'danger')
    return redirect(url_for('leave.view_approvals'))


@leave_bp.route('/reject/<request_id>', methods=['POST'])
@login_required
# @role_required(['manager', 'hr', 'admin'])
def reject_leave(request_id):
    if current_user.role not in ['manager', 'hr', 'admin']:
        flash('Permission denied.', 'danger')
        return redirect(url_for('leave.view_approvals'))

    # Add check: Does this manager ACTUALLY have permission to reject THIS request?

    comments = request.form.get('rejection_reason', '') # Optional reason from form
    success = LeaveRequest.update_status(request_id, 'Rejected', current_user.get_id(), comments)
    if success:
        flash('Leave request rejected.', 'success')
        # Add notification logic here
    else:
        flash('Failed to reject leave request.', 'danger')
    return redirect(url_for('leave.view_approvals'))

# Add routes for cancelling a request (by employee)
# Add route for viewing leave balances