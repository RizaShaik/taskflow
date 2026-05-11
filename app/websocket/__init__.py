# app/websocket/__init__.py
# Importing events registers all @socketio.on() handlers.
# The import is used for its side effect (handler registration),
# not for any specific name — hence the noqa comment.

from app.websocket import events  # noqa: F401