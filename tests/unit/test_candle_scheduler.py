"""
Unit tests for CandleScheduler.

Tests candle close time calculation for all timeframes.
"""
import pytest
from datetime import datetime, timedelta
from src.domain.market_data.services.candle_scheduler import CandleScheduler


class TestCandleScheduler:
    """Test suite for CandleScheduler."""

    @pytest.fixture
    def scheduler(self):
        """Create scheduler instance."""
        return CandleScheduler()

    def test_get_next_candle_time_1m(self, scheduler):
        """Test 1m candle close calculation."""
        # Reference: 14:30:45 UTC
        ref = datetime(2024, 11, 14, 14, 30, 45)

        next_close = scheduler.get_next_candle_time("1m", ref)

        # Should close at 14:31:00
        expected = datetime(2024, 11, 14, 14, 31, 0)
        assert next_close == expected

    def test_get_next_candle_time_5m(self, scheduler):
        """Test 5m candle close calculation."""
        # Reference: 14:00:30 UTC
        ref = datetime(2024, 11, 14, 14, 0, 30)

        next_close = scheduler.get_next_candle_time("5m", ref)

        # Should close at 14:05:00
        expected = datetime(2024, 11, 14, 14, 5, 0)
        assert next_close == expected

    def test_get_next_candle_time_5m_at_boundary(self, scheduler):
        """Test 5m when exactly at boundary."""
        ref = datetime(2024, 11, 14, 14, 15, 0)

        next_close = scheduler.get_next_candle_time("5m", ref)

        # Should close at next boundary 14:20:00
        expected = datetime(2024, 11, 14, 14, 20, 0)
        assert next_close == expected

    def test_get_next_candle_time_15m(self, scheduler):
        """Test 15m candle close calculation."""
        # Reference: 14:20:30 UTC
        ref = datetime(2024, 11, 14, 14, 20, 30)

        next_close = scheduler.get_next_candle_time("15m", ref)

        # Should close at 14:30:00
        expected = datetime(2024, 11, 14, 14, 30, 0)
        assert next_close == expected

    def test_get_next_candle_time_30m(self, scheduler):
        """Test 30m candle close calculation."""
        # Reference: 14:20:30 UTC
        ref = datetime(2024, 11, 14, 14, 20, 30)

        next_close = scheduler.get_next_candle_time("30m", ref)

        # Should close at 14:30:00
        expected = datetime(2024, 11, 14, 14, 30, 0)
        assert next_close == expected

    def test_get_next_candle_time_1h(self, scheduler):
        """Test 1h candle close calculation."""
        # Reference: 14:30:45 UTC
        ref = datetime(2024, 11, 14, 14, 30, 45)

        next_close = scheduler.get_next_candle_time("1h", ref)

        # Should close at 15:00:00
        expected = datetime(2024, 11, 14, 15, 0, 0)
        assert next_close == expected

    def test_get_next_candle_time_1h_at_boundary(self, scheduler):
        """Test 1h when exactly at boundary."""
        ref = datetime(2024, 11, 14, 14, 0, 0)

        next_close = scheduler.get_next_candle_time("1h", ref)

        # Should close at next hour 15:00:00
        expected = datetime(2024, 11, 14, 15, 0, 0)
        assert next_close == expected

    def test_get_next_candle_time_4h(self, scheduler):
        """Test 4h candle close calculation."""
        # Reference: 14:30:45 UTC (after 12:00, next is 16:00)
        ref = datetime(2024, 11, 14, 14, 30, 45)

        next_close = scheduler.get_next_candle_time("4h", ref)

        # Should close at 16:00:00
        expected = datetime(2024, 11, 14, 16, 0, 0)
        assert next_close == expected

    def test_get_next_candle_time_4h_boundaries(self, scheduler):
        """Test 4h closes at specific hours."""
        # Test multiple times to verify boundaries
        test_cases = [
            # (reference_time, expected_next_close)
            (datetime(2024, 11, 14, 0, 30, 0), datetime(2024, 11, 14, 4, 0, 0)),   # 00:30 -> 04:00
            (datetime(2024, 11, 14, 4, 30, 0), datetime(2024, 11, 14, 8, 0, 0)),   # 04:30 -> 08:00
            (datetime(2024, 11, 14, 8, 30, 0), datetime(2024, 11, 14, 12, 0, 0)),  # 08:30 -> 12:00
            (datetime(2024, 11, 14, 12, 30, 0), datetime(2024, 11, 14, 16, 0, 0)), # 12:30 -> 16:00
            (datetime(2024, 11, 14, 16, 30, 0), datetime(2024, 11, 14, 20, 0, 0)), # 16:30 -> 20:00
            (datetime(2024, 11, 14, 20, 30, 0), datetime(2024, 11, 15, 0, 0, 0)),  # 20:30 -> 00:00 next day
        ]

        for ref, expected in test_cases:
            next_close = scheduler.get_next_candle_time("4h", ref)
            assert next_close == expected, f"Failed for {ref}: got {next_close}, expected {expected}"

    def test_get_next_candle_time_1d(self, scheduler):
        """Test 1d candle close calculation."""
        # Reference: 2024-11-14 14:30:45 UTC
        ref = datetime(2024, 11, 14, 14, 30, 45)

        next_close = scheduler.get_next_candle_time("1d", ref)

        # Should close at 2024-11-15 00:00:00
        expected = datetime(2024, 11, 15, 0, 0, 0)
        assert next_close == expected

    def test_get_next_candle_time_1d_at_midnight(self, scheduler):
        """Test 1d when exactly at midnight."""
        # Reference: 2024-11-14 00:00:00 UTC
        ref = datetime(2024, 11, 14, 0, 0, 0)

        next_close = scheduler.get_next_candle_time("1d", ref)

        # Should close at next midnight 2024-11-15 00:00:00
        expected = datetime(2024, 11, 15, 0, 0, 0)
        assert next_close == expected

    def test_get_next_candle_time_1w(self, scheduler):
        """Test 1w candle close calculation."""
        # Reference: Thursday 2024-11-14 14:30:45 UTC
        ref = datetime(2024, 11, 14, 14, 30, 45)

        next_close = scheduler.get_next_candle_time("1w", ref)

        # Should close at Monday 2024-11-18 00:00:00
        expected = datetime(2024, 11, 18, 0, 0, 0)
        assert next_close == expected

    def test_get_next_candle_time_1w_on_monday(self, scheduler):
        """Test 1w when on Monday."""
        # Reference: Monday 2024-11-11 14:30:45 UTC
        ref = datetime(2024, 11, 11, 14, 30, 45)

        next_close = scheduler.get_next_candle_time("1w", ref)

        # Should close at next Monday 2024-11-18 00:00:00
        expected = datetime(2024, 11, 18, 0, 0, 0)
        assert next_close == expected

    def test_get_wait_seconds(self, scheduler):
        """Test wait seconds calculation."""
        # Reference: 14:00:30 UTC
        ref = datetime(2024, 11, 14, 14, 0, 30)

        wait_seconds = scheduler.get_wait_seconds("1h", ref)

        # Should wait 3570 seconds until 15:00:00
        expected = 3570.0
        assert abs(wait_seconds - expected) < 0.1  # Allow small float difference

    def test_microseconds_are_zero(self, scheduler):
        """Verify all closes have microseconds = 0."""
        ref = datetime(2024, 11, 14, 14, 30, 45, 123456)

        for timeframe in ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"]:
            next_close = scheduler.get_next_candle_time(timeframe, ref)
            assert next_close.microsecond == 0, f"{timeframe} has non-zero microseconds"

    def test_all_timeframes_supported(self, scheduler):
        """Verify all timeframes are supported."""
        ref = datetime(2024, 11, 14, 14, 30, 45)

        for timeframe in ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"]:
            next_close = scheduler.get_next_candle_time(timeframe, ref)
            assert next_close > ref, f"Timeframe {timeframe} returned past time"
            assert next_close.microsecond == 0, f"Timeframe {timeframe} has microseconds"


