# hrms/routes/auth.py

# ... (imports and other routes remain the same) ...

# --- REGISTER ROUTE ---
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Handles user registration."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')
        password2 = request.form.get('password2')
        role = 'employee'

        # --- Input Validation ---
        error = False
        # ... (keep existing validation checks) ...
        if not username:
            flash('Username is required.', 'warning'); error = True
        if not email:
            flash('Email is required.', 'warning'); error = True
        if not password:
            flash('Password is required.', 'warning'); error = True
        if password != password2:
            flash('Passwords do not match.', 'warning'); error = True

        if not error:
            if User.get_by_username(username):
                flash(f"Username '{username}' is already taken. Please choose another.", 'danger'); error = True
            # Ensure email check is case-insensitive if storing lowercase
            if User.get_by_email(email):
                flash(f"Email '{email}' is already registered. Please use another.", 'danger'); error = True

        if error:
            return render_template('auth/register.html', title="Register",
                                   username=username, email=email)

        # --- Create and Save New User ---
        try:
            new_user = User(username=username, email=email, role=role)
            new_user.set_password(password)
            # ---> Call save() and check the returned ID <---
            new_user_id = new_user.save()

            if new_user_id: # Check if save() returned a valid ID
                flash(f'Account created successfully for {username}! Please log in.', 'success')
                return redirect(url_for('auth.login'))
            else:
                # Handle the case where save returned None (indicating failure)
                flash('An error occurred while saving your account details.', 'danger')
                return render_template('auth/register.html', title="Register",
                                    username=username, email=email)

        except Exception as e:
            # Log the actual error e in a real application
            print(f"Error saving user: {e}") # Basic print for debugging
            flash('An error occurred while creating your account. Please try again later.', 'danger')
            return render_template('auth/register.html', title="Register",
                                   username=username, email=email)

    # --- GET Request ---
    return render_template('auth/register.html', title="Register")

# ... (logout route remains the same) ...