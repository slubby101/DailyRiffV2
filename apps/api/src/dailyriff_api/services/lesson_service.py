"""Lesson service: recurrence generation with DST-safe TZ handling.

Recurrence rules are stored against studio-local timezone (not UTC offset).
This means a lesson at "3:00 PM America/New_York" stays at 3:00 PM local time
even when clocks change for DST.
"""

from __future__ import annotations

from datetime import date, time, timedelta
from zoneinfo import ZoneInfo


def generate_occurrences(
    *,
    start_date: date,
    end_date: date | None,
    cadence: str,
    day_of_week: int | None,
    start_time: time,
    studio_timezone: str,
    max_occurrences: int = 52,
) -> list[date]:
    """Generate occurrence dates for a lesson template.

    All dates are in studio-local timezone. Recurring lessons are anchored
    to the studio's IANA timezone so they survive DST transitions — the
    wall-clock time stays the same even when UTC offset changes.

    Args:
        start_date: First possible occurrence date.
        end_date: Last possible occurrence date (inclusive). Defaults to
            start_date + 1 year if not provided for recurring lessons.
        cadence: 'one_time', 'weekly', 'biweekly', or 'monthly'.
        day_of_week: 0=Monday through 6=Sunday. Required for recurring.
        start_time: Lesson start time (in studio-local TZ).
        studio_timezone: IANA timezone string (e.g. 'America/New_York').
        max_occurrences: Safety cap to prevent runaway generation.

    Returns:
        List of occurrence dates in chronological order.
    """
    # Validate timezone
    try:
        ZoneInfo(studio_timezone)
    except (KeyError, ValueError) as exc:
        raise ValueError(f"Invalid timezone: {studio_timezone}") from exc

    if cadence == "one_time":
        return [start_date]

    if day_of_week is None:
        raise ValueError("day_of_week is required for recurring lessons")

    if end_date is None:
        end_date = start_date + timedelta(days=365)

    occurrences: list[date] = []
    current = start_date

    # Advance to the first matching day_of_week
    while current.weekday() != day_of_week and current <= end_date:
        current += timedelta(days=1)

    while current <= end_date and len(occurrences) < max_occurrences:
        occurrences.append(current)

        if cadence == "weekly":
            current += timedelta(weeks=1)
        elif cadence == "biweekly":
            current += timedelta(weeks=2)
        elif cadence == "monthly":
            # Move forward roughly 4 weeks, then find the next matching day
            current += timedelta(weeks=4)
            while current.weekday() != day_of_week:
                current += timedelta(days=1)

    return occurrences


def build_ics_event(
    *,
    lesson_title: str,
    occurrence_date: date,
    start_time: time,
    duration_minutes: int,
    studio_timezone: str,
    student_name: str | None = None,
    uid: str,
) -> str:
    """Build a single VEVENT in iCalendar format.

    Uses DTSTART with TZID= for DST-safe external calendar interop.
    """
    tz = ZoneInfo(studio_timezone)
    # Format: YYYYMMDDTHHMMSS
    dt_str = f"{occurrence_date:%Y%m%d}T{start_time:%H%M%S}"

    from datetime import datetime as dt_cls

    start_dt = dt_cls.combine(occurrence_date, start_time, tzinfo=tz)
    end_dt = start_dt + timedelta(minutes=duration_minutes)
    end_str = f"{end_dt:%Y%m%d}T{end_dt:%H%M%S}"

    summary = lesson_title
    if student_name:
        summary = f"{lesson_title} — {student_name}"

    lines = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTART;TZID={studio_timezone}:{dt_str}",
        f"DTEND;TZID={studio_timezone}:{end_str}",
        f"SUMMARY:{summary}",
        "END:VEVENT",
    ]
    return "\r\n".join(lines)


def build_ics_calendar(events: list[str], tz: str) -> str:
    """Wrap VEVENT blocks in a full iCalendar document."""
    header = "\r\n".join([
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//DailyRiff//Lessons//EN",
        "CALSCALE:GREGORIAN",
        f"X-WR-TIMEZONE:{tz}",
    ])
    footer = "END:VCALENDAR"
    body = "\r\n".join(events)
    return f"{header}\r\n{body}\r\n{footer}\r\n"
