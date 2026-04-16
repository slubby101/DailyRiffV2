"""Tests for the streak calculation service.

Streak rules (ported from Polymet PracticeStreakCalculator):
- One practice recording per calendar day counts toward the streak
- Active if today or yesterday has a practice
- Tracks current streak + longest streak
- Multi-recording-same-day = one streak day
- DST boundaries handled correctly
"""

from __future__ import annotations

from datetime import date

from dailyriff_api.services.streak_service import compute_streaks, compute_weekly_minutes


class TestComputeStreaks:
    """Test streak computation from a list of practice dates."""

    def test_no_practice_dates_returns_zero_streaks(self):
        result = compute_streaks([], today=date(2026, 4, 16))
        assert result.current_streak == 0
        assert result.longest_streak == 0
        assert result.is_active is False

    def test_single_practice_today_gives_streak_of_one(self):
        result = compute_streaks([date(2026, 4, 16)], today=date(2026, 4, 16))
        assert result.current_streak == 1
        assert result.longest_streak == 1
        assert result.is_active is True
        assert result.total_practice_days == 1

    def test_single_practice_yesterday_gives_streak_of_one(self):
        result = compute_streaks([date(2026, 4, 15)], today=date(2026, 4, 16))
        assert result.current_streak == 1
        assert result.longest_streak == 1
        assert result.is_active is True

    def test_practice_two_days_ago_gives_zero_current_streak(self):
        result = compute_streaks([date(2026, 4, 14)], today=date(2026, 4, 16))
        assert result.current_streak == 0
        assert result.is_active is False
        assert result.longest_streak == 1

    def test_consecutive_days_build_streak(self):
        dates = [date(2026, 4, 14), date(2026, 4, 15), date(2026, 4, 16)]
        result = compute_streaks(dates, today=date(2026, 4, 16))
        assert result.current_streak == 3
        assert result.longest_streak == 3
        assert result.is_active is True

    def test_gap_breaks_current_streak(self):
        # 3-day streak then gap then 2-day streak ending today
        dates = [
            date(2026, 4, 10), date(2026, 4, 11), date(2026, 4, 12),
            date(2026, 4, 15), date(2026, 4, 16),
        ]
        result = compute_streaks(dates, today=date(2026, 4, 16))
        assert result.current_streak == 2
        assert result.longest_streak == 3

    def test_multi_recording_same_day_counts_as_one(self):
        dates = [date(2026, 4, 16), date(2026, 4, 16), date(2026, 4, 16)]
        result = compute_streaks(dates, today=date(2026, 4, 16))
        assert result.current_streak == 1
        assert result.longest_streak == 1
        assert result.total_practice_days == 1

    def test_longest_streak_tracked_separately_from_current(self):
        # Old 5-day streak, then current 2-day streak
        dates = [
            date(2026, 4, 1), date(2026, 4, 2), date(2026, 4, 3),
            date(2026, 4, 4), date(2026, 4, 5),
            date(2026, 4, 15), date(2026, 4, 16),
        ]
        result = compute_streaks(dates, today=date(2026, 4, 16))
        assert result.current_streak == 2
        assert result.longest_streak == 5

    def test_streak_active_when_yesterday_but_not_today(self):
        dates = [date(2026, 4, 13), date(2026, 4, 14), date(2026, 4, 15)]
        result = compute_streaks(dates, today=date(2026, 4, 16))
        assert result.current_streak == 3
        assert result.is_active is True

    def test_dst_spring_forward_does_not_break_streak(self):
        """DST spring-forward (March 8, 2026 in US) should not break date-based streak."""
        dates = [date(2026, 3, 7), date(2026, 3, 8), date(2026, 3, 9)]
        result = compute_streaks(dates, today=date(2026, 3, 9))
        assert result.current_streak == 3
        assert result.longest_streak == 3

    def test_dst_fall_back_does_not_break_streak(self):
        """DST fall-back (Nov 1, 2026 in US) should not break date-based streak."""
        dates = [date(2026, 10, 31), date(2026, 11, 1), date(2026, 11, 2)]
        result = compute_streaks(dates, today=date(2026, 11, 2))
        assert result.current_streak == 3
        assert result.longest_streak == 3

    def test_day_boundary_new_year(self):
        dates = [date(2025, 12, 31), date(2026, 1, 1)]
        result = compute_streaks(dates, today=date(2026, 1, 1))
        assert result.current_streak == 2
        assert result.longest_streak == 2

    def test_unsorted_input_handled(self):
        dates = [date(2026, 4, 16), date(2026, 4, 14), date(2026, 4, 15)]
        result = compute_streaks(dates, today=date(2026, 4, 16))
        assert result.current_streak == 3
        assert result.longest_streak == 3


class TestComputeWeeklyMinutes:
    """Test weekly practice minutes computation."""

    def test_no_durations_returns_zero(self):
        assert compute_weekly_minutes([]) == 0

    def test_sums_durations_in_seconds_to_minutes(self):
        # 300s + 600s + 900s = 1800s = 30 minutes
        assert compute_weekly_minutes([300, 600, 900]) == 30

    def test_rounds_down_partial_minutes(self):
        # 310s = 5 min 10 sec → 5 minutes
        assert compute_weekly_minutes([310]) == 5
