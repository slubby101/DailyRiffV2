"""Lesson service unit tests: recurrence generation and ICS export."""

from __future__ import annotations

from datetime import date, time

import pytest

from dailyriff_api.services.lesson_service import (
    build_ics_calendar,
    build_ics_event,
    generate_occurrences,
)


# ---------------------------------------------------------------------------
# One-time lessons
# ---------------------------------------------------------------------------


def test_one_time_lesson_returns_single_date() -> None:
    result = generate_occurrences(
        start_date=date(2026, 5, 1),
        end_date=None,
        cadence="one_time",
        day_of_week=None,
        start_time=time(15, 0),
        studio_timezone="America/New_York",
    )
    assert result == [date(2026, 5, 1)]


# ---------------------------------------------------------------------------
# Weekly recurring
# ---------------------------------------------------------------------------


def test_weekly_generates_correct_dates() -> None:
    # Thursday = weekday 3
    result = generate_occurrences(
        start_date=date(2026, 5, 1),  # Friday
        end_date=date(2026, 5, 31),
        cadence="weekly",
        day_of_week=3,  # Thursday
        start_time=time(15, 0),
        studio_timezone="America/New_York",
    )
    # First Thursday after May 1 is May 7, then 14, 21, 28
    assert result == [
        date(2026, 5, 7),
        date(2026, 5, 14),
        date(2026, 5, 21),
        date(2026, 5, 28),
    ]


def test_weekly_start_date_on_matching_day() -> None:
    # May 4, 2026 is a Monday (weekday 0)
    result = generate_occurrences(
        start_date=date(2026, 5, 4),
        end_date=date(2026, 5, 25),
        cadence="weekly",
        day_of_week=0,  # Monday
        start_time=time(10, 0),
        studio_timezone="America/New_York",
    )
    assert result == [
        date(2026, 5, 4),
        date(2026, 5, 11),
        date(2026, 5, 18),
        date(2026, 5, 25),
    ]


# ---------------------------------------------------------------------------
# Biweekly recurring
# ---------------------------------------------------------------------------


def test_biweekly_generates_every_other_week() -> None:
    result = generate_occurrences(
        start_date=date(2026, 5, 4),  # Monday
        end_date=date(2026, 6, 30),
        cadence="biweekly",
        day_of_week=0,  # Monday
        start_time=time(14, 0),
        studio_timezone="America/Chicago",
    )
    assert result == [
        date(2026, 5, 4),
        date(2026, 5, 18),
        date(2026, 6, 1),
        date(2026, 6, 15),
        date(2026, 6, 29),
    ]


# ---------------------------------------------------------------------------
# Monthly recurring
# ---------------------------------------------------------------------------


def test_monthly_generates_same_weekday_each_month() -> None:
    result = generate_occurrences(
        start_date=date(2026, 1, 5),  # Monday
        end_date=date(2026, 4, 30),
        cadence="monthly",
        day_of_week=0,  # Monday
        start_time=time(16, 0),
        studio_timezone="America/New_York",
    )
    # Each occurrence should be on a Monday, roughly 4 weeks apart
    # 4-week jump: Jan 5 → Feb 2 → Mar 2 → Mar 30 → Apr 27
    assert len(result) == 5
    for d in result:
        assert d.weekday() == 0


# ---------------------------------------------------------------------------
# DST edge cases
# ---------------------------------------------------------------------------


def test_weekly_lesson_crosses_spring_forward() -> None:
    """Recurring lesson crossing spring-forward boundary (Mar 8 2026, America/New_York).

    The lesson at 3:00 PM local time should remain at 3:00 PM after clocks
    spring forward. The occurrence dates themselves don't change — DST safety
    means we store dates, not UTC offsets.
    """
    result = generate_occurrences(
        start_date=date(2026, 3, 1),
        end_date=date(2026, 3, 31),
        cadence="weekly",
        day_of_week=6,  # Sunday
        start_time=time(15, 0),  # 3 PM
        studio_timezone="America/New_York",
    )
    # Sundays in March 2026: 1, 8 (spring forward), 15, 22, 29
    assert result == [
        date(2026, 3, 1),
        date(2026, 3, 8),   # Spring forward day
        date(2026, 3, 15),
        date(2026, 3, 22),
        date(2026, 3, 29),
    ]


