"""
config/settings.py
------------------
Central configuration for FlowDesk.

Why use config classes?
- Keeps all settings in one place
- Lets you switch between dev/prod easily
- No secrets hardcoded anywhere
"""

import os
from dotenv import load_dotenv

# load_dotenv() reads the .env file and pushes every
# variable into os.environ so we can read them below.
load_dotenv()


class Config:
    """
    Base configuration — shared by ALL environments.
    Child classes (Dev, Prod) override only what's different.
    """

    # Flask uses this to sign session cookies.
    # If someone gets this key they can forge sessions — keep it secret.
    SECRET_KEY = os.environ.get("SECRET_KEY", "fallback-key-CHANGE-THIS")

    # SQLAlchemy connection string: tells it which database to use.
    # Format: postgresql://username:password@host:port/database_name
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:password@localhost:5432/taskflow"
    )

    # Disables a SQLAlchemy feature we don't need.
    # Leaving it True floods your terminal with warnings.
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Which async mode Flask-SocketIO should use.
    # 'eventlet' is the most compatible option.
    SOCKETIO_ASYNC_MODE = os.environ.get("SOCKETIO_ASYNC_MODE", "eventlet")


class DevelopmentConfig(Config):
    """Development settings — debug mode ON, verbose errors."""
    DEBUG = True


class ProductionConfig(Config):
    """Production settings — debug mode OFF, no error details exposed."""
    DEBUG = False


# This dictionary lets run.py select a config by name:
# e.g., config_map["development"] gives DevelopmentConfig
config_map = {
    "development": DevelopmentConfig,
    "production":  ProductionConfig,
}