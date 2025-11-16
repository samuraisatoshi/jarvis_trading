"""
Candle scheduler for executing jobs at official candle close times.

This scheduler ensures jobs run at precise candle close times, not arbitrary delays.
Example: 1h candles close at :00 minute (14:00, 15:00, etc), not 1 hour after start.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Callable, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class CandleScheduler:
    """
    Schedules jobs to run at official candle close times.

    Timeframe schedules:
    - 1m:  Every minute at :00 seconds
    - 5m:  At :00, :05, :10, :15, :20, :25, :30, :35, :40, :45, :50, :55
    - 15m: At :00, :15, :30, :45
    - 30m: At :00, :30
    - 1h:  At minute :00 of each hour
    - 4h:  At 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC
    - 1d:  At 00:00:00 UTC
    - 1w:  Monday at 00:00:00 UTC
    """

    TIMEFRAME_INTERVALS = {
        "1m": 60,  # Seconds
        "5m": 300,
        "15m": 900,
        "30m": 1800,
        "1h": 3600,
        "4h": 14400,
        "1d": 86400,
        "1w": 604800,
    }

    def __init__(self):
        """Initialize scheduler."""
        self.jobs: Dict[str, asyncio.Task] = {}
        self.running_jobs: Dict[str, bool] = {}

    def get_next_candle_time(self, timeframe: str, reference_time: Optional[datetime] = None) -> datetime:
        """
        Calculate the exact time when next candle closes.

        Args:
            timeframe: Candle timeframe (1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w)
            reference_time: Reference time (default: current UTC time)

        Returns:
            datetime of next candle close in UTC
        """
        if reference_time is None:
            reference_time = datetime.utcnow()

        # Round down to UTC epoch for calculations
        epoch = datetime(1970, 1, 1)
        seconds_since_epoch = (reference_time - epoch).total_seconds()
        interval_seconds = self.TIMEFRAME_INTERVALS[timeframe]

        # Calculate how many seconds until next interval boundary
        remainder = int(seconds_since_epoch) % interval_seconds
        if remainder == 0 and reference_time.microsecond == 0:
            # Already at exact boundary
            seconds_to_next = interval_seconds
        else:
            seconds_to_next = interval_seconds - remainder

        next_time = reference_time + timedelta(seconds=seconds_to_next)

        # For specific timeframes, adjust to correct boundaries
        if timeframe == "1d":
            # 1d candles close at 00:00:00 UTC
            next_time = next_time.replace(hour=0, minute=0, second=0, microsecond=0)
            if next_time <= reference_time:
                next_time += timedelta(days=1)

        elif timeframe == "4h":
            # 4h candles close at 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC
            hour = next_time.hour
            if hour % 4 != 0:
                hour = (hour // 4 + 1) * 4
                if hour >= 24:
                    next_time = next_time.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                else:
                    next_time = next_time.replace(hour=hour, minute=0, second=0, microsecond=0)

        elif timeframe == "1w":
            # 1w candles close on Monday at 00:00:00 UTC
            # Weekday: 0=Monday, 6=Sunday
            current_weekday = reference_time.weekday()

            if current_weekday == 0 and reference_time.hour == 0 and reference_time.minute == 0 and reference_time.second == 0:
                # At exactly Monday midnight, next close is next Monday
                next_time = reference_time + timedelta(weeks=1)
            else:
                # Calculate days until next Monday
                days_until_monday = (7 - current_weekday) % 7
                if days_until_monday == 0:
                    # Same week, next Monday
                    days_until_monday = 7

                next_time = reference_time + timedelta(days=days_until_monday)
                next_time = next_time.replace(hour=0, minute=0, second=0, microsecond=0)

        # Ensure microseconds are 0
        next_time = next_time.replace(microsecond=0)

        return next_time

    def get_wait_seconds(self, timeframe: str, reference_time: Optional[datetime] = None) -> float:
        """
        Get seconds to wait until next candle close.

        Args:
            timeframe: Candle timeframe
            reference_time: Reference time (default: current UTC time)

        Returns:
            Seconds to wait (float with fractional seconds)
        """
        if reference_time is None:
            reference_time = datetime.utcnow()

        next_close = self.get_next_candle_time(timeframe, reference_time)
        wait_delta = next_close - reference_time

        return wait_delta.total_seconds()

    async def schedule_job(
        self, timeframe: str, callback: Callable, callback_args: tuple = (), callback_kwargs: dict = None
    ):
        """
        Schedule a job to run at candle close times.

        Job will run repeatedly at every candle close.

        Args:
            timeframe: Candle timeframe
            callback: Async callback to execute
            callback_args: Positional arguments for callback
            callback_kwargs: Keyword arguments for callback
        """
        if callback_kwargs is None:
            callback_kwargs = {}

        job_name = timeframe
        self.running_jobs[job_name] = True

        try:
            while self.running_jobs.get(job_name, False):
                # Calculate wait time until next candle close
                wait_seconds = self.get_wait_seconds(timeframe)

                logger.info(f"[{timeframe}] Next candle close in {wait_seconds:.1f} seconds")

                try:
                    # Wait until candle close
                    await asyncio.sleep(wait_seconds)

                    # Execute callback at exact candle close
                    now = datetime.utcnow()
                    logger.info(f"[{timeframe}] Candle closed at {now.isoformat()} UTC")

                    if asyncio.iscoroutinefunction(callback):
                        await callback(*callback_args, timeframe=timeframe, **callback_kwargs)
                    else:
                        callback(*callback_args, timeframe=timeframe, **callback_kwargs)

                except asyncio.CancelledError:
                    logger.info(f"[{timeframe}] Job cancelled")
                    break
                except Exception as e:
                    logger.error(f"[{timeframe}] Error executing callback: {e}", exc_info=True)
                    # Continue to next cycle on error

        except Exception as e:
            logger.error(f"[{timeframe}] Scheduler error: {e}", exc_info=True)
        finally:
            self.running_jobs[job_name] = False

    def start_job(self, timeframe: str, callback: Callable, callback_args: tuple = (), callback_kwargs: dict = None):
        """
        Start a scheduled job for a specific timeframe.

        Args:
            timeframe: Candle timeframe
            callback: Async callback to execute
            callback_args: Positional arguments for callback
            callback_kwargs: Keyword arguments for callback
        """
        if callback_kwargs is None:
            callback_kwargs = {}

        # Cancel existing job if any
        if timeframe in self.jobs:
            self.stop_job(timeframe)

        # Create and store task
        task = asyncio.create_task(self.schedule_job(timeframe, callback, callback_args, callback_kwargs))
        self.jobs[timeframe] = task

        next_run = self.get_next_candle_time(timeframe)
        logger.info(f"[{timeframe}] Job started. Next candle close: {next_run.isoformat()} UTC")

    def stop_job(self, timeframe: str):
        """Stop a scheduled job."""
        if timeframe in self.jobs:
            self.running_jobs[timeframe] = False
            self.jobs[timeframe].cancel()
            del self.jobs[timeframe]
            logger.info(f"[{timeframe}] Job stopped")

    def stop_all_jobs(self):
        """Stop all scheduled jobs."""
        for timeframe in list(self.jobs.keys()):
            self.stop_job(timeframe)

    def get_active_jobs(self) -> list:
        """Get list of active job timeframes."""
        return list(self.jobs.keys())

    def get_job_status(self, timeframe: str) -> Optional[Dict]:
        """Get status of a job."""
        if timeframe not in self.jobs:
            return None

        task = self.jobs[timeframe]
        next_close = self.get_next_candle_time(timeframe)
        wait_seconds = self.get_wait_seconds(timeframe)

        return {
            "timeframe": timeframe,
            "active": not task.done(),
            "next_close": next_close.isoformat(),
            "wait_seconds": wait_seconds,
        }

    async def cleanup(self):
        """Cleanup resources."""
        self.stop_all_jobs()
        await asyncio.sleep(0.1)  # Allow tasks to finish
