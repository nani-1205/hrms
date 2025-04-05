from hrms import create_app

app = create_app()

if __name__ == '__main__':
    # Get host and port from config or use defaults
    # host = app.config.get('HOST', '0.0.0.0') # Example if reading from config
    # port = app.config.get('PORT', 5000)      # Example if reading from config

    host = '0.0.0.0'  # Listen on all available network interfaces
    port = 5000       # Default Flask port, change if needed
    debug = app.config['DEBUG'] # Get debug status from config

    print(f" * Starting Flask development server on http://{host}:{port}")
    print(f"   Accessible externally at http://<YOUR_MACHINE_IP>:{port}")
    # Use Flask's built-in server for development
    # For production, use a WSGI server like Gunicorn or uWSGI
    app.run(host=host, port=port, debug=debug)