"""
app/__init__.py
---------------
Application Factory for FlowDesk.

Why a factory function instead of a global app object?
- Avoids circular imports (routes importing app, app importing routes)
- Makes testing easy — call create_app() with test config
- Industry standard pattern for Flask applications
"""

import logging
import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO

# ── Create extensions WITHOUT attaching them to an app yet ──────────────────
# We create these here so any file can import them:
#   from app import db
# But they have no app attached until create_app() calls .init_app()
db = SQLAlchemy()
socketio = SocketIO()


def create_app(env: str = None) -> Flask:
    """
    Create, configure, and return the Flask application.

    Args:
        env: 'development' or 'production'. Defaults to FLASK_ENV env var.

    Returns:
        Fully configured Flask application instance.
    """
    from config.settings import config_map

    # Create the Flask app.
    # __name__ tells Flask where to look for templates and static files.
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "..", "templates"),
        static_folder=os.path.join(os.path.dirname(__file__), "..", "static"),
    )

    # ── Load config ───────────────────────────────────────────────────────────
    env = env or os.environ.get("FLASK_ENV", "development")
    app.config.from_object(config_map.get(env, config_map["development"]))

    # ── Set up logging ────────────────────────────────────────────────────────
    # This prints useful info to your terminal as the app runs.
    logging.basicConfig(
        level=logging.DEBUG if app.debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # ── Attach extensions to this app ─────────────────────────────────────────
    # .init_app() connects the extension to our specific Flask instance.
    db.init_app(app)
    socketio.init_app(
        app,
        async_mode=app.config["SOCKETIO_ASYNC_MODE"],
        cors_allowed_origins="*",
        logger=False,
        engineio_logger=False,
    )

# ── Register Blueprints ────────────────────────────────────────────────────
    from app.routes.auth      import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.tasks     import tasks_bp
    from app.routes.analytics import analytics_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(analytics_bp)

    # ── Register WebSocket handlers ────────────────────────────────────────────
    from app.websocket import events  # noqa: F401

    # ── Create all database tables ────────────────────────────────────────────
    # app_context() is required any time you access the database
    # outside of a request. create_all() reads our models and builds
    # the tables in PostgreSQL if they don't exist yet.
    with app.app_context():
        from app.models import User, Task  # noqa — needed to register metadata
        db.create_all()
        logging.info("Database tables verified/created.")

    return app