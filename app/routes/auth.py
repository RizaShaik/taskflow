"""
app/routes/auth.py
-------------------
Authentication Blueprint for FlowDesk.

URL prefix: /auth
All routes in this file start with /auth automatically.

Routes:
    GET  /auth/login          → serve login HTML page
    GET  /auth/register       → serve register HTML page
    POST /auth/api/register   → create new account (JSON API)
    POST /auth/api/login      → verify credentials, create session (JSON API)
    POST /auth/api/logout     → clear session (JSON API)

Convention used here:
    HTML page routes  → no /api/ in the path, return render_template()
    API routes        → /api/ in the path, return JSON via success/error_response()
"""

import logging
from flask import (
    Blueprint,
    request,
    session,
    redirect,
    url_for,
    render_template,
)
from app.services.auth_service import AuthService
from app.utils.validators import validate_registration, validate_login
from app.utils.helpers import success_response, error_response

logger = logging.getLogger(__name__)

# ── Create Blueprint ────────────────────────────────────────────────────────────
# "auth"         → the name used in url_for("auth.login_page")
# __name__       → tells Flask where this blueprint lives
# url_prefix     → prepends /auth to every route in this file
auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


# ══════════════════════════════════════════════════════════════════════════════
# HTML PAGE ROUTES
# These routes return rendered HTML — the browser navigates to them directly.
# ══════════════════════════════════════════════════════════════════════════════

@auth_bp.route("/login")
def login_page():
    """
    GET /auth/login
    Serve the login HTML page.

    If the user is already logged in, redirect to dashboard.
    No point showing the login form to someone already authenticated.
    """
    if "user_id" in session:
        return redirect(url_for("dashboard.index"))
    return render_template("auth/login.html")


@auth_bp.route("/register")
def register_page():
    """
    GET /auth/register
    Serve the registration HTML page.

    Same logic — redirect logged-in users away from this page.
    """
    if "user_id" in session:
        return redirect(url_for("dashboard.index"))
    return render_template("auth/register.html")


# ══════════════════════════════════════════════════════════════════════════════
# JSON API ROUTES
# These routes are called by JavaScript fetch() — they return JSON, not HTML.
# ══════════════════════════════════════════════════════════════════════════════

@auth_bp.route("/api/register", methods=["POST"])
def register():
    """
    POST /auth/api/register

    Expected JSON body:
        {
            "username": "johndoe",
            "email":    "john@example.com",
            "password": "mypassword123"
        }

    Success response (201 Created):
        {
            "success": true,
            "message": "Account created successfully.",
            "data": { "id": 1, "username": "johndoe", ... }
        }

    Error response (400 Bad Request):
        {
            "success": false,
            "message": "That username is already taken."
        }
    """
    # request.get_json() parses the JSON body from the request.
    # silent=True means it returns None instead of raising an error
    # if the body isn't valid JSON or Content-Type isn't application/json.
    # 'or {}' means if we get None, use an empty dict — safe to call
    # .get() on without crashing.
    data = request.get_json(silent=True) or {}

    # ── Step 1: Validate input format ─────────────────────────────────────────
    # validate_registration raises ValueError with a message if invalid.
    # We catch it and turn it into a 400 JSON error response.
    try:
        validate_registration(data)
    except ValueError as exc:
        return error_response(str(exc), 400)

    # ── Step 2: Business logic (check duplicates, create user) ────────────────
    # AuthService.register raises ValueError if username/email taken.
    # We also catch generic Exception for unexpected DB errors.
    try:
        user = AuthService.register(
            username=data["username"],
            email=data["email"],
            password=data["password"],
        )
        # 201 Created is the correct HTTP status for resource creation
        return success_response(
            data=user.to_dict(),
            message="Account created successfully.",
            status_code=201,
        )
    except ValueError as exc:
        # Business rule violation — e.g. "username already taken"
        return error_response(str(exc), 400)
    except Exception:
        # Something unexpected — log full traceback, return generic message.
        # Never expose internal error details to the client.
        logger.exception("Unexpected error during registration")
        return error_response("Registration failed. Please try again.", 500)


@auth_bp.route("/api/login", methods=["POST"])
def login():
    """
    POST /auth/api/login

    Expected JSON body:
        {
            "email":    "john@example.com",
            "password": "mypassword123"
        }

    On success:
        - Creates a server-side session (encrypted cookie)
        - Returns user data

    Success response (200 OK):
        {
            "success": true,
            "message": "Logged in successfully.",
            "data": { "id": 1, "username": "johndoe", ... }
        }

    Error response (401 Unauthorized):
        {
            "success": false,
            "message": "Invalid email or password."
        }
    """
    data = request.get_json(silent=True) or {}

    # ── Step 1: Validate that fields are present ───────────────────────────────
    try:
        validate_login(data)
    except ValueError as exc:
        return error_response(str(exc), 400)

    # ── Step 2: Verify credentials ─────────────────────────────────────────────
    try:
        user = AuthService.login(
            email=data["email"],
            password=data["password"],
        )

        # ── Step 3: Create the session ─────────────────────────────────────────
        # session.permanent = True makes the session last beyond the browser close.
        # Flask uses the PERMANENT_SESSION_LIFETIME config to set expiry
        # (default is 31 days). Without this, session clears when browser closes.
        session.permanent = True

        # Store the minimum needed to identify the user on future requests.
        # We store username too so we can display it without a DB query.
        session["user_id"]  = user.id
        session["username"] = user.username

        logger.info(
            "Session created for user_id=%s username=%s",
            user.id, user.username
        )

        return success_response(
            data=user.to_dict(),
            message="Logged in successfully.",
        )

    except ValueError as exc:
        # 401 = Unauthorized — credentials didn't match
        return error_response(str(exc), 401)
    except Exception:
        logger.exception("Unexpected error during login")
        return error_response("Login failed. Please try again.", 500)


@auth_bp.route("/api/logout", methods=["POST"])
def logout():
    """
    POST /auth/api/logout

    Clears the session — the user is now logged out.
    The encrypted cookie on the browser becomes empty/invalid.

    No authentication check needed here —
    if there's no session, clearing it is a no-op. Safe either way.

    Success response (200 OK):
        {
            "success": true,
            "message": "Logged out successfully."
        }
    """
    # Who is logging out (for logging — grab before clearing)
    user_id  = session.get("user_id",  "unknown")
    username = session.get("username", "unknown")

    # Wipe every key from the session
    session.clear()

    logger.info("User logged out: id=%s username=%s", user_id, username)

    return success_response(message="Logged out successfully.")