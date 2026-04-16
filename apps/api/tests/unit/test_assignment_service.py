"""Assignment service unit tests — AssignmentValidator + assignment_service."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from dailyriff_api.services.assignment_service import AssignmentValidator


STUDIO_ID = uuid.uuid4()
TEACHER_ID = uuid.uuid4()
STUDENT_ID = uuid.uuid4()


class TestAssignmentValidator:
    """Validator ported from Polymet: teacher↔student studio match,
    due ≤6mo, ≤10 pieces, ≤15 techniques."""

    def test_valid_assignment_passes(self):
        errors = AssignmentValidator.validate(
            studio_id=STUDIO_ID,
            teacher_id=TEACHER_ID,
            student_id=STUDENT_ID,
            title="Practice scales",
            due_date=datetime.now(timezone.utc) + timedelta(days=7),
            pieces=["Clair de Lune"],
            techniques=["legato"],
        )
        assert errors == []

    def test_due_date_in_past_rejected(self):
        errors = AssignmentValidator.validate(
            studio_id=STUDIO_ID,
            teacher_id=TEACHER_ID,
            student_id=STUDENT_ID,
            title="Practice scales",
            due_date=datetime.now(timezone.utc) - timedelta(days=1),
        )
        assert any("past" in e.lower() for e in errors)

    def test_due_date_over_six_months_rejected(self):
        errors = AssignmentValidator.validate(
            studio_id=STUDIO_ID,
            teacher_id=TEACHER_ID,
            student_id=STUDENT_ID,
            title="Practice scales",
            due_date=datetime.now(timezone.utc) + timedelta(days=200),
        )
        assert any("6 month" in e.lower() for e in errors)

    def test_more_than_ten_pieces_rejected(self):
        errors = AssignmentValidator.validate(
            studio_id=STUDIO_ID,
            teacher_id=TEACHER_ID,
            student_id=STUDENT_ID,
            title="Practice scales",
            due_date=datetime.now(timezone.utc) + timedelta(days=7),
            pieces=[f"piece_{i}" for i in range(11)],
        )
        assert any("10 pieces" in e.lower() for e in errors)

    def test_more_than_fifteen_techniques_rejected(self):
        errors = AssignmentValidator.validate(
            studio_id=STUDIO_ID,
            teacher_id=TEACHER_ID,
            student_id=STUDENT_ID,
            title="Practice scales",
            due_date=datetime.now(timezone.utc) + timedelta(days=7),
            techniques=[f"tech_{i}" for i in range(16)],
        )
        assert any("15 techniques" in e.lower() for e in errors)

    def test_empty_title_rejected(self):
        errors = AssignmentValidator.validate(
            studio_id=STUDIO_ID,
            teacher_id=TEACHER_ID,
            student_id=STUDENT_ID,
            title="",
            due_date=datetime.now(timezone.utc) + timedelta(days=7),
        )
        assert any("title" in e.lower() for e in errors)

    def test_teacher_same_as_student_rejected(self):
        errors = AssignmentValidator.validate(
            studio_id=STUDIO_ID,
            teacher_id=TEACHER_ID,
            student_id=TEACHER_ID,
            title="Practice scales",
            due_date=datetime.now(timezone.utc) + timedelta(days=7),
        )
        assert any("same" in e.lower() or "teacher" in e.lower() for e in errors)