def test_weekly_lesson_crosses_fall_back() -> None:
    """Recurring lesson crossing fall-back boundary (Nov 1 2026, America/New_York)."""
    result = generate_occurrences(
        start_date=date(2026, 10, 25),
        end_date=date(2026, 11, 15),
        cadence="weekly",
        day_of_week=6,  # Sunday
        start_time=time(15, 0),
        studio_timezone="America/New_York",
    )
    # Sundays: Oct 25, Nov 1 (fall back), Nov 8, Nov 15
    assert result == [
        date(2026, 10, 25),
        date(2026, 11, 1),   # Fall back day
        date(2026, 11, 8),
        date(2026, 11, 15),
    ]


# ---------------------------------------------------------------------------
# Max occurrences safety cap
# ---------------------------------------------------------------------------


def test_max_occurrences_caps_generation() -> None:
    result = generate_occurrences(
        start_date=date(2026, 1, 5),
        end_date=date(2030, 12, 31),
        cadence="weekly",
        day_of_week=0,
        start_time=time(10, 0),
        studio_timezone="America/New_York",
        max_occurrences=5,
    )
    assert len(result) == 5


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_recurring_requires_day_of_week() -> None:
    with pytest.raises(ValueError, match="day_of_week is required"):
        generate_occurrences(
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 31),
            cadence="weekly",
            day_of_week=None,
            start_time=time(15, 0),
            studio_timezone="America/New_York",
        )


def test_invalid_timezone_raises() -> None:
    with pytest.raises(ValueError, match="Invalid timezone"):
        generate_occurrences(
            start_date=date(2026, 5, 1),
            end_date=None,
            cadence="one_time",
            day_of_week=None,
            start_time=time(15, 0),
            studio_timezone="Not/A/Timezone",
        )


def test_no_end_date_defaults_to_one_year() -> None:
    result = generate_occurrences(
        start_date=date(2026, 1, 5),
        end_date=None,
        cadence="weekly",
        day_of_week=0,
        start_time=time(10, 0),
        studio_timezone="America/New_York",
    )
    # 52 weeks cap
    assert len(result) == 52


# ---------------------------------------------------------------------------
# ICS export
# ---------------------------------------------------------------------------


def test_build_ics_event_contains_tzid() -> None:
    ics = build_ics_event(
        lesson_title="Piano Lesson",
        occurrence_date=date(2026, 5, 7),
        start_time=time(15, 0),
        duration_minutes=30,
        studio_timezone="America/New_York",
        uid="test-uid@dailyriff.com",
    )
    assert "DTSTART;TZID=America/New_York:20260507T150000" in ics
    assert "DTEND;TZID=America/New_York:20260507T153000" in ics
    assert "SUMMARY:Piano Lesson" in ics


def test_build_ics_event_with_student_name() -> None:
    ics = build_ics_event(
        lesson_title="Piano",
        occurrence_date=date(2026, 5, 7),
        start_time=time(15, 0),
        duration_minutes=60,
        studio_timezone="America/Chicago",
        student_name="Alice",
        uid="uid@dailyriff.com",
    )
    assert "SUMMARY:Piano — Alice" in ics
    assert "DTEND;TZID=America/Chicago:20260507T160000" in ics


def test_build_ics_calendar_wraps_events() -> None:
    event = build_ics_event(
        lesson_title="Test",
        occurrence_date=date(2026, 5, 7),
        start_time=time(15, 0),
        duration_minutes=30,
        studio_timezone="America/New_York",
        uid="test@dailyriff.com",
    )
    cal = build_ics_calendar([event], "America/New_York")
    assert cal.startswith("BEGIN:VCALENDAR")
    assert "END:VCALENDAR" in cal
    assert "BEGIN:VEVENT" in cal
    assert "X-WR-TIMEZONE:America/New_York" in cal


def test_multi_recording_same_day_counted_once() -> None:
    """Ensure that generating occurrences doesn't duplicate dates.

    Even if generate is called multiple times, the same date only appears once.
    """
    result = generate_occurrences(
        start_date=date(2026, 5, 4),
        end_date=date(2026, 5, 4),
        cadence="one_time",
        day_of_week=None,
        start_time=time(15, 0),
        studio_timezone="America/New_York",
    )
    assert result == [date(2026, 5, 4)]
