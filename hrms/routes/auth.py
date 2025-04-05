# hrms/routes/auth.py

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
# No need to import check_password_hash here, use user.check_password()
from ..models.user import User
# from bson import ObjectId # Not needed here currently
# from .. import get_db # Not needed here currently
import logging

# Get a logger instance for this module
log = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)


# --- LOGIN ROUTE ---
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handles user login."""
    if current_user.is_authenticated:
        log.debug(f"User '{current_user.username}' already authenticated. Redirecting to dashboard.")
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        log.info(f"Login attempt for username: '{username}'")

        if not username or not password:
             flash('Please enter both username and password.', 'warning')
             return render_template('auth/login.html', title="Login")

        # Find user by username
        user = User.get_by_username(username)

        # Validate user and password
        if not user:
            log.warning(f"Login failed: Username '{username}' not found.")
            flash('Invalid username or password. Please try again.', 'danger')
        elif not user.check_password(password):
            log.warning(f"Login failed: Incorrect password for username '{username}'.")
            flash('Invalid username or password. Please try again.', 'danger')
        elif not user.is_active:
             log.warning(f"Login failed: Account for username '{username}' is inactive.")
             flash('Your account is inactive. Please contact HR/Admin.', 'warning')
        else:
            # Login successful
            login_user(user, remember=remember)
            log.info(f"User '{username}' logged in successfully.")
            flash(f'Welcome back, {user.username}!', 'success')

            # Redirect to originally requested page or dashboard
            next_page = request.args.get('next')
            if next_page:
                 log.debug(f"Redirecting logged in user '{username}' to originally requested page: {next_page}")
                 # Basic check to prevent open redirect vulnerability
                 # More robust checks might involve urlparse or Werkzeug's safe_redirect
                 if not next_page.startswith('/'):
                     next_page = url_for('main.dashboard') # Fallback if next_page seems unsafe
                 return redirect(next_page)
            else:
                 log.debug(f"Redirecting logged in user '{username}' to dashboard.")
                 return redirect(url_for('main.dashboard'))

        # If any checks failed, re-render login page
        return render_template('auth/login.html', title="Login")

    # --- GET Request ---
    return render_template('auth/login.html', title="Login")


# --- REGISTER ROUTE ---
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Handles user registration."""
    if current_user.is_authenticated:
        # If user is already logged in, redirect them away
        log.debug(f"Authenticated user '{current_user.username}' attempted to access register page. Redirecting.")
        return redirect(url_for('main.dashboard'))

    # Optional: Check if self-registration is allowed via config
    # allow_reg = current_app.config.get('ALLOW_SELF_REGISTRATION', True) # Example config flag
    # if not allow_reg:
    #    log.info("Self-registration attempt denied (feature disabled).")
    #    flash('Self-registration is currently disabled.', 'info')
    #    return redirect(url_for('auth.login'))

    form_data = {} # To hold submitted data for re-rendering form on error
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower() # Store emails consistently lowercase
        password = request.form.get('password')
        password2 = request.form.get('password2')
        role = 'employee' # Default role for self-registration

        # Store for re-rendering form (don't store password)
        form_data['username'] = username
        form_data['email'] = email

        log.info(f"Registration attempt: username='{username}', email='{email}'")

        # --- Input Validation ---
        error = False
        if not username: flash('Username is required.', 'warning'); error = True
        if not email: flash('Email is required.', 'warning'); error = True
        # Add more robust email validation if needed (e.g., using regex or a library)
        if not password: flash('Password is required.', 'warning'); error = True
        if password != password2: flash('Passwords do not match.', 'warning'); error = True
        # Add password complexity rules if desired

        # DB Checks (only if basic validation passed)
        if not error:
            try:
                # Check for existing username
                if User.get_by_username(username):
                    log.warning(f"Registration failed: Username '{username}' already exists.")
                    flash(f"Username '{username}' is already taken. Please choose another.", 'danger')
                    error = True
                # Check for existing email
                if User.get_by_email(email):
                    log.warning(f"Registration failed: Email '{email}' already exists.")
                    flash(f"Email '{email}' is already registered. Please use another.", 'danger')
                    error = True
            except Exception as e:
                # Catch potential DB errors during checks
                log.error(f"Database error during registration check for '{username}': {e}", exc_info=True)
                flash('Error checking existing user data. Please try again later.', 'danger')
                error = True # Treat DB error as validation failure for this attempt

        if error:
            # Re-render form with errors and previous input
            return render_template('auth/register.html', title="Register", **form_data)

        # --- Create and Save New User ---
        # This block runs only if all validation passed
        try:
            new_user = User(username=username, email=email, role=role)
            new_user.set_password(password) # Hash the password

            # Call save() and check the returned ID
            new_user_id = new_user.save() # Calls the updated save() method

            if new_user_id: # Check if save() succeeded (returned a valid ID string)
                log.info(f"Successfully created user '{username}' with ID {new_user_id}")
                flash(f'Account created successfully for {username}! Please log in.', 'success')
                return redirect(url_for('auth.login'))
            else:
                # Handle the case where save() returned None (internal model error, maybe duplicate key)
                log.error(f"User.save() failed for username '{username}' (returned None). Check model logs for specific error (e.g., duplicate key).")
                # Provide a slightly more informative message if possible, but avoid exposing too much detail
                flash('Could not save account details. The username or email might already be in use, or an internal error occurred.', 'danger')
                return render_template('auth/register.html', title="Register", **form_data)

        except Exception as e:
            # Catch any other unexpected errors during user creation/saving process
            log.error(f"Unexpected error during registration save process for username '{username}': {e}", exc_info=True)
            flash('An unexpected error occurred while creating your account. Please try again later or contact support.', 'danger')
            return render_template('auth/register.html', title="Register", **form_data)

    # --- GET Request ---
    # Render the empty registration form
    return render_template('auth/register.html', title="Register")


# --- LOGOUT ROUTE ---
@auth_bp.route('/logout')
@login_required # User must be logged in to log out
def logout():
    """Handles user logout."""
    username = current_user.username # Get username before logging out
    logout_user()
    log.info(f"User '{username}' logged out.")
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login')) # Redirect to login page after logout