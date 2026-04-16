"""Attendance service unit tests: status transition validation."""

from __future__ import annotations

from dailyriff_api.services.attendance_service import (
    get_valid_absence_transitions,
    get_valid_attendance_transitions,
    validate_absence_transition,
    validate_attendance_transition,
)


# ---------------------------------------------------------------------------
# Attendance transitions
# ---------------------------------------------------------------------------


def test_scheduled_can_transition_to_present() -> None:
    assert validate_attendance_transition("scheduled", "present") is True


def test_scheduled_can_transition_to_absent() -> None:
    assert validate_attendance_transition("scheduled", "absent") is True


def test_scheduled_can_transition_to_late() -> None:
    assert validate_attendance_transition("scheduled", "late") is True


def test_scheduled_can_transition_to_excused() -> None:
    assert validate_attendance_transition("scheduled", "excused") is True


def test_scheduled_can_transition_to_cancelled() -> None:
    assert validate_attendance_transition("scheduled", "cancelled") is True


def test_present_can_be_corrected_to_late() -> None:
    assert validate_attendance_transition("present", "late") is True


def test_present_cannot_transition_to_absent() -> None:
    assert validate_attendance_transition("present", "absent") is False


def test_absent_can_be_excused() -> None:
    assert validate_attendance_transition("absent", "excused") is True


def test_absent_cannot_transition_to_present() -> None:
    assert validate_attendance_transition("absent", "present") is False


def test_excused_is_terminal() -> None:
    assert get_valid_attendance_transitions("excused") == set()


def test_cancelled_is_terminal() -> None:
    assert get_valid_attendance_transitions("cancelled") == set()


def test_late_can_be_corrected_to_present() -> None:
    assert validate_attendance_transition("late", "present") is True


# ---------------------------------------------------------------------------
# Absence transitions
# ---------------------------------------------------------------------------


def test_reported_can_transition_to_acknowledged() -> None:
    assert validate_absence_transition("reported", "acknowledged") is True


def test_reported_can_transition_to_makeup_requested() -> None:
    assert validate_absence_transition("reported", "makeup_requested") is True


def test_acknowledged_can_transition_to_makeup_requested() -> None:
    assert validate_absence_transition("acknowledged", "makeup_requested") is True


def test_acknowledged_can_transition_to_resolved() -> None:
    assert validate_absence_transition("acknowledged", "resolved") is True


def test_makeup_requested_can_transition_to_makeup_scheduled() -> None:
    assert validate_absence_transition("makeup_requested", "makeup_scheduled") is True


def test_makeup_scheduled_can_transition_to_resolved() -> None:
    assert validate_absence_transition("makeup_scheduled", "resolved") is True


def test_resolved_is_terminal() -> None:
    assert get_valid_absence_transitions("resolved") == set()


def test_reported_cannot_skip_to_resolved() -> None:
    assert validate_absence_transition("reported", "resolved") is False


def test_makeup_scheduled_cannot_go_back_to_requested() -> None:
    assert validate_absence_transition("makeup_scheduled", "makeup_requested") is False
