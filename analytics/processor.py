"""
analytics/processor.py
-----------------------
Analytics engine for FlowDesk.

Design principles:
    - Zero Flask imports — pure Python/Pandas/NumPy
    - Takes a plain list of dicts as input (not SQLAlchemy objects)
    - Returns plain dicts as output (easy to JSON-serialise)
    - Handles the empty-data case gracefully (new users have no tasks)

Why accept dicts instead of Task objects?
    Decoupling. This module doesn't know SQLAlchemy exists.
    The route converts Task objects → dicts, then passes them here.
    If we ever switch from SQLAlchemy to another ORM, this file
    doesn't change at all.

Usage:
    tasks = TaskService.get_all(user_id)
    task_dicts = [t.to_dict() for t in tasks]
    processor = AnalyticsProcessor(task_dicts)
    result = processor.compute_all()
"""

import logging
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class AnalyticsProcessor:
    """
    Computes task analytics using Pandas DataFrames and NumPy operations.

    Initialise with a list of task dictionaries:
        processor = AnalyticsProcessor(task_dicts)

    Then call individual methods or compute_all() for everything:
        result = processor.compute_all()
    """

    # Expected columns — used when creating an empty DataFrame
    # so downstream code always gets consistent column names
    COLUMNS = ["id", "title", "priority", "status", "created_at", "updated_at"]

    def __init__(self, tasks: list[dict]):
        """
        Build a Pandas DataFrame from the task list.

        Args:
            tasks: List of dicts, each representing one task.
                   (from Task.to_dict())

        If tasks is empty we still create a DataFrame — just with
        the correct column names and zero rows. This prevents
        KeyError crashes when the user has no tasks yet.
        """
        if tasks:
            self.df = pd.DataFrame(tasks)

            # Parse created_at as proper datetime objects.
            # utc=True tells Pandas to treat them as UTC-aware timestamps.
            # This is important for correct date grouping later.
            self.df["created_at"] = pd.to_datetime(
                self.df["created_at"], utc=True
            )
        else:
            # Empty DataFrame with the right structure
            self.df = pd.DataFrame(columns=self.COLUMNS)

        logger.debug(
            "AnalyticsProcessor initialised with %d tasks", len(self.df)
        )

    # ── Summary Statistics ─────────────────────────────────────────────────────

    def get_summary(self) -> dict:
        """
        Compute top-level task summary statistics.

        Uses NumPy for:
            - np.round()  → controlled decimal places
            - np.dot()    → weighted productivity score (dot product)
            - np.array()  → vectorised weight application

        Returns:
            {
                "total": int,
                "completed": int,
                "pending": int,
                "in_progress": int,
                "completion_percentage": float,  ← 0.0 to 100.0
                "productivity_score": float       ← 0.0 to 100.0
            }
        """
        df    = self.df
        total = len(df)

        # Handle the empty case — avoid division by zero
        if total == 0:
            return {
                "total":                 0,
                "completed":             0,
                "pending":               0,
                "in_progress":           0,
                "completion_percentage": 0.0,
                "productivity_score":    0.0,
            }

        # ── Status counts ──────────────────────────────────────────────────────
        # Pandas boolean mask: (df["status"] == "completed") creates a
        # Series of True/False values. .sum() counts the True ones.
        completed   = int((df["status"] == "completed").sum())
        pending     = int((df["status"] == "pending").sum())
        in_progress = int((df["status"] == "in_progress").sum())

        # ── Completion percentage ──────────────────────────────────────────────
        # np.round() gives us controlled decimal places.
        # Plain Python round() also works but np.round() is the
        # NumPy-idiomatic way — shows you know the library.
        completion_pct = float(
            np.round((completed / total) * 100, 2)
        )

        # ── Productivity score (NumPy dot product) ─────────────────────────────
        # Concept: not all task states are equal.
        #   Completed   = full credit  (weight 1.0)
        #   In Progress = half credit  (weight 0.5)
        #   Pending     = no credit    (weight 0.0)
        #
        # np.dot([completed, in_progress, pending], [1.0, 0.5, 0.0])
        # = (completed * 1.0) + (in_progress * 0.5) + (pending * 0.0)
        # = effective_work_units
        #
        # Divide by total to normalise to 0-1, multiply by 100 for %.
        counts       = np.array([completed, in_progress, pending], dtype=float)
        score_weights = np.array([1.0,       0.5,         0.0])

        productivity_score = float(
            np.round(np.dot(counts, score_weights) / total * 100, 2)
        )

        return {
            "total":                 total,
            "completed":             completed,
            "pending":               pending,
            "in_progress":           in_progress,
            "completion_percentage": completion_pct,
            "productivity_score":    productivity_score,
        }

    # ── Priority Distribution ──────────────────────────────────────────────────

    def get_priority_distribution(self) -> dict:
        """
        Count tasks in each priority level.

        Uses Pandas value_counts() — counts occurrences of each
        unique value in the 'priority' column.

        Example:
            priority
            medium    5
            high      3
            low       2
            dtype: int64

        We convert to a dict and fill missing keys with 0
        so the response always has all three keys even if
        the user has no low-priority tasks.

        Returns:
            { "high": int, "medium": int, "low": int }
        """
        if self.df.empty:
            return {"high": 0, "medium": 0, "low": 0}

        # value_counts() returns a Series: priority → count
        # .to_dict() converts it to { "medium": 5, "high": 3, "low": 2 }
        counts = self.df["priority"].value_counts().to_dict()

        # .get(key, 0) returns 0 if that priority has no tasks
        # int() converts numpy int64 → Python int for JSON serialisation
        return {
            "high":   int(counts.get("high",   0)),
            "medium": int(counts.get("medium", 0)),
            "low":    int(counts.get("low",    0)),
        }

    # ── Daily Task Trend ───────────────────────────────────────────────────────

    def get_daily_trend(self) -> list[dict]:
        """
        Count how many tasks were created per day over the last 7 days.

        Uses Pandas date operations:
            .dt.date    → extracts just the date from a datetime
            .groupby()  → groups rows by date
            .size()     → counts rows in each group
            .reset_index() → turns the grouped result back into a DataFrame
            .tail(7)    → keeps only the last 7 entries

        Returns:
            [
                { "date": "2024-01-10", "count": 3 },
                { "date": "2024-01-11", "count": 1 },
                ...
            ]

        Empty list if no tasks exist.
        """
        if self.df.empty:
            return []

        # Work on a copy so we don't mutate the original DataFrame
        df = self.df.copy()

        # Extract the date portion from the UTC-aware datetime column.
        # "2024-01-15 10:30:00+00:00" → datetime.date(2024, 1, 15)
        df["date"] = df["created_at"].dt.date

        # Group by date, count tasks per group, keep last 7 days
        trend = (
            df.groupby("date")   # Group rows by their date value
            .size()              # Count rows in each group
            .reset_index(name="count")  # Name the count column "count"
            .tail(7)             # Keep the 7 most recent dates
        )

        # Convert each row to a dict.
        # str(row["date"]) converts date object → "2024-01-15" string
        # int(row["count"]) converts numpy int64 → Python int
        return [
            {
                "date":  str(row["date"]),
                "count": int(row["count"]),
            }
            for _, row in trend.iterrows()
        ]

    # ── Status Breakdown (bonus) ───────────────────────────────────────────────

    def get_status_breakdown(self) -> dict:
        """
        Return percentage breakdown by status.

        Uses NumPy for the percentage calculation.
        Bonus feature — gives the frontend data for a pie chart.

        Returns:
            {
                "pending":     { "count": 2, "percentage": 20.0 },
                "in_progress": { "count": 3, "percentage": 30.0 },
                "completed":   { "count": 5, "percentage": 50.0 }
            }
        """
        if self.df.empty:
            return {
                "pending":     {"count": 0, "percentage": 0.0},
                "in_progress": {"count": 0, "percentage": 0.0},
                "completed":   {"count": 0, "percentage": 0.0},
            }

        total  = len(self.df)
        counts = self.df["status"].value_counts().to_dict()

        result = {}
        for status in ["pending", "in_progress", "completed"]:
            count = int(counts.get(status, 0))
            # np.round for consistent decimal handling
            pct   = float(np.round((count / total) * 100, 1))
            result[status] = {"count": count, "percentage": pct}

        return result

    # ── Master Method ──────────────────────────────────────────────────────────

    def compute_all(self) -> dict:
        """
        Run all analytics and return a single combined payload.

        This is what the API route calls — one method that
        returns everything the dashboard needs in one go.

        Returns:
            {
                "summary":              { ... },
                "priority_distribution": { ... },
                "daily_trend":           [ ... ],
                "status_breakdown":      { ... }
            }
        """
        logger.debug("Running full analytics computation")

        return {
            "summary":               self.get_summary(),
            "priority_distribution": self.get_priority_distribution(),
            "daily_trend":           self.get_daily_trend(),
            "status_breakdown":      self.get_status_breakdown(),
        }