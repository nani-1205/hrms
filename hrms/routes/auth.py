# hrms/routes/auth.py

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
# No need to import check_password_hash here for registration
from ..models.user import User
# Import ObjectId if you were planning to link users to employees immediately
# from bson import ObjectId
# Import get_db only if direct access needed, model methods are preferred
# from .. import get_db

auth_bp = Blueprint('auth', __name__)

# --- LOGIN ROUTE ---
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        if not username or not password:
             flash('Please enter both username and password.', 'warning')
             return render_template('auth/login.html', title="Login")

        user = User.get_by_username(username)

        if not user or not user.check_password(password):
            flash('Invalid username or password. Please try again.', 'danger')
            return render_template('auth/login.html', title="Login")

        if not user.is_active:
             flash('Your account is inactive. Please contact HR/Admin.', 'warning')
             return render_template('auth/login.html', title="Login")

        login_user(user, remember=remember)
        flash(f'Welcome back, {user.username}!', 'success')
        next_page = request.args.get('next')
        return redirect(next_page) if next_page else redirect(url_for('main.dashboard'))

    return render_template('auth/login.html', title="Login")


# --- REGISTER ROUTE --- # <--- ADD THIS FUNCTION ---
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Handles user registration."""
    if current_user.is_authenticated:
        # If user is already logged in, redirect them away from register page
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower() # Store emails lowercase
        password = request.form.get('password')
        password2 = request.form.get('password2')
        # Default role for self-registration. Change if needed or add admin control.
        role = 'employee'

        # --- Input Validation ---
        error = False
        if not username:
            flash('Username is required.', 'warning')
            error = True
        if not email:
            flash('Email is required.', 'warning')
            error = True
        # Add basic email format check if desired (more robust checks exist)
        # elif '@' not in email or '.' not in email.split('@')[-1]:
        #     flash('Invalid email format.', 'warning')
        #     error = True
        if not password:
            flash('Password is required.', 'warning')
            error = True
        if password != password2:
            flash('Passwords do not match.', 'warning')
            error = True

        # Check if username or email already exists in DB
        if not error:
            if User.get_by_username(username):
                flash(f"Username '{username}' is already taken. Please choose another.", 'danger')
                error = True
            if User.get_by_email(email):
                flash(f"Email '{email}' is already registered. Please use another.", 'danger')
                error = True

        if error:
            # Re-render form, passing back submitted values (except password)
            return render_template('auth/register.html', title="Register",
                                   username=username, email=email)

        # --- Create and Save New User ---
        try:
            new_user = User(username=username, email=email, role=role)
            new_user.set_password(password) # Hash the password
            saved_user = new_user.save()    # Save to MongoDB
            flash(f'Account created successfully for {saved_user.username}! Please log in.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            # Log the actual error e in a real application
            print(f"Error saving user: {e}") # Basic print for debugging
            flash('An error occurred while creating your account. Please try again later.', 'danger')
            return render_template('auth/register.html', title="Register",
                                   username=username, email=email)

    # --- GET Request ---
    # Consider adding a config flag (e.g., app.config['ALLOW_REGISTRATION'])
    # to disable this route easily if self-registration shouldn't be allowed.
    # if not current_app.config.get('ALLOW_REGISTRATION', True):
    #    flash('Self-registration is currently disabled.', 'info')
    #    return redirect(url_for('auth.login'))

    return render_template('auth/register.html', title="Register")
# -------------------------------------------------- #


# --- LOGOUT ROUTE ---
@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))