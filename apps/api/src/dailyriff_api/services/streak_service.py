"""Streak calculation service.

Ports Polymet PracticeStreakCalculator logic:
- One practice recording per calendar day counts toward the streak
- Active if today or yesterday has a practice
- Tracks current streak and longest streak
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class StreakResult:
    current_streak: int
    longest_streak: int
    is_active: bool
    total_practice_days: int = 0
    weekly_minutes: int = 0


def compute_streaks(
    practice_dates: list[date],
    *,
    today: date | None = None,
) -> StreakResult:
    """Compute current and longest streak from a list of practice dates.

    Each unique date counts as one streak day (multi-recording-same-day = 1).
    A streak is active if today or yesterday has a practice.
    """
    if not practice_dates:
        return StreakResult(current_streak=0, longest_streak=0, is_active=False)

    if today is None:
        today = date.today()

    unique_dates = sorted(set(practice_dates))
    total_practice_days = len(unique_dates)

    # Compute all streaks (runs of consecutive dates)
    streaks: list[list[date]] = []
    current_run = [unique_dates[0]]
    for i in range(1, len(unique_dates)):
        if (unique_dates[i] - unique_dates[i - 1]).days == 1:
            current_run.append(unique_dates[i])
        else:
            streaks.append(current_run)
            current_run = [unique_dates[i]]
    streaks.append(current_run)

    longest_streak = max(len(s) for s in streaks)

    # Current streak: the most recent run, but only if it touches today or yesterday
    last_run = streaks[-1]
    last_date = last_run[-1]
    if last_date == today or last_date == today - timedelta(days=1):
        current_streak = len(last_run)
        is_active = True
    else:
        current_streak = 0
        is_active = False

    return StreakResult(
        current_streak=current_streak,
        longest_streak=longest_streak,
        is_active=is_active,
        total_practice_days=total_practice_days,
    )


def compute_weekly_minutes(duration_seconds_list: list[int]) -> int:
    """Sum recording durations (in seconds) and return total minutes (rounded down)."""
    return sum(duration_seconds_list) // 60
