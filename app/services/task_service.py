"""
app/services/task_service.py
-----------------------------
Task CRUD business logic for FlowDesk.

Handles:
- Fetching all tasks for a user
- Fetching one task by ID
- Creating a task
- Updating a task (partial updates supported)
- Deleting a task

Security principle applied throughout:
    Every query includes BOTH task_id AND user_id.
    This means user A can never read, edit, or delete
    user B's tasks — even if they guess the task ID.
    This attack is called "Insecure Direct Object Reference" (IDOR)
    and is in the OWASP Top 10 security list. We prevent it here.

Example of the vulnerability we prevent:
    Task ID 5 belongs to user 1.
    User 2 sends: DELETE /api/tasks/5
    Without user_id check: task 5 gets deleted. BAD.
    With user_id check: "Task not found" returned. SAFE.
"""

import logging
from app import db
from app.models.task import Task, Priority, Status

logger = logging.getLogger(__name__)


class TaskService:
    """Handles all task lifecycle operations."""

    @staticmethod
    def get_all(user_id: int) -> list:
        """
        Return all tasks belonging to a specific user.

        Args:
            user_id: The ID of the logged-in user.

        Returns:
            List of Task objects, newest first.

        Why order_by(Task.created_at.desc())?
            Most recently created tasks appear at the top
            of the list — what users expect from a task manager.
        """
        tasks = (
            Task.query
            .filter_by(user_id=user_id)
            .order_by(Task.created_at.desc())
            .all()
        )
        logger.debug("Fetched %d tasks for user_id=%s", len(tasks), user_id)
        return tasks

    @staticmethod
    def get_by_id(task_id: int, user_id: int) -> Task:
        """
        Return a single task, verified to belong to this user.

        Args:
            task_id: The task's primary key.
            user_id: The logged-in user's ID.

        Returns:
            Task object if found and owned by user.

        Raises:
            ValueError: If no matching task exists.

        Why filter by BOTH task_id AND user_id?
            See the IDOR explanation in the module docstring.
            filter_by() with both conditions produces:
            WHERE id = task_id AND user_id = user_id
        """
        task = Task.query.filter_by(id=task_id, user_id=user_id).first()

        if not task:
            # We say "not found" rather than "not yours" —
            # don't confirm the task exists to unauthorised users
            raise ValueError("Task not found.")

        return task

    @staticmethod
    def create(user_id: int, data: dict) -> Task:
        """
        Create and persist a new task.

        Args:
            user_id: Owner of the new task.
            data:    Validated dictionary with task fields.

        Returns:
            The newly created Task object.

        Why Priority(data.get("priority", "medium"))?
            Priority is an Enum. Passing the string "high" to
            Priority() converts it to Priority.HIGH.
            If the string isn't valid, Python raises ValueError —
            but validate_task() runs first so this never happens.
        """
        task = Task(
            title=data["title"].strip(),
            description=(data.get("description") or "").strip(),
            priority=Priority(data.get("priority", "medium")),
            status=Status(data.get("status", "pending")),
            user_id=user_id,
        )

        db.session.add(task)
        db.session.commit()

        logger.info(
            "Task created: id=%s title='%s' user_id=%s",
            task.id, task.title[:30], user_id
        )
        return task

    @staticmethod
    def update(task_id: int, user_id: int, data: dict) -> Task:
        """
        Partially update an existing task.

        Only fields present in data are changed.
        Missing fields keep their current value.

        This is a PATCH-style update even though our route uses PUT.
        Why? It's simpler for the frontend — it only needs to send
        the fields it wants to change.

        Args:
            task_id: The task to update.
            user_id: Must match task's owner (security check).
            data:    Dictionary of fields to update (any subset).

        Returns:
            The updated Task object.

        Raises:
            ValueError: If task not found or not owned by user.

        Example:
            # Only update status, leave everything else unchanged:
            TaskService.update(1, 5, {"status": "completed"})
        """
        # get_by_id already checks ownership — raises ValueError if not found
        task = TaskService.get_by_id(task_id, user_id)

        # Only update fields that were actually sent in the request.
        # 'if "title" in data' is different from 'if data.get("title")' —
        # the latter would skip updating if title is an empty string,
        # but we want to catch that case in the validator instead.

        if "title" in data and data["title"]:
            task.title = data["title"].strip()

        if "description" in data:
            # Allow setting description to empty string (clearing it)
            task.description = (data["description"] or "").strip()

        if "priority" in data and data["priority"]:
            # Convert string → Enum: "high" → Priority.HIGH
            task.priority = Priority(data["priority"].lower())

        if "status" in data and data["status"]:
            task.status = Status(data["status"].lower())

        # SQLAlchemy detects that 'task' was modified and will
        # UPDATE only the changed columns. updated_at refreshes
        # automatically via the onupdate= setting in the model.
        db.session.commit()

        logger.info("Task updated: id=%s user_id=%s", task_id, user_id)
        return task

    @staticmethod
    def delete(task_id: int, user_id: int) -> None:
        """
        Delete a task permanently.

        Args:
            task_id: The task to delete.
            user_id: Must match task's owner.

        Returns:
            None

        Raises:
            ValueError: If task not found or not owned by user.

        Why return None instead of the deleted task?
            Once deleted, the object is detached from the session.
            Accessing its attributes after commit() is unreliable.
            The route just needs to know it succeeded.
        """
        task = TaskService.get_by_id(task_id, user_id)

        db.session.delete(task)
        db.session.commit()

        logger.info("Task deleted: id=%s user_id=%s", task_id, user_id)