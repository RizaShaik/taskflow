"""
run.py
------
Entry point for FlowDesk.
Run with: python run.py
"""

from app import create_app, socketio

# Create the app using settings from .env
app = create_app()

if __name__ == "__main__":
    # socketio.run() replaces the normal app.run()
    # It starts the server with WebSocket support.
    socketio.run(
        app,
        host="0.0.0.0",   # Accept connections from any IP (not just localhost)
        port=5000,
        debug=app.debug,
        use_reloader=True,
        allow_unsafe_werkzeug=True  # Required for eventlet in dev mode
    )