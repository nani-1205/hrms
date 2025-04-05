# run.py
from hrms import create_app, get_db # Import get_db if User model needs it directly (usually uses it internally)
from hrms.models.user import User # Import the User model
import os
import click # Import Flask's integrated Click library

# Create the Flask app instance using the factory function
app = create_app()

# --- Define CLI Commands ---

@app.cli.command("create-admin")
@click.option('--username', prompt=True, default='admin', help='The username for the admin account.')
@click.option('--email', prompt=True, help='The email address for the admin account.')
@click.password_option(confirmation_prompt=True, help='The password for the admin account.')
def create_admin_user(username, email, password):
    """Creates the initial administrator user."""
    with app.app_context(): # Ensure we are within the application context to use get_db()
        log = app.logger # Get the app's logger

        log.info(f"Attempting to create admin user: username='{username}', email='{email}'")

        # Basic validation
        if not username or not email or not password:
            click.echo("Error: Username, email, and password are required.")
            log.error("Admin creation failed: Missing required fields.")
            return

        # Check if admin or user with same username/email already exists
        existing_admin = User.get_collection().find_one({"role": "admin"})
        if existing_admin:
            click.echo(f"Error: An admin user ('{existing_admin['username']}') already exists.")
            log.warning("Admin creation aborted: Admin user already exists.")
            return

        existing_username = User.get_by_username(username)
        if existing_username:
            click.echo(f"Error: Username '{username}' is already taken.")
            log.warning(f"Admin creation aborted: Username '{username}' already exists.")
            return

        existing_email = User.get_by_email(email.lower())
        if existing_email:
            click.echo(f"Error: Email '{email}' is already registered.")
            log.warning(f"Admin creation aborted: Email '{email}' already exists.")
            return

        # Create the new admin user object
        try:
            admin_user = User(
                username=username,
                email=email.lower(), # Store email lowercase
                role='admin',       # Set the role explicitly
                is_active=True      # Ensure admin is active by default
            )
            admin_user.set_password(password) # Hash the password

            # Save the user to the database
            new_id = admin_user.save()

            if new_id:
                click.echo(f"Admin user '{username}' created successfully with ID: {new_id}")
                log.info(f"Admin user '{username}' created successfully.")
            else:
                # This might happen if save() returned None due to an internal error (like duplicate key race condition)
                click.echo("Error: Failed to save admin user to the database. Check application logs.")
                log.error("Admin creation failed: User.save() returned None.")

        except Exception as e:
            click.echo(f"An unexpected error occurred: {e}")
            log.error(f"Admin creation failed: Unexpected error - {e}", exc_info=True)


# --- Run the Development Server ---
if __name__ == '__main__':
    # Configuration for Flask's built-in development server
    host = os.environ.get('FLASK_RUN_HOST', app.config.get('HOST', '0.0.0.0'))
    port = int(os.environ.get('FLASK_RUN_PORT', app.config.get('PORT', 5000)))
    debug = app.config.get('DEBUG', False)

    print(f" * Starting Flask development server on http://{host}:{port}")
    if host == '0.0.0.0':
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.1)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            print(f"   Accessible externally at http://{local_ip}:{port}")
        except Exception:
            print(f"   Accessible externally (check your machine's network IP address)")

    print(f" * Debug mode: {'on' if debug else 'off'}")
    app.run(host=host, port=port, debug=debug)