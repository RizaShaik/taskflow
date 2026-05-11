"""
app/services/auth_service.py
-----------------------------
Authentication business logic for FlowDesk.

This file handles:
- Creating new user accounts (register)
- Verifying credentials (login)

Why is this a class with static methods instead of plain functions?
- Groups related operations together under one namespace
- Called as AuthService.register() which reads clearly in routes
- Static methods because we don't need to store any state —
  every method is self-contained and just does its job

What this file deliberately does NOT do:
- Touch the Flask session (that's the route's job)
- Return HTTP responses (that's the route's job)
- Validate input format (that's validators.py's job)
  It only raises ValueError if business rules are violated
  (e.g. email already registered)
"""

import logging
from app import db
from app.models.user import User

# Get a logger for this module.
# __name__ will be 'app.services.auth_service' — makes log messages
# easy to trace back to this exact file.
logger = logging.getLogger(__name__)


class AuthService:
    """Handles all user authentication operations."""

    @staticmethod
    def register(username: str, email: str, password: str) -> User:
        """
        Create and persist a new user account.

        Steps:
            1. Normalise the inputs (strip whitespace, lowercase email)
            2. Check username isn't already taken
            3. Check email isn't already registered
            4. Create User object, hash the password
            5. Save to database
            6. Return the new User

        Args:
            username: Desired username (already format-validated)
            email:    User's email address
            password: Plain-text password (we hash it here)

        Returns:
            The newly created User object.

        Raises:
            ValueError: If username or email is already taken.

        Why we check BOTH username and email separately:
            Gives the user a specific, actionable error message.
            "Username taken" vs "Email already registered" —
            much more helpful than a generic "registration failed".
        """
        # Normalise inputs
        # .strip() removes accidental leading/trailing spaces
        # .lower() on email means john@gmail.com == JOHN@GMAIL.COM
        username = username.strip()
        email    = email.strip().lower()

        # ── Check for conflicts ────────────────────────────────────────────────
        # .first() returns the User object if found, or None if not.
        # We only care about existence, not the actual object.
        existing_username = User.query.filter_by(username=username).first()
        if existing_username:
            raise ValueError("That username is already taken.")

        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            raise ValueError("An account with this email already exists.")

        # ── Create the user ────────────────────────────────────────────────────
        user = User(username=username, email=email)

        # set_password() hashes the password before storing it.
        # After this call, user.password_hash is something like:
        # "pbkdf2:sha256:600000$x7Km..." — the original is gone forever.
        user.set_password(password)

        # ── Persist to database ────────────────────────────────────────────────
        # db.session.add() stages the new user (like git add)
        # db.session.commit() writes it to PostgreSQL (like git commit)
        # If commit() fails (e.g. DB connection drops), SQLAlchemy
        # automatically rolls back so we never have partial data.
        db.session.add(user)
        db.session.commit()

        logger.info("New user registered: id=%s username=%s", user.id, username)
        return user

    @staticmethod
    def login(email: str, password: str) -> User:
        """
        Verify login credentials and return the User.

        Steps:
            1. Normalise email
            2. Find user by email
            3. Check password hash matches
            4. Return User if valid

        Args:
            email:    The submitted email address.
            password: The submitted plain-text password.

        Returns:
            The authenticated User object.

        Raises:
            ValueError: If credentials are invalid.

        Security note — NEVER reveal which part is wrong:
            "Invalid email or password" is the correct message.
            NOT "email not found" or "wrong password".
            The latter two let attackers probe which emails
            are registered in your system.
        """
        email = email.strip().lower()

        # Look up user by email
        user = User.query.filter_by(email=email).first()

        # check_password() runs the hash comparison.
        # If user is None, we use 'not user' to short-circuit
        # before calling check_password — avoids AttributeError.
        if not user or not user.check_password(password):
            # Same error for both cases — intentionally vague
            raise ValueError("Invalid email or password.")

        logger.info("User logged in: id=%s username=%s", user.id, user.username)
        return user