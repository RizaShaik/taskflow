"""
app/routes/tasks.py
--------------------
Task REST API Blueprint for FlowDesk.

URL prefix: /api/tasks
All routes require authentication (@login_required).

Endpoints:
    GET    /api/tasks         → get all tasks for current user
    POST   /api/tasks         → create a new task
    GET    /api/tasks/<id>    → get one task
    PUT    /api/tasks/<id>    → update a task
    DELETE /api/tasks/<id>    → delete a task

Architecture reminder:
    Routes are intentionally thin — they:
        1. Read the request
        2. Call a validator
        3. Call a service method
        4. Emit a WebSocket event (on writes)
        5. Return a response

    All actual logic lives in TaskService (services/task_service.py).
    This keeps each route under ~20 lines of real code.
"""

import logging
from flask import Blueprint, request, session
from app.services.task_service import TaskService
from app.utils.validators import validate_task
from app.utils.helpers import success_response, error_response, login_required
from app.websocket.events import emit_task_event

logger = logging.getLogger(__name__)

# ── Blueprint setup ────────────────────────────────────────────────────────────
# url_prefix="/api/tasks" means:
#   @tasks_bp.route("")         → /api/tasks
#   @tasks_bp.route("/<int:id>") → /api/tasks/5
tasks_bp = Blueprint("tasks", __name__, url_prefix="/api/tasks")


# ── Private helper ─────────────────────────────────────────────────────────────

def _uid() -> int:
    """
    Return the current user's ID from the session.

    Named _uid (underscore prefix) to signal it's internal to this module.
    Called in every route — keeps the routes clean.
    """
    return session["user_id"]


# ══════════════════════════════════════════════════════════════════════════════
# GET ALL TASKS
# ══════════════════════════════════════════════════════════════════════════════

@tasks_bp.route("", methods=["GET"])
@login_required
def get_tasks():
    """
    GET /api/tasks
    Return all tasks belonging to the logged-in user.

    No request body needed.

    Success response (200):
        {
            "success": true,
            "message": "Success",
            "data": [
                {
                    "id": 1,
                    "title": "Buy groceries",
                    "description": "Milk, eggs, bread",
                    "priority": "medium",
                    "status": "pending",
                    "created_at": "2024-01-15T10:00:00+00:00",
                    "updated_at": "2024-01-15T10:00:00+00:00",
                    "user_id": 3
                },
                ...
            ]
        }

    Why convert to list of dicts?
        Task objects from SQLAlchemy can't be directly JSON-serialised.
        .to_dict() converts each Task into a plain Python dictionary
        that jsonify() can turn into valid JSON.
    """
    try:
        tasks = TaskService.get_all(_uid())
        return success_response(
            data=[task.to_dict() for task in tasks]
        )
    except Exception:
        logger.exception("Error fetching tasks for user_id=%s", _uid())
        return error_response("Could not fetch tasks.", 500)


# ══════════════════════════════════════════════════════════════════════════════
# GET ONE TASK
# ══════════════════════════════════════════════════════════════════════════════

@tasks_bp.route("/<int:task_id>", methods=["GET"])
@login_required
def get_task(task_id: int):
    """
    GET /api/tasks/<task_id>
    Return a single task by its ID.

    The <int:task_id> in the route path means:
        - Flask extracts the number from the URL
        - Converts it to a Python int automatically
        - Passes it as the task_id parameter
        - If it's not a number (e.g. /api/tasks/abc), Flask returns 404

    Success response (200):
        { "success": true, "data": { ...task... } }

    Error response (404):
        { "success": false, "message": "Task not found." }
    """
    try:
        task = TaskService.get_by_id(task_id, _uid())
        return success_response(data=task.to_dict())
    except ValueError as exc:
        # ValueError from get_by_id means task doesn't exist
        # or belongs to another user — either way: 404
        return error_response(str(exc), 404)
    except Exception:
        logger.exception("Error fetching task_id=%s", task_id)
        return error_response("Could not fetch task.", 500)


# ══════════════════════════════════════════════════════════════════════════════
# CREATE TASK
# ══════════════════════════════════════════════════════════════════════════════

