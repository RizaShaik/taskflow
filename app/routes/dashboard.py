"""
app/routes/dashboard.py
------------------------
Serves the main dashboard HTML page.

Why is this separate from auth.py?
    auth.py handles authentication logic.
    dashboard.py handles page rendering.
    Single responsibility — each file has one job.

Routes:
    GET /        → redirect to dashboard or login
    GET /dashboard → render the main dashboard page
"""

from flask import Blueprint, render_template, redirect, url_for, session
from app.utils.helpers import login_required

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def root():
    """
    GET /
    Root URL — redirect based on auth state.

    Logged in  → go to dashboard
    Logged out → go to login page
    """
    if "user_id" in session:
        return redirect(url_for("dashboard.index"))
    return redirect(url_for("auth.login_page"))


@dashboard_bp.route("/dashboard")
@login_required
def index():
    """
    GET /dashboard
    Render the main dashboard.

    @login_required ensures only authenticated users reach this.
    We pass username to the template so it can display it
    without making an extra database call.
    """
    return render_template(
        "dashboard/index.html",
        username=session.get("username", "User")
    )