class TestCandleSchedulerJobStatus:
    """Test job status tracking."""

    @pytest.fixture
    def scheduler(self):
        """Create scheduler instance."""
        return CandleScheduler()

    def test_get_active_jobs_empty(self, scheduler):
        """Test active jobs when none running."""
        assert scheduler.get_active_jobs() == []

    def test_get_job_status_not_found(self, scheduler):
        """Test getting status of non-existent job."""
        status = scheduler.get_job_status("1h")
        assert status is None


class TestCandleSchedulerEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def scheduler(self):
        """Create scheduler instance."""
        return CandleScheduler()

    def test_end_of_day_1h(self, scheduler):
        """Test 1h calculation at end of day."""
        # Reference: 23:30:45 UTC
        ref = datetime(2024, 11, 14, 23, 30, 45)

        next_close = scheduler.get_next_candle_time("1h", ref)

        # Should close at 00:00:00 next day
        expected = datetime(2024, 11, 15, 0, 0, 0)
        assert next_close == expected

    def test_end_of_day_5m(self, scheduler):
        """Test 5m calculation at end of day."""
        # Reference: 23:56:45 UTC
        ref = datetime(2024, 11, 14, 23, 56, 45)

        next_close = scheduler.get_next_candle_time("5m", ref)

        # Should close at 00:00:00 next day
        expected = datetime(2024, 11, 15, 0, 0, 0)
        assert next_close == expected

    def test_leap_year(self, scheduler):
        """Test 1d calculation on leap year (2024 is leap year)."""
        # Reference: 2024-02-28 14:30:00 (not leap year day)
        ref = datetime(2024, 2, 28, 14, 30, 0)

        next_close = scheduler.get_next_candle_time("1d", ref)

        # Should close at 2024-02-29 00:00:00 (leap day)
        expected = datetime(2024, 2, 29, 0, 0, 0)
        assert next_close == expected

    def test_year_boundary(self, scheduler):
        """Test calculation at year boundary."""
        # Reference: 2024-12-31 23:30:00 UTC
        ref = datetime(2024, 12, 31, 23, 30, 0)

        next_close = scheduler.get_next_candle_time("1h", ref)

        # Should close at 2025-01-01 00:00:00
        expected = datetime(2025, 1, 1, 0, 0, 0)
        assert next_close == expected
