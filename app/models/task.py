"""
app/models/task.py
------------------
Task model — maps to the 'tasks' table in PostgreSQL.

Key decisions:
- Priority and Status use Python's Enum class.
  This means only valid values ("low", "medium", "high") can ever
  reach the database. Anything else raises a Python error before
  the query even runs — safer than checking in the route.
- updated_at uses onupdate= so it automatically refreshes
  every time the row is changed.
"""

from datetime import datetime, timezone
import enum
from app import db


# ── Enums ──────────────────────────────────────────────────────────────────────
# str + enum.Enum means the enum value IS the string.
# Priority.HIGH.value == "high"
# This is important for JSON serialisation later.

class Priority(str, enum.Enum):
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"


class Status(str, enum.Enum):
    PENDING     = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED   = "completed"


# ── Model ──────────────────────────────────────────────────────────────────────

class Task(db.Model):
    __tablename__ = "tasks"

    # ── Columns ───────────────────────────────────────────────────────────────
    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(
        db.String(200),
        nullable=False          # Every task must have a title
    )

    description = db.Column(
        db.Text,
        nullable=True           # Description is optional
    )

    priority = db.Column(
        # db.Enum() creates a PostgreSQL ENUM type.
        # name= is what the type is called inside PostgreSQL.
        db.Enum(
        Priority,
        values_callable=lambda obj: [e.value for e in obj],
        name="priority_enum"
        ),
        nullable=False,
        default=Priority.MEDIUM # Default is medium if not specified
    )

    status = db.Column(
        db.Enum(
        Status,
        values_callable=lambda obj: [e.value for e in obj],
        name="status_enum"
        ),
        nullable=False,
        default=Status.PENDING  # New tasks start as pending
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        # onupdate= runs this lambda every time the row is UPDATED
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # ── Foreign Key ───────────────────────────────────────────────────────────
    # This column stores the id of the User who owns this task.
    # ForeignKey("users.id") enforces referential integrity at the DB level:
    # you cannot insert a task with a user_id that doesn't exist in users.
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True   # We'll frequently query tasks WHERE user_id = X
    )

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """
        JSON-safe dictionary representation.

        Note: .value is needed on enums to get the string ("high"),
        not the Python object (Priority.HIGH).
        """
        return {
            "id":          self.id,
            "title":       self.title,
            "description": self.description,
            "priority":    self.priority.value,
            "status":      self.status.value,
            "created_at":  self.created_at.isoformat(),
            "updated_at":  self.updated_at.isoformat(),
            "user_id":     self.user_id,
        }

    def __repr__(self) -> str:
        return f"<Task id={self.id} title='{self.title[:30]}'>"