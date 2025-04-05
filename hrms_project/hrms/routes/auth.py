from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash # Use check_password_hash from User model is better
from ..models.user import User
from .. import get_db # Import get_db if you need direct db access here, usually model methods are enough

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard')) # Redirect if already logged in

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        if not username or not password:
             flash('Please enter both username and password.', 'warning')
             return render_template('auth/login.html', title="Login")

        user = User.get_by_username(username)

        # Check if user exists and password is correct
        if not user or not user.check_password(password):
            flash('Invalid username or password. Please try again.', 'danger')
            return render_template('auth/login.html', title="Login")

        # Check if user account is active
        if not user.is_active:
             flash('Your account is inactive. Please contact HR/Admin.', 'warning')
             return render_template('auth/login.html', title="Login")

        # Log the user in using Flask-Login
        login_user(user, remember=remember)
        flash(f'Welcome back, {user.username}!', 'success')

        # Redirect to the page user was trying to access, or dashboard
        next_page = request.args.get('next')
        return redirect(next_page) if next_page else redirect(url_for('main.dashboard'))

    # GET Request
    return render_template('auth/login.html', title="Login")


@auth_bp.route('/register', methods=['GET', 'POST'])
# @login_required # Maybe only admins can register new users? Or allow self-registration?
# @role_required(['admin']) # Example if only admins can register
def register():
    # Basic Registration Example - Adapt permissions as needed
    # You might want only Admins/HR to create users, or have an approval flow.

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        password2 = request.form.get('password2')
        role = request.form.get('role', 'employee') # Default role

        # --- Basic Validation ---
        if not username or not email or not password or not password2:
             flash('All fields are required.', 'warning')
             return render_template('auth/register.html', title="Register")

        if password != password2:
            flash('Passwords do not match.', 'warning')
            return render_template('auth/register.html', title="Register")

        # Check if username or email already exists
        if User.get_by_username(username):
             flash('Username already exists. Please choose another.', 'danger')
             return render_template('auth/register.html', title="Register", username=username, email=email)
        if User.get_by_email(email):
             flash('Email address already registered. Please use another.', 'danger')
             return render_template('auth/register.html', title="Register", username=username, email=email)

        # --- Create User ---
        new_user = User(username=username, email=email, role=role)
        new_user.set_password(password) # Hash the password
        try:
            saved_user = new_user.save()
            flash(f'User {saved_user.username} created successfully! They can now log in.', 'success')
            # Decide where to redirect: login page or maybe user list if admin created
            return redirect(url_for('auth.login'))
            # If admin created, maybe: return redirect(url_for('admin.list_users'))
        except Exception as e:
             flash(f'Error creating user: {e}', 'danger')
             # Log the error e
             return render_template('auth/register.html', title="Register", username=username, email=email)


    # --- GET Request ---
    # Decide if registration should be publicly accessible
    # For internal HRMS, usually registration is handled by Admin/HR
    # If allowing self-registration, ensure proper validation and maybe email verification
    return render_template('auth/register.html', title="Register")


@auth_bp.route('/logout')
@login_required # Must be logged in to logout
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))