from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@main_bp.route('/dashboard')
@login_required # User must be logged in to see the dashboard
def dashboard():
    """Displays the main dashboard."""
    # In a real app, fetch relevant data based on user role:
    # - Pending approvals for managers/HR
    # - Upcoming holidays/events
    # - Quick links
    # - Own leave balance for employees
    # etc.

    # Example: Pass username to the template
    username = current_user.username
    role = current_user.role

    # You could fetch some stats here:
    # from ..models.employee import Employee
    # total_employees = len(Employee.find_all(projection={'_id': 1})) # Efficient count
    total_employees = 0 # Placeholder

    return render_template(
        'main/dashboard.html',
        title="Dashboard",
        username=username,
        role=role,
        total_employees=total_employees
    )

# You might have a public landing page if the root is not the dashboard
# @main_bp.route('/welcome')
# def welcome():
#     return render_template('main/welcome.html') # Create this template if needed