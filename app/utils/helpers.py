"""
app/utils/helpers.py
---------------------
Reusable Flask helpers for FlowDesk.

Contains:
- success_response()  → standardised 200/201 JSON
- error_response()    → standardised 4xx/5xx JSON
- login_required      → decorator that blocks unauthenticated requests

Why centralise responses here?
  If you ever need to change the response format (e.g. add a
  'timestamp' field to every response), you change it in ONE
  place and it applies everywhere automatically.
"""

import logging
from functools import wraps
from flask import jsonify, session, redirect, url_for, request

logger = logging.getLogger(__name__)


# ── Response Helpers ───────────────────────────────────────────────────────────

def success_response(data=None, message: str = "Success", status_code: int = 200):
    """
    Build a standardised success JSON response.

    Args:
        data:        The payload to return (dict, list, or None).
        message:     Human-readable success message.
        status_code: HTTP status code (200 = OK, 201 = Created).

    Returns:
        Flask Response object + HTTP status code tuple.

    Example output:
        {
            "success": true,
            "message": "Task created.",
            "data": { "id": 1, "title": "Buy milk", ... }
        }
    """
    payload = {
        "success": True,
        "message": message,
    }

    # Only include 'data' key if there is actually data to send.
    # Avoids returning { "data": null } on delete operations.
    if data is not None:
        payload["data"] = data

    return jsonify(payload), status_code


def error_response(message: str = "An error occurred.", status_code: int = 400):
    """
    Build a standardised error JSON response.

    Args:
        message:     Human-readable error description.
        status_code: HTTP error code.
                     400 = Bad Request (client sent bad data)
                     401 = Unauthorised (not logged in)
                     403 = Forbidden (logged in but not allowed)
                     404 = Not Found
                     500 = Internal Server Error (our bug)

    Returns:
        Flask Response object + HTTP status code tuple.

    Example output:
        {
            "success": false,
            "message": "Task title is required."
        }
    """
    payload = {
        "success": False,
        "message": message,
    }
    return jsonify(payload), status_code


# ── login_required Decorator ──────────────────────────────────────────────────

def login_required(f):
    """
    Decorator that protects routes from unauthenticated access.

    How it works:
        1. Checks if 'user_id' key exists in the session cookie.
        2. If yes → the original route function runs normally.
        3. If no  → returns 401 (API) or redirects to login (HTML page).

    Usage on any route:
        @tasks_bp.route("/api/tasks")
        @login_required          ← add this line
        def get_tasks():
            ...

    How sessions work in Flask:
        Flask stores session data in a signed cookie on the user's
        browser. The SECRET_KEY is used to sign it — without the key
        nobody can forge a session. We store user_id in the session
        at login and clear it at logout.
    """
    @wraps(f)
    # @wraps preserves the original function's name and docstring.
    # Without it, all decorated functions would appear as 'decorated'
    # in logs and error messages — very confusing to debug.
    def decorated_function(*args, **kwargs):

        if "user_id" not in session:
            # Distinguish between API calls and HTML page requests.
            # API calls get a JSON error; HTML requests get a redirect.
            if request.is_json or request.path.startswith("/api/"):
                logger.warning(
                    "Unauthenticated API request to %s", request.path
                )
                return error_response(
                    "Authentication required. Please log in.", 401
                )
            # For HTML pages → redirect to the login page
            return redirect(url_for("auth.login_page"))

        # User is authenticated — run the actual route function
        return f(*args, **kwargs)

    return decorated_function