@tasks_bp.route("", methods=["POST"])
@login_required
def create_task():
    """
    POST /api/tasks
    Create a new task for the logged-in user.

    Request body (JSON):
        {
            "title":       "Finish the report",       ← required
            "description": "Q4 financial summary",    ← optional
            "priority":    "high",                    ← optional (default: medium)
            "status":      "pending"                  ← optional (default: pending)
        }

    Success response (201 Created):
        {
            "success": true,
            "message": "Task created.",
            "data": { ...new task... }
        }

    Side effect:
        Emits 'task_created' WebSocket event to all connected clients.
        Other browsers update their task list in real time.

    Error response (400):
        { "success": false, "message": "Task title is required." }
    """
    # Parse JSON body — silent=True prevents crash on malformed JSON
    data = request.get_json(silent=True) or {}

    # ── Validate input ─────────────────────────────────────────────────────────
    try:
        validate_task(data, is_update=False)
    except ValueError as exc:
        return error_response(str(exc), 400)

    # ── Create task ────────────────────────────────────────────────────────────
    try:
        task = TaskService.create(user_id=_uid(), data=data)

        # Broadcast to all connected browsers via WebSocket
        # This is what makes the dashboard update in real time
        emit_task_event("task_created", task.to_dict())

        return success_response(
            data=task.to_dict(),
            message="Task created.",
            status_code=201,
        )
    except Exception:
        logger.exception("Error creating task for user_id=%s", _uid())
        return error_response("Could not create task.", 500)


# ══════════════════════════════════════════════════════════════════════════════
# UPDATE TASK
# ══════════════════════════════════════════════════════════════════════════════

@tasks_bp.route("/<int:task_id>", methods=["PUT"])
@login_required
def update_task(task_id: int):
    """
    PUT /api/tasks/<task_id>
    Update an existing task.

    Supports partial updates — only send the fields you want to change.

    Request body examples:

        Update just the status:
            { "status": "completed" }

        Update title and priority:
            { "title": "New title", "priority": "low" }

        Update everything:
            {
                "title":       "Updated title",
                "description": "New description",
                "priority":    "low",
                "status":      "completed"
            }

    Success response (200):
        {
            "success": true,
            "message": "Task updated.",
            "data": { ...updated task... }
        }

    Side effect:
        Emits 'task_updated' WebSocket event — all browsers
        update the changed task card in real time.
    """
    data = request.get_json(silent=True) or {}

    # is_update=True → title is NOT required for partial updates
    try:
        validate_task(data, is_update=True)
    except ValueError as exc:
        return error_response(str(exc), 400)

    try:
        task = TaskService.update(
            task_id=task_id,
            user_id=_uid(),
            data=data,
        )
        emit_task_event("task_updated", task.to_dict())

        return success_response(
            data=task.to_dict(),
            message="Task updated.",
        )
    except ValueError as exc:
        # Task not found or doesn't belong to user
        return error_response(str(exc), 404)
    except Exception:
        logger.exception("Error updating task_id=%s", task_id)
        return error_response("Could not update task.", 500)


# ══════════════════════════════════════════════════════════════════════════════
# DELETE TASK
# ══════════════════════════════════════════════════════════════════════════════

@tasks_bp.route("/<int:task_id>", methods=["DELETE"])
@login_required
def delete_task(task_id: int):
    """
    DELETE /api/tasks/<task_id>
    Permanently delete a task.

    No request body needed.

    Success response (200):
        {
            "success": true,
            "message": "Task deleted."
        }
        Note: no 'data' field — the task no longer exists.

    Side effect:
        Emits 'task_deleted' with {"id": task_id} so browsers
        can remove the correct card from their list.

    Error response (404):
        { "success": false, "message": "Task not found." }
    """
    try:
        TaskService.delete(task_id=task_id, user_id=_uid())

        # Send only the ID — the task object no longer exists
        emit_task_event("task_deleted", {"id": task_id})

        return success_response(message="Task deleted.")
    except ValueError as exc:
        return error_response(str(exc), 404)
    except Exception:
        logger.exception("Error deleting task_id=%s", task_id)
        return error_response("Could not delete task.", 500)