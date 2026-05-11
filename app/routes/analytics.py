"""
app/routes/analytics.py
------------------------
Analytics API Blueprint for FlowDesk.

URL prefix: /api/analytics

Routes:
    GET /api/analytics  → compute and return full analytics payload

Flow:
    1. Get all tasks for logged-in user from DB (via TaskService)
    2. Convert Task objects → plain dicts
    3. Feed dicts into AnalyticsProcessor
    4. Return computed stats as JSON

Why not pass Task objects directly to AnalyticsProcessor?
    Keeps analytics/ independent of SQLAlchemy.
    The route is the bridge between the DB world and the
    analytics world — it speaks both languages.
"""

import logging
from flask import Blueprint, session
from app.services.task_service import TaskService
from app.utils.helpers import success_response, error_response, login_required
from analytics.processor import AnalyticsProcessor

logger = logging.getLogger(__name__)

analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/analytics")


@analytics_bp.route("", methods=["GET"])
@login_required
def get_analytics():
    """
    GET /api/analytics
    Return full analytics payload for the logged-in user's tasks.

    No request body needed.

    Success response (200):
        {
            "success": true,
            "message": "Success",
            "data": {
                "summary": {
                    "total": 10,
                    "completed": 6,
                    "pending": 2,
                    "in_progress": 2,
                    "completion_percentage": 60.0,
                    "productivity_score": 70.0
                },
                "priority_distribution": {
                    "high": 3,
                    "medium": 5,
                    "low": 2
                },
                "daily_trend": [
                    { "date": "2024-01-10", "count": 2 },
                    { "date": "2024-01-11", "count": 4 }
                ],
                "status_breakdown": {
                    "pending":     { "count": 2, "percentage": 20.0 },
                    "in_progress": { "count": 2, "percentage": 20.0 },
                    "completed":   { "count": 6, "percentage": 60.0 }
                }
            }
        }
    """
    try:
        user_id = session["user_id"]

        # ── Step 1: Fetch tasks from DB ────────────────────────────────────────
        tasks = TaskService.get_all(user_id)

        # ── Step 2: Convert to plain dicts ─────────────────────────────────────
        # AnalyticsProcessor expects dicts, not SQLAlchemy objects.
        # to_dict() gives us JSON-safe Python dictionaries.
        task_dicts = [task.to_dict() for task in tasks]

        # ── Step 3: Run analytics ──────────────────────────────────────────────
        processor = AnalyticsProcessor(task_dicts)
        result    = processor.compute_all()

        logger.info(
            "Analytics computed for user_id=%s | %d tasks",
            user_id, len(task_dicts)
        )

        return success_response(data=result)

    except Exception:
        logger.exception(
            "Analytics computation failed for user_id=%s",
            session.get("user_id", "unknown")
        )
        return error_response("Could not compute analytics.", 500)