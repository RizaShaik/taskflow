"""
app/models/user.py
------------------
User model — maps to the 'users' table in PostgreSQL.

Key decisions:
- Passwords are NEVER stored as plain text.
  We use Werkzeug's generate_password_hash() which runs bcrypt,
  turning "mypassword123" into something like:
  "pbkdf2:sha256:600000$abc123..."
- The 'tasks' relationship lets us do user.tasks to get all
  tasks belonging to that user — SQLAlchemy handles the JOIN.
"""

from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


class User(db.Model):
    # This tells SQLAlchemy which PostgreSQL table this class maps to.
    __tablename__ = "users"

    # ── Columns ───────────────────────────────────────────────────────────────
    id = db.Column(
        db.Integer,
        primary_key=True       # Auto-increments: 1, 2, 3, ...
    )

    username = db.Column(
        db.String(80),
        unique=True,           # No two users can share a username
        nullable=False,        # Cannot be empty
        index=True             # Creates a DB index — makes lookups faster
    )

    email = db.Column(
        db.String(120),
        unique=True,           # No two users can share an email
        nullable=False,
        index=True
    )

    password_hash = db.Column(
        db.String(256),
        nullable=False         # We always store the hash, never the real password
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        # default= is called once per new row.
        # lambda ensures it's evaluated at insert time, not import time.
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # ── Relationship ──────────────────────────────────────────────────────────
    # This is NOT a column. It's a Python-level link between User and Task.
    # 'backref="owner"' means every Task gets a .owner attribute pointing
    # back to its User — so task.owner gives you the User object.
    # 'cascade="all, delete-orphan"' means if a user is deleted,
    # all their tasks are automatically deleted too.
    tasks = db.relationship(
        "Task",
        backref="owner",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )

    # ── Password Methods ──────────────────────────────────────────────────────

    def set_password(self, password: str) -> None:
        """
        Hash the plain-text password and store only the hash.

        Example:
            user.set_password("mypassword123")
            # user.password_hash is now "pbkdf2:sha256:600000$..."
        """
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """
        Compare a plain-text password against the stored hash.

        Returns:
            True if password matches, False otherwise.

        Example:
            user.check_password("mypassword123")  # → True
            user.check_password("wrongpassword")  # → False
        """
        return check_password_hash(self.password_hash, password)

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """
        Convert this User to a dictionary for JSON responses.
        Notice: password_hash is NOT included — never send that to the client.
        """
        return {
            "id":         self.id,
            "username":   self.username,
            "email":      self.email,
            "created_at": self.created_at.isoformat(),
        }

    def __repr__(self) -> str:
        """How this object appears when printed — useful for debugging."""
        return f"<User id={self.id} username={self.username}>"