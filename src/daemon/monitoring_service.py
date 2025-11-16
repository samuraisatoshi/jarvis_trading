"""
Daemon health monitoring service.

Tracks daemon metrics, health status, and sends periodic reports.
"""

from typing import List, Dict
from loguru import logger
from datetime import datetime, timezone, timedelta

from .models import Signal, TradeResult
from .portfolio_service import PortfolioService
from .notification_handler import NotificationHandler


class MonitoringService:
    """
    Daemon health monitoring service.

    Tracks operational metrics, monitors daemon health,
    and coordinates periodic status reporting.
    """

    def __init__(
        self,
        portfolio_service: PortfolioService,
        notification_handler: NotificationHandler
    ):
        """
        Initialize monitoring service.

        Args:
            portfolio_service: Portfolio service for status queries
            notification_handler: Notification handler for alerts
        """
        self.portfolio_service = portfolio_service
        self.notification_handler = notification_handler

        # Metrics
        self.signal_checks = 0
        self.signals_detected = 0
        self.trades_executed = 0
        self.trades_failed = 0
        self.start_time = datetime.now(timezone.utc)
        self.last_error: Dict = {}

    def record_signal_check(self, signals: List[Signal]) -> None:
        """
        Record signal check event.

        Args:
            signals: Signals found in this check
        """
        self.signal_checks += 1
        self.signals_detected += len(signals)

        if signals:
            logger.info(
                f"Signal check #{self.signal_checks}: "
                f"{len(signals)} signals found"
            )
        else:
            logger.debug(
                f"Signal check #{self.signal_checks}: No signals"
            )

    def record_trade_execution(self, result: TradeResult) -> None:
        """
        Record trade execution result.

        Args:
            result: Trade execution result
        """
        if result.success:
            self.trades_executed += 1
            logger.info(f"✅ Trade #{self.trades_executed}: {result}")
        else:
            self.trades_failed += 1
            logger.warning(f"❌ Trade failed: {result.error}")

            # Record error
            self.last_error = {
                'timestamp': datetime.now(timezone.utc),
                'type': 'trade_execution',
                'signal': str(result.signal),
                'error': result.error
            }

    def record_error(
        self,
        error_type: str,
        error: str,
        context: str = ""
    ) -> None:
        """
        Record error event.

        Args:
            error_type: Type of error
            error: Error message
            context: Additional context
        """
        self.last_error = {
            'timestamp': datetime.now(timezone.utc),
            'type': error_type,
            'error': error,
            'context': context
        }

        logger.error(f"{error_type}: {error} ({context})")

    def get_health_status(self) -> Dict:
        """
        Get daemon health status.

        Returns:
            Dict with health metrics and status
        """
        now = datetime.now(timezone.utc)
        uptime = now - self.start_time
        uptime_hours = uptime.total_seconds() / 3600

        # Calculate success rate
        total_trades = self.trades_executed + self.trades_failed
        success_rate = (
            self.trades_executed / total_trades
            if total_trades > 0
            else 1.0
        )

        # Calculate signals per hour
        signals_per_hour = (
            self.signals_detected / uptime_hours
            if uptime_hours > 0
            else 0
        )

        return {
            'uptime_hours': uptime_hours,
            'uptime_formatted': self._format_uptime(uptime),
            'signal_checks': self.signal_checks,
            'signals_detected': self.signals_detected,
            'signals_per_hour': signals_per_hour,
            'trades_executed': self.trades_executed,
            'trades_failed': self.trades_failed,
            'success_rate': success_rate,
            'last_error': self.last_error,
            'status': self._determine_health_status(success_rate)
        }

    def send_periodic_report(
        self,
        watchlist: List[str],
        include_health: bool = True
    ) -> None:
        """
        Send periodic status report.

        Args:
            watchlist: List of symbols to report on
            include_health: Include health metrics in report
        """
        try:
            # Get portfolio status
            portfolio = self.portfolio_service.get_portfolio_status(watchlist)
            self.notification_handler.send_status_update(portfolio)

            # Log health metrics
            if include_health:
                health = self.get_health_status()
                logger.info(
                    f"Health: {health['uptime_formatted']}, "
                    f"{health['trades_executed']} trades, "
                    f"{health['success_rate']:.1%} success rate, "
                    f"Status: {health['status']}"
                )

        except Exception as e:
            logger.error(f"Failed to send periodic report: {e}")
            self.record_error('periodic_report', str(e))

    def send_health_alert_if_needed(self) -> None:
        """
        Send health alert if daemon health is degraded.

        Alerts on:
        - Success rate < 50%
        - Recent errors
        """
        health = self.get_health_status()

        # Check success rate
        if health['success_rate'] < 0.5 and health['trades_executed'] > 5:
            self.notification_handler.send_error_alert(
                f"Low success rate: {health['success_rate']:.1%}",
                f"{health['trades_failed']} of "
                f"{health['trades_executed'] + health['trades_failed']} trades failed"
            )

        # Check recent errors
        if self.last_error:
            error_time = self.last_error['timestamp']
            age = datetime.now(timezone.utc) - error_time

            # Alert if error in last hour
            if age < timedelta(hours=1):
                self.notification_handler.send_error_alert(
                    self.last_error['error'],
                    f"Type: {self.last_error['type']}, "
                    f"Context: {self.last_error.get('context', 'N/A')}"
                )

    def get_metrics_summary(self) -> str:
        """
        Get formatted metrics summary.

        Returns:
            Human-readable metrics string
        """
        health = self.get_health_status()

        summary = "📊 Daemon Metrics\n"
        summary += f"Uptime: {health['uptime_formatted']}\n"
        summary += f"Signal Checks: {health['signal_checks']}\n"
        summary += f"Signals Detected: {health['signals_detected']} "
        summary += f"({health['signals_per_hour']:.1f}/hr)\n"
        summary += f"Trades Executed: {health['trades_executed']}\n"
        summary += f"Trades Failed: {health['trades_failed']}\n"
        summary += f"Success Rate: {health['success_rate']:.1%}\n"
        summary += f"Status: {health['status']}"

        return summary

    def _format_uptime(self, uptime: timedelta) -> str:
        """
        Format uptime as readable string.

        Args:
            uptime: Time delta

        Returns:
            Formatted string (e.g., "2d 3h 15m")
        """
        days = uptime.days
        hours = uptime.seconds // 3600
        minutes = (uptime.seconds % 3600) // 60

        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")

        return " ".join(parts) if parts else "< 1m"

    def _determine_health_status(self, success_rate: float) -> str:
        """
        Determine health status from metrics.

        Args:
            success_rate: Trade success rate (0-1)

        Returns:
            Health status string
        """
        if success_rate >= 0.9:
            return "HEALTHY"
        elif success_rate >= 0.7:
            return "GOOD"
        elif success_rate >= 0.5:
            return "DEGRADED"
        else:
            return "UNHEALTHY"
