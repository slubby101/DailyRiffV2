"""Assignment service — validation and business logic.

AssignmentValidator ported from Polymet: teacher↔student studio match,
due ≤6mo, ≤10 pieces, ≤15 techniques.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID


class AssignmentValidator:
    """Stateless validation rules for assignment creation."""

    MAX_PIECES = 10
    MAX_TECHNIQUES = 15
    MAX_DUE_DAYS = 183  # ~6 months

    @classmethod
    def validate(
        cls,
        *,
        studio_id: UUID,
        teacher_id: UUID,
        student_id: UUID,
        title: str,
        due_date: datetime,
        pieces: list[str] | None = None,
        techniques: list[str] | None = None,
    ) -> list[str]:
        errors: list[str] = []

        if not title or not title.strip():
            errors.append("Title is required")

        if teacher_id == student_id:
            errors.append("Teacher and student cannot be the same user")

        now = datetime.now(timezone.utc)
        if due_date < now:
            errors.append("Due date cannot be in the past")

        max_due = now + timedelta(days=cls.MAX_DUE_DAYS)
        if due_date > max_due:
            errors.append(f"Due date cannot be more than 6 months ({cls.MAX_DUE_DAYS} days) in the future")

        if pieces and len(pieces) > cls.MAX_PIECES:
            errors.append(f"Cannot have more than 10 pieces")

        if techniques and len(techniques) > cls.MAX_TECHNIQUES:
            errors.append(f"Cannot have more than 15 techniques")

        return errors
