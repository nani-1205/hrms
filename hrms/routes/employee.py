from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user # Protect routes
from ..models.employee import Employee
from bson import ObjectId # Import ObjectId

employee_bp = Blueprint('employee', __name__)

# Decorator for role checking (Example)
from functools import wraps

def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in role:
                 flash('You do not have permission to access this page.', 'danger')
                 return redirect(url_for('main.dashboard')) # Or appropriate page
            return f(*args, **kwargs)
        return decorated_function
    return decorator


@employee_bp.route('/')
@login_required # Must be logged in
# @role_required(['admin', 'hr', 'manager']) # Example: Only admins, HR, or managers can view list
def list_employees():
    """List all employees."""
    # Add pagination later
    employees = Employee.find_all(sort=[('last_name', 1), ('first_name', 1)])
    return render_template('employee/list.html', employees=employees, title="Employees")

@employee_bp.route('/<id>')
@login_required
def detail(id):
    """Show employee details."""
    employee = Employee.find_by_id(id)
    if not employee:
        flash('Employee not found.', 'danger')
        return redirect(url_for('employee.list_employees'))
    # Add permission check: Can current_user view this specific employee?
    # e.g., if current_user.role == 'manager' and employee['manager_id'] != current_user.id: deny
    return render_template('employee/detail.html', employee=employee, title="Employee Details")

@employee_bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'hr']) # Only admin/HR can add
def add_employee():
    """Add a new employee."""
    if request.method == 'POST':
        # --- Basic Form Data Handling ---
        # IMPORTANT: Add proper validation and sanitation here!
        form_data = {
            'first_name': request.form.get('first_name'),
            'last_name': request.form.get('last_name'),
            'email': request.form.get('email'),
            'employee_code': request.form.get('employee_code'), # Ensure unique
            'department': request.form.get('department'),
            'designation': request.form.get('designation'),
            'date_of_joining': request.form.get('date_of_joining'), # Convert to datetime object maybe
            'contact_no': request.form.get('contact_no'),
            'status': 'active' # Default status
            # Add other fields from your form
        }

        # Basic validation example
        if not form_data['first_name'] or not form_data['last_name'] or not form_data['email']:
            flash('First Name, Last Name, and Email are required.', 'warning')
            return render_template('employee/form.html', title="Add Employee", employee=form_data) # Pass data back

        # Check if employee code or email already exists (if they should be unique)
        if Employee.find_by_employee_code(form_data['employee_code']):
             flash(f"Employee code '{form_data['employee_code']}' already exists.", 'danger')
             return render_template('employee/form.html', title="Add Employee", employee=form_data)

        # --- Create Employee ---
        try:
            employee_id = Employee.create(form_data)
            flash(f"Employee '{form_data['first_name']} {form_data['last_name']}' added successfully!", 'success')
            return redirect(url_for('employee.detail', id=employee_id))
        except Exception as e:
            flash(f"Error adding employee: {e}", 'danger')
            # Log the error e
            return render_template('employee/form.html', title="Add Employee", employee=form_data)


    # --- GET Request ---
    return render_template('employee/form.html', title="Add Employee", employee={}) # Pass empty dict for template consistency

@employee_bp.route('/edit/<id>', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'hr']) # Only admin/HR can edit
def edit_employee(id):
    """Edit an existing employee."""
    employee = Employee.find_by_id(id)
    if not employee:
        flash('Employee not found.', 'danger')
        return redirect(url_for('employee.list_employees'))

    if request.method == 'POST':
        # --- Basic Form Data Handling ---
        # IMPORTANT: Add proper validation and sanitation here!
        form_data = {
            'first_name': request.form.get('first_name'),
            'last_name': request.form.get('last_name'),
            'email': request.form.get('email'),
            'employee_code': request.form.get('employee_code'),
            'department': request.form.get('department'),
            'designation': request.form.get('designation'),
            'date_of_joining': request.form.get('date_of_joining'),
            'contact_no': request.form.get('contact_no'),
            'status': request.form.get('status', employee.get('status')) # Keep old status if not provided
            # Add other fields from your form
        }

        # Basic validation example
        if not form_data['first_name'] or not form_data['last_name'] or not form_data['email']:
            flash('First Name, Last Name, and Email are required.', 'warning')
            # Pass original employee data merged with form data for repopulation
            updated_view_data = {**employee, **form_data}
            return render_template('employee/form.html', title="Edit Employee", employee=updated_view_data, edit_mode=True, id=id)

        # Check for uniqueness if necessary (e.g., if employee_code changed)
        # existing_emp = Employee.find_by_employee_code(form_data['employee_code'])
        # if existing_emp and str(existing_emp['_id']) != id:
        #     flash(f"Employee code '{form_data['employee_code']}' already used by another employee.", 'danger')
        #     updated_view_data = {**employee, **form_data}
        #     return render_template('employee/form.html', title="Edit Employee", employee=updated_view_data, edit_mode=True, id=id)

        # --- Update Employee ---
        try:
            if Employee.update(id, form_data):
                flash('Employee updated successfully!', 'success')
                return redirect(url_for('employee.detail', id=id))
            else:
                 flash('No changes detected or error updating employee.', 'info')
                 # Optional: redirect back to detail or stay on edit page
                 return redirect(url_for('employee.edit_employee', id=id))

        except Exception as e:
            flash(f"Error updating employee: {e}", 'danger')
            # Log the error e
            updated_view_data = {**employee, **form_data}
            return render_template('employee/form.html', title="Edit Employee", employee=updated_view_data, edit_mode=True, id=id)

    # --- GET Request ---
    # Convert ObjectId to string for the template if necessary, though direct access usually works
    employee['_id'] = str(employee['_id'])
    return render_template('employee/form.html', title="Edit Employee", employee=employee, edit_mode=True, id=id)


@employee_bp.route('/delete/<id>', methods=['POST']) # Use POST for delete actions
@login_required
@role_required(['admin', 'hr']) # Only admin/HR can delete
def delete_employee(id):
    """Delete an employee."""
    # Consider soft delete (changing status) instead of hard delete
    employee = Employee.find_by_id(id) # Check if exists first
    if not employee:
         flash('Employee not found.', 'danger')
         return redirect(url_for('employee.list_employees'))

    try:
        if Employee.delete(id):
            flash(f"Employee '{employee.get('first_name', '')} {employee.get('last_name', '')}' deleted successfully!", 'success')
        else:
            flash('Error deleting employee.', 'danger')
    except Exception as e:
         flash(f"Error deleting employee: {e}", 'danger')
         # Log the error

    return redirect(url_for('employee.list_employees'))