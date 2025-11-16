"""
Monitoring Application Service

Orchestrates daemon monitoring operations, coordinating between
domain services, repositories, and system resources.
"""

import json
import logging
import os
import signal
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from src.domain.monitoring import (
    CircuitBreakerManager,
    HealthAssessor,
    HealthReport
)
from src.infrastructure.persistence.sqlite_metrics_repository import (
    SQLiteMetricsRepository
)

logger = logging.getLogger(__name__)


class DaemonStatus:
    """Daemon process status information."""

    def __init__(
        self,
        running: bool,
        pid: Optional[int] = None,
        uptime_seconds: float = 0.0
    ):
        self.running = running
        self.pid = pid
        self.uptime_seconds = uptime_seconds


class MonitoringApplicationService:
    """
    Application service for daemon monitoring operations.

    Coordinates between CLI, domain services, and infrastructure to provide
    monitoring, control, and health assessment capabilities.
    """

    def __init__(
        self,
        db_path: Path,
        pid_file: Path,
        control_file: Path,
        log_file: Path
    ):
        """
        Initialize monitoring service.

        Args:
            db_path: Path to paper trading database
            pid_file: Path to daemon PID file
            control_file: Path to daemon control file
            log_file: Path to daemon log file
        """
        self.db_path = db_path
        self.pid_file = pid_file
        self.control_file = control_file
        self.log_file = log_file

        # Initialize dependencies
        self.metrics_repo = SQLiteMetricsRepository(db_path)
        self.breaker_manager = CircuitBreakerManager()
        self.health_assessor = HealthAssessor(self.breaker_manager)

    def get_daemon_status(self) -> DaemonStatus:
        """
        Get current daemon process status.

        Returns:
            DaemonStatus with running state, PID, and uptime
        """
        if not self.pid_file.exists():
            return DaemonStatus(running=False)

        try:
            with open(self.pid_file) as f:
                pid = int(f.read().strip())

            # Check if process exists
            os.kill(pid, 0)  # Signal 0 doesn't kill, just checks

            # Calculate uptime
            stat = self.pid_file.stat()
            created = datetime.fromtimestamp(stat.st_ctime)
            uptime = (datetime.now() - created).total_seconds()

            return DaemonStatus(
                running=True,
                pid=pid,
                uptime_seconds=uptime
            )

        except (ProcessLookupError, ValueError, OSError):
            # PID file exists but process doesn't
            self.pid_file.unlink(missing_ok=True)
            return DaemonStatus(running=False)

    def get_health_report(self) -> HealthReport:
        """
        Generate comprehensive health assessment report.

        Returns:
            HealthReport with metrics, breakers, alerts, and recommendations
        """
        status = self.get_daemon_status()
        metrics = self.metrics_repo.get_performance_metrics()

        report = self.health_assessor.assess(
            metrics=metrics,
            daemon_running=status.running,
            daemon_pid=status.pid,
            daemon_uptime=status.uptime_seconds
        )

        return report

    def pause_trading(self, reason: str = "Manual intervention") -> bool:
        """
        Pause trading by setting control flag.

        Args:
            reason: Reason for pause

        Returns:
            True if successful, False if daemon not running
        """
        status = self.get_daemon_status()

        if not status.running:
            logger.error("Cannot pause: daemon not running")
            return False

        control = {
            "action": "pause",
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        }

        with open(self.control_file, 'w') as f:
            json.dump(control, f, indent=2)

        logger.info(f"Trading paused (PID {status.pid}): {reason}")
        return True

    def resume_trading(self) -> bool:
        """
        Resume trading by clearing control flag.

        Returns:
            True if successful, False if daemon not running
        """
        status = self.get_daemon_status()

        if not status.running:
            logger.error("Cannot resume: daemon not running")
            return False

        control = {
            "action": "resume",
            "timestamp": datetime.now().isoformat()
        }

        with open(self.control_file, 'w') as f:
            json.dump(control, f, indent=2)

        # Reset circuit breakers
        self.breaker_manager.reset_all()

        logger.info(f"Trading resumed (PID {status.pid})")
        return True

    def stop_daemon(self, force: bool = False) -> bool:
        """
        Stop daemon process.

        Args:
            force: If True, use SIGKILL immediately

        Returns:
            True if stopped successfully
        """
        status = self.get_daemon_status()

        if not status.running:
            logger.error("Daemon not running")
            return False

        try:
            if force:
                os.kill(status.pid, signal.SIGKILL)
                self.pid_file.unlink(missing_ok=True)
                logger.info(f"Daemon killed (PID {status.pid})")
                return True

            # Send SIGTERM for graceful shutdown
            os.kill(status.pid, signal.SIGTERM)
            logger.info(f"Stop signal sent to daemon (PID {status.pid})")

            # Wait up to 10 seconds
            for _ in range(10):
                time.sleep(1)
                if not self.get_daemon_status().running:
                    logger.info("Daemon stopped gracefully")
                    return True

            # Force kill if still running
            logger.warning("Graceful shutdown timeout, forcing...")
            os.kill(status.pid, signal.SIGKILL)
            self.pid_file.unlink(missing_ok=True)
            logger.info("Daemon killed")
            return True

        except Exception as e:
            logger.error(f"Error stopping daemon: {e}")
            return False

    def start_daemon(self) -> bool:
        """
        Start daemon process.

        Note: Currently not implemented - daemon must be started manually.

        Returns:
            False (not implemented)
        """
        status = self.get_daemon_status()

        if status.running:
            logger.error("Daemon already running")
            return False

        # TODO: Implement daemon start
        logger.warning("Start command not implemented yet")
        logger.info("Run daemon manually from jarvis_trading directory")
        return False

    def read_logs(self, lines: int = 50) -> List[str]:
        """
        Read recent log lines.

        Args:
            lines: Number of lines to read

        Returns:
            List of log lines
        """
        if not self.log_file.exists():
            logger.error(f"Log file not found: {self.log_file}")
            return []

        try:
            with open(self.log_file) as f:
                all_lines = f.readlines()
                return all_lines[-lines:]
        except Exception as e:
            logger.error(f"Error reading logs: {e}")
            return []

    def format_duration(self, seconds: float) -> str:
        """
        Format duration in human-readable format.

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted string (e.g., "2d 3h 15m")
        """
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            return f"{seconds/60:.0f}m"
        elif seconds < 86400:
            hours = seconds / 3600
            return f"{hours:.1f}h"
        else:
            days = seconds / 86400
            return f"{days:.1f}d"
