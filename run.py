# hrms_project/run.py

from hrms import create_app

app = create_app()

if __name__ == '__main__':
    # Get host and port from config or use defaults
    # You could add HOST and PORT to your .env and Config class
    host = app.config.get('HOST', '0.0.0.0')
    port = app.config.get('PORT', 5000)
    debug = app.config['DEBUG']

    print(f" * Starting Flask development server on http://{host}:{port}")
    # Use Flask's built-in server for development
    # host='0.0.0.0' makes it accessible on your network IP address
    # For production, use a WSGI server like Gunicorn or uWSGI
    app.run(host=host, port=port, debug=debug)