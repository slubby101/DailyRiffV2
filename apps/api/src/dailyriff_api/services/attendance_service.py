"""Attendance service: status transitions and makeup scheduling."""

from __future__ import annotations

# Valid attendance status transitions
_VALID_TRANSITIONS: dict[str, set[str]] = {
    "scheduled": {"present", "absent", "late", "excused", "cancelled"},
    "present": {"late"},  # correction
    "absent": {"excused"},  # teacher can excuse after the fact
    "late": {"present"},  # correction
    "excused": set(),  # terminal
    "cancelled": set(),  # terminal
}

# Valid absence status transitions
_ABSENCE_TRANSITIONS: dict[str, set[str]] = {
    "reported": {"acknowledged", "makeup_requested"},
    "acknowledged": {"makeup_requested", "resolved"},
    "makeup_requested": {"makeup_scheduled", "resolved"},
    "makeup_scheduled": {"resolved"},
    "resolved": set(),  # terminal
}


def validate_attendance_transition(current: str, target: str) -> bool:
    """Check if an attendance status transition is valid."""
    allowed = _VALID_TRANSITIONS.get(current, set())
    return target in allowed


def validate_absence_transition(current: str, target: str) -> bool:
    """Check if an absence status transition is valid."""
    allowed = _ABSENCE_TRANSITIONS.get(current, set())
    return target in allowed


def get_valid_attendance_transitions(current: str) -> set[str]:
    """Return the set of valid target statuses from a given attendance status."""
    return _VALID_TRANSITIONS.get(current, set())


def get_valid_absence_transitions(current: str) -> set[str]:
    """Return the set of valid target statuses from a given absence status."""
    return _ABSENCE_TRANSITIONS.get(current, set())
