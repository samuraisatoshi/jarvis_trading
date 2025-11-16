#!/usr/bin/env python3
"""
Automatic Health Check (for Cron)

This script runs periodically (e.g., every hour) to check
trading daemon health and take automatic action if needed.

JARVIS uses this for autonomous supervision.

Usage (cron):
    0 * * * * cd /path/to/jarvis_trading && python scripts/auto_health_check.py

Actions taken automatically:
- Pause trading if circuit breakers trigger
- Send alert notifications
- Log health report
- Take emergency stop action if critical
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.monitor_paper_trading import DaemonMonitor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/health_checks.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

ALERT_FILE = Path(__file__).parent.parent / "health_alerts.json"


class AutoHealthChecker:
    """Automatic health monitoring with autonomous actions."""

    def __init__(self):
        self.monitor = DaemonMonitor()
        self.alerts_sent = []

    def run(self):
        """Run health check and take action if needed."""
        logger.info("=== Automatic Health Check Started ===")

        # Check daemon status
        is_running, pid = self.monitor.is_running()

        if not is_running:
            logger.warning("Daemon not running - skipping health check")
            self._send_alert(
                severity="critical",
                title="Daemon Not Running",
                message="Paper trading daemon is not running. "
                        "Start manually if needed."
            )
            return

        # Get health report
        uptime = self.monitor.get_daemon_uptime(pid)
        metrics = self.monitor.get_metrics()

        report = self.monitor.health_assessor.assess(
            metrics=metrics,
            daemon_running=is_running,
            daemon_pid=pid,
            daemon_uptime=uptime
        )

        # Log health status
        logger.info(f"Health Status: {report.status.value}")
        logger.info(f"Risk Score: {report.risk_score:.0f}/100")
        logger.info(
            f"Portfolio: ${report.metrics.portfolio_value:,.2f} | "
            f"Daily P&L: {report.metrics.daily_pnl_pct:+.2%}"
        )

        # Save health report
        self._save_health_report(report)

        # Take automatic action
        if report.should_stop:
            logger.critical("CRITICAL RISK - Stopping daemon")
            self.monitor.stop()
            self._send_alert(
                severity="critical",
                title="Emergency Stop Triggered",
                message=f"Risk score: {report.risk_score:.0f}/100. "
                        f"Daemon stopped automatically. "
                        f"Recommendations: {', '.join(report.recommendations)}"
            )

        elif report.should_pause:
            logger.warning("HIGH RISK - Pausing trading")
            breakers = [
                cb.name for cb in report.circuit_breakers
                if cb.state.value == "open"
            ]
            reason = f"Circuit breakers: {', '.join(breakers)}" if breakers else "High risk detected"
            self.monitor.pause(reason=reason)
            self._send_alert(
                severity="warning",
                title="Trading Paused Automatically",
                message=f"Risk score: {report.risk_score:.0f}/100. "
                        f"Reason: {reason}"
            )

        # Check specific alerts
        for alert in report.active_alerts:
            if alert.severity.value == "critical":
                self._send_alert(
                    severity=alert.severity.value,
                    title=alert.title,
                    message=alert.message
                )

        logger.info(f"Health check complete. Status: {report.status.value}")

    def _save_health_report(self, report):
        """Save health report to file for JARVIS analysis."""
        reports_dir = Path(__file__).parent.parent / "logs" / "health_reports"
        reports_dir.mkdir(exist_ok=True, parents=True)

        filename = (
            f"health_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        filepath = reports_dir / filename

        with open(filepath, 'w') as f:
            json.dump(report.to_dict(), f, indent=2)

        logger.info(f"Health report saved: {filepath}")

    def _send_alert(self, severity: str, title: str, message: str):
        """
        Send alert notification.

        In production, this would:
        - Send email
        - Send SMS
        - Post to Slack/Discord
        - Log to monitoring system
        """
        alert = {
            "timestamp": datetime.now().isoformat(),
            "severity": severity,
            "title": title,
            "message": message
        }

        # Log alert
        log_func = {
            "info": logger.info,
            "warning": logger.warning,
            "critical": logger.critical
        }.get(severity, logger.info)

        log_func(f"ALERT: {title} - {message}")

        # Save alert to file
        self.alerts_sent.append(alert)

        # Append to alerts file
        alerts = []
        if ALERT_FILE.exists():
            with open(ALERT_FILE) as f:
                try:
                    alerts = json.load(f)
                except json.JSONDecodeError:
                    alerts = []

        alerts.append(alert)

        # Keep only last 100 alerts
        alerts = alerts[-100:]

        with open(ALERT_FILE, 'w') as f:
            json.dump(alerts, f, indent=2)

        # TODO: Implement actual notification
        # - Email via SMTP
        # - SMS via Twilio
        # - Slack webhook
        # - Context memory message to JARVIS


def main():
    """Main entry point for cron job."""
    try:
        checker = AutoHealthChecker()
        checker.run()
    except Exception as e:
        logger.exception(f"Health check failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
