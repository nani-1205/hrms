# run.py
from hrms import create_app
import os

# Create the Flask app instance using the factory function
app = create_app()

if __name__ == '__main__':
    # Configuration for Flask's built-in development server
    # Get host/port/debug settings primarily from Flask config (loaded from .env)
    host = os.environ.get('FLASK_RUN_HOST', app.config.get('HOST', '0.0.0.0'))
    port = int(os.environ.get('FLASK_RUN_PORT', app.config.get('PORT', 5000)))
    debug = app.config.get('DEBUG', False)

    print(f" * Starting Flask development server on http://{host}:{port}")
    # Attempt to display accessible network IP if listening on 0.0.0.0
    if host == '0.0.0.0':
        try:
            import socket
            # Connect to an external address to find the primary local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.1) # Avoid long wait if no connection
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            print(f"   Accessible externally at http://{local_ip}:{port}")
        except Exception:
            # Fallback message if IP detection fails
            print(f"   Accessible externally (check your machine's network IP address)")

    print(f" * Debug mode: {'on' if debug else 'off'}")
    # Important: DO NOT use app.run() in a production environment.
    # Use a production-ready WSGI server like Gunicorn or uWSGI.
    app.run(host=host, port=port, debug=debug)