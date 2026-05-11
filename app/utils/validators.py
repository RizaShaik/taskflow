"""
app/utils/validators.py
------------------------
Input validation functions for FlowDesk.

Design principles:
- Zero Flask imports — these are pure Python functions.
  That means you can test them without starting a server.
- Each function raises ValueError with a clear human-readable
  message on failure. The route catches ValueError and turns
  it into a 400 JSON response.
- Each function returns None on success (no news is good news).

Why raise ValueError instead of returning True/False?
  Returning False tells you something is wrong.
  Raising ValueError tells you WHAT is wrong.
  The route can pass the message directly to the user.
"""

import re

# ── Constants ──────────────────────────────────────────────────────────────────

# Valid values for priority and status.
# Using sets for O(1) lookup — faster than lists for membership checks.
VALID_PRIORITIES = {"low", "medium", "high"}
VALID_STATUSES   = {"pending", "in_progress", "completed"}

# Basic email pattern: something@something.something
# Not 100% RFC-compliant but catches obvious mistakes.
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ── Registration Validator ─────────────────────────────────────────────────────

def validate_registration(data: dict) -> None:
    """
    Validate user registration payload.

    Expected keys: username, email, password

    Raises:
        ValueError: with a description of what's wrong.

    Example usage:
        try:
            validate_registration(request.get_json())
        except ValueError as e:
            return error_response(str(e), 400)
    """
    # .get() safely returns None if key is missing.
    # 'or ""' turns None into "" so .strip() doesn't crash.
    username = (data.get("username") or "").strip()
    email    = (data.get("email")    or "").strip()
    password =  data.get("password") or ""

    # ── Username checks ────────────────────────────────────────────────────────
    if not username:
        raise ValueError("Username is required.")

    if len(username) < 3:
        raise ValueError("Username must be at least 3 characters.")

    if len(username) > 80:
        raise ValueError("Username must be 80 characters or fewer.")

    # Only allow letters, numbers, underscores, hyphens
    if not re.match(r"^[a-zA-Z0-9_-]+$", username):
        raise ValueError("Username can only contain letters, numbers, _ and -")

    # ── Email checks ───────────────────────────────────────────────────────────
    if not email:
        raise ValueError("Email is required.")

    if not EMAIL_REGEX.match(email):
        raise ValueError("Please enter a valid email address.")

    # ── Password checks ────────────────────────────────────────────────────────
    if not password:
        raise ValueError("Password is required.")

    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters.")

    if len(password) > 128:
        raise ValueError("Password must be 128 characters or fewer.")


# ── Login Validator ────────────────────────────────────────────────────────────

def validate_login(data: dict) -> None:
    """
    Validate login payload.

    Expected keys: email, password

    We keep this intentionally vague — we don't tell the user
    whether their email OR password is wrong (security best practice:
    an attacker shouldn't be able to confirm which emails are registered).
    """
    email    = (data.get("email")    or "").strip()
    password =  data.get("password") or ""

    if not email:
        raise ValueError("Email is required.")

    if not password:
        raise ValueError("Password is required.")


# ── Task Validator ─────────────────────────────────────────────────────────────

def validate_task(data: dict, *, is_update: bool = False) -> None:
    """
    Validate task create/update payload.

    Args:
        data:       The JSON body from the request.
        is_update:  If True, title is optional (partial updates allowed).
                    If False (create), title is required.

    Expected keys: title, description (optional), priority, status

    The * in the signature forces is_update to be passed as a keyword:
        validate_task(data, is_update=True)   ← correct
        validate_task(data, True)             ← TypeError — intentional
    """
    title       = (data.get("title")       or "").strip()
    description = (data.get("description") or "").strip()
    priority    = (data.get("priority")    or "").strip().lower()
    status      = (data.get("status")      or "").strip().lower()

    # ── Title ──────────────────────────────────────────────────────────────────
    # Required on create, optional on update
    if not is_update and not title:
        raise ValueError("Task title is required.")

    if title and len(title) > 200:
        raise ValueError("Title must be 200 characters or fewer.")

    # ── Description ────────────────────────────────────────────────────────────
    if description and len(description) > 2000:
        raise ValueError("Description must be 2000 characters or fewer.")

    # ── Priority ───────────────────────────────────────────────────────────────
    # Only validate if a value was actually provided
    if priority and priority not in VALID_PRIORITIES:
        raise ValueError(
            f"Priority must be one of: {', '.join(sorted(VALID_PRIORITIES))}."
        )

    # ── Status ─────────────────────────────────────────────────────────────────
    if status and status not in VALID_STATUSES:
        raise ValueError(
            f"Status must be one of: {', '.join(sorted(VALID_STATUSES))}."
        )