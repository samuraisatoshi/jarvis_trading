#!/usr/bin/env python3
"""
Paper Trading Daemon Monitor

JARVIS uses this script to supervise and control the paper trading daemon.

Commands:
    status  - Check daemon status and health
    health  - Full health report with recommendations
    pause   - Pause trading (circuit breaker manual)
    resume  - Resume trading
    stop    - Kill daemon process
    start   - Start daemon
    logs    - View recent logs

Usage:
    python scripts/monitor_paper_trading.py status
    python scripts/monitor_paper_trading.py health --json
    python scripts/monitor_paper_trading.py pause --reason "High drawdown"
"""

import argparse
import json
import logging
import os
import signal
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.domain.monitoring import (
    CircuitBreakerManager,
    HealthAssessor,
    PerformanceMetrics
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
PID_FILE = Path(__file__).parent.parent / "paper_trading.pid"
CONTROL_FILE = Path(__file__).parent.parent / "paper_trading.control"
DB_PATH = Path(__file__).parent.parent / "paper_trading.db"


class DaemonMonitor:
    """Monitor and control paper trading daemon."""

    def __init__(self):
        self.breaker_manager = CircuitBreakerManager()
        self.health_assessor = HealthAssessor(self.breaker_manager)

    def is_running(self) -> tuple[bool, Optional[int]]:
        """
        Check if daemon is running.

        Returns:
            (is_running, pid)
        """
        if not PID_FILE.exists():
            return False, None

        try:
            with open(PID_FILE) as f:
                pid = int(f.read().strip())

            # Check if process exists
            os.kill(pid, 0)  # Signal 0 doesn't kill, just checks
            return True, pid

        except (ProcessLookupError, ValueError, OSError):
            # PID file exists but process doesn't
            PID_FILE.unlink(missing_ok=True)
            return False, None

    def get_daemon_uptime(self, pid: Optional[int]) -> float:
        """Get daemon uptime in seconds."""
        if not pid or not PID_FILE.exists():
            return 0.0

        try:
            stat = PID_FILE.stat()
            created = datetime.fromtimestamp(stat.st_ctime)
            return (datetime.now() - created).total_seconds()
        except Exception:
            return 0.0

    def get_metrics(self) -> PerformanceMetrics:
        """
        Fetch current performance metrics from database.

        Returns:
            PerformanceMetrics with current state
        """
        # TODO: Implement actual database query
        # For now, return mock data structure
        import sqlite3

        if not DB_PATH.exists():
            logger.warning("Database not found, using default metrics")
            return self._default_metrics()

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            # Get portfolio value
            cursor.execute(
                "SELECT value FROM portfolio_state "
                "ORDER BY timestamp DESC LIMIT 1"
            )
            row = cursor.fetchone()
            portfolio_value = row[0] if row else 10000.0

            # Get daily trades
            today_start = datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            cursor.execute(
                "SELECT COUNT(*), "
                "SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END), "
                "SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END), "
                "SUM(pnl) "
                "FROM trades "
                "WHERE exit_timestamp >= ? AND status = 'CLOSED'",
                (today_start.timestamp(),)
            )
            row = cursor.fetchone()
            total_trades = row[0] or 0
            winning_trades = row[1] or 0
            losing_trades = row[2] or 0
            daily_pnl = row[3] or 0.0

            # Get consecutive losses
            cursor.execute(
                "SELECT pnl FROM trades "
                "WHERE status = 'CLOSED' "
                "ORDER BY exit_timestamp DESC LIMIT 10"
            )
            recent_pnls = [row[0] for row in cursor.fetchall()]
            consecutive_losses = 0
            for pnl in recent_pnls:
                if pnl < 0:
                    consecutive_losses += 1
                else:
                    break

            # Get drawdown (simplified)
            cursor.execute(
                "SELECT MAX(value) - MIN(value) FROM portfolio_state "
                "WHERE timestamp >= ?",
                ((datetime.now() - timedelta(days=30)).timestamp(),)
            )
            row = cursor.fetchone()
            max_drawdown = row[0] / portfolio_value if row and row[0] else 0.0

            # Get active positions
            cursor.execute(
                "SELECT COUNT(*) FROM trades WHERE status = 'ACTIVE'"
            )
            active_positions = cursor.fetchone()[0]

            # Calculate metrics
            win_rate = (
                winning_trades / total_trades
                if total_trades > 0 else 0.0
            )
            daily_pnl_pct = daily_pnl / portfolio_value
            sharpe_ratio = 1.5  # TODO: Calculate from returns

            # Get API latency (from last ping)
            cursor.execute(
                "SELECT latency_ms FROM api_health "
                "ORDER BY timestamp DESC LIMIT 1"
            )
            row = cursor.fetchone()
            api_latency = row[0] if row else 100.0

            # Get data freshness
            cursor.execute(
                "SELECT MAX(timestamp) FROM market_data"
            )
            row = cursor.fetchone()
            if row and row[0]:
                last_update = datetime.fromtimestamp(row[0])
                data_freshness = (
                    datetime.now() - last_update
                ).total_seconds()
            else:
                data_freshness = 0.0

            conn.close()

            return PerformanceMetrics(
                timestamp=datetime.now(),
                portfolio_value=portfolio_value,
                daily_pnl=daily_pnl,
                daily_pnl_pct=daily_pnl_pct,
                drawdown=max_drawdown,
                sharpe_ratio=sharpe_ratio,
                win_rate=win_rate,
                profit_factor=2.0,  # TODO: Calculate
                active_positions=active_positions,
                total_trades_today=total_trades,
                winning_trades_today=winning_trades,
                losing_trades_today=losing_trades,
                consecutive_losses=consecutive_losses,
                api_latency_ms=api_latency,
                data_freshness_seconds=data_freshness
            )

        except Exception as e:
            logger.error(f"Error fetching metrics: {e}")
            return self._default_metrics()

    def _default_metrics(self) -> PerformanceMetrics:
        """Return default metrics when data unavailable."""
        return PerformanceMetrics(
            timestamp=datetime.now(),
            portfolio_value=10000.0,
            daily_pnl=0.0,
            daily_pnl_pct=0.0,
            drawdown=0.0,
            sharpe_ratio=0.0,
            win_rate=0.0,
            profit_factor=0.0,
            active_positions=0,
            total_trades_today=0,
            winning_trades_today=0,
            losing_trades_today=0,
            consecutive_losses=0,
            api_latency_ms=0.0,
            data_freshness_seconds=0.0
        )

    def status(self, as_json: bool = False):
        """Print daemon status."""
        is_running, pid = self.is_running()
        uptime = self.get_daemon_uptime(pid)

        if as_json:
            data = {
                "running": is_running,
                "pid": pid,
                "uptime_seconds": uptime,
                "uptime_human": self._format_duration(uptime)
            }
            print(json.dumps(data, indent=2))
        else:
            status_emoji = "🟢" if is_running else "🔴"
            status_text = "RUNNING" if is_running else "STOPPED"

            print(f"\n{status_emoji} Paper Trading Daemon: {status_text}")
            if is_running:
                print(f"   PID: {pid}")
                print(f"   Uptime: {self._format_duration(uptime)}")
            print()

    def health(self, as_json: bool = False):
        """Generate full health report."""
        is_running, pid = self.is_running()
        uptime = self.get_daemon_uptime(pid)
        metrics = self.get_metrics()

        report = self.health_assessor.assess(
            metrics=metrics,
            daemon_running=is_running,
            daemon_pid=pid,
            daemon_uptime=uptime
        )

        if as_json:
            print(json.dumps(report.to_dict(), indent=2))
        else:
            self._print_health_report(report)

    def _print_health_report(self, report):
        """Print formatted health report."""
        # Status header
        status_emoji = {
            "healthy": "🟢",
            "degraded": "🟡",
            "unhealthy": "🟠",
            "critical": "🔴"
        }
        emoji = status_emoji.get(report.status.value, "⚪")

        print(f"\n{emoji} HEALTH STATUS: {report.status.value.upper()}")
        print(f"   Timestamp: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Risk Score: {report.risk_score:.0f}/100")

        # Daemon
        print(f"\n📊 DAEMON")
        daemon_status = "RUNNING" if report.daemon_running else "STOPPED"
        print(f"   Status: {daemon_status}")
        if report.daemon_pid:
            print(f"   PID: {report.daemon_pid}")
            print(
                f"   Uptime: "
                f"{self._format_duration(report.daemon_uptime_seconds)}"
            )

        # Metrics
        m = report.metrics
        print(f"\n💰 PERFORMANCE")
        print(f"   Portfolio: ${m.portfolio_value:,.2f}")
        print(f"   Daily P&L: ${m.daily_pnl:+,.2f} ({m.daily_pnl_pct:+.2%})")
        print(f"   Drawdown: {m.drawdown:.2%}")
        print(f"   Win Rate: {m.win_rate:.1%}")
        print(f"   Sharpe: {m.sharpe_ratio:.2f}")
        print(f"   Active: {m.active_positions} positions")
        print(f"   Consecutive Losses: {m.consecutive_losses}")

        # Circuit breakers
        active_breakers = [
            cb for cb in report.circuit_breakers
            if cb.state.value == "open"
        ]
        if active_breakers:
            print(f"\n⚠️  CIRCUIT BREAKERS ({len(active_breakers)} ACTIVE)")
            for cb in active_breakers:
                print(f"   • {cb.name}: {cb.description}")
                print(f"     Current: {cb.current_value:.2f} | "
                      f"Threshold: {cb.threshold:.2f}")

        # Alerts
        if report.active_alerts:
            print(f"\n🚨 ALERTS ({len(report.active_alerts)})")
            for alert in report.active_alerts[:5]:  # Show max 5
                severity_emoji = {
                    "info": "ℹ️",
                    "warning": "⚠️",
                    "critical": "🚨"
                }
                emoji = severity_emoji.get(alert.severity.value, "•")
                print(f"   {emoji} {alert.title}: {alert.message}")

        # Recommendations
        print(f"\n💡 RECOMMENDATIONS")
        for rec in report.recommendations:
            print(f"   • {rec}")

        # Actions
        print(f"\n🎯 SUGGESTED ACTIONS")
        if report.should_stop:
            print("   🛑 STOP DAEMON (critical risk)")
        elif report.should_pause:
            print("   ⏸️  PAUSE TRADING (high risk)")
        else:
            print("   ✅ CONTINUE MONITORING")

        print()

    def pause(self, reason: str = "Manual intervention"):
        """Pause trading (set control flag)."""
        is_running, pid = self.is_running()

        if not is_running:
            logger.error("Daemon not running")
            return

        # Write pause control file
        control = {
            "action": "pause",
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        }

        with open(CONTROL_FILE, 'w') as f:
            json.dump(control, f, indent=2)

        print(f"✅ Trading paused (PID {pid})")
        print(f"   Reason: {reason}")

    def resume(self):
        """Resume trading."""
        is_running, pid = self.is_running()

        if not is_running:
            logger.error("Daemon not running")
            return

        # Write resume control file
        control = {
            "action": "resume",
            "timestamp": datetime.now().isoformat()
        }

        with open(CONTROL_FILE, 'w') as f:
            json.dump(control, f, indent=2)

        # Reset circuit breakers
        self.breaker_manager.reset_all()

        print(f"✅ Trading resumed (PID {pid})")

    def stop(self):
        """Stop daemon process."""
        is_running, pid = self.is_running()

        if not is_running:
            logger.error("Daemon not running")
            return

        try:
            # Send SIGTERM for graceful shutdown
            os.kill(pid, signal.SIGTERM)
            print(f"✅ Stop signal sent to daemon (PID {pid})")
            print("   Waiting for graceful shutdown...")

            # Wait up to 10 seconds
            import time
            for _ in range(10):
                time.sleep(1)
                if not self.is_running()[0]:
                    print("   Daemon stopped successfully")
                    return

            # Force kill if still running
            print("   Forcing shutdown...")
            os.kill(pid, signal.SIGKILL)
            PID_FILE.unlink(missing_ok=True)
            print("   Daemon killed")

        except Exception as e:
            logger.error(f"Error stopping daemon: {e}")

    def start(self):
        """Start daemon process."""
        is_running, _ = self.is_running()

        if is_running:
            logger.error("Daemon already running")
            return

        # TODO: Implement daemon start
        print("⚠️  Start command not implemented yet")
        print("   Run daemon manually from jarvis_trading directory")

    def logs(self, lines: int = 50):
        """View recent logs."""
        log_file = Path(__file__).parent.parent / "logs" / "paper_trading.log"

        if not log_file.exists():
            logger.error("Log file not found")
            return

        # Read last N lines
        with open(log_file) as f:
            all_lines = f.readlines()
            recent = all_lines[-lines:]

        print(f"\n📋 Last {lines} log lines:\n")
        for line in recent:
            print(line.rstrip())

    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format."""
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


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Paper Trading Daemon Monitor (for JARVIS)"
    )

    subparsers = parser.add_subparsers(dest='command', help='Command')

    # Status command
    status_parser = subparsers.add_parser(
        'status', help='Check daemon status'
    )
    status_parser.add_argument(
        '--json', action='store_true', help='Output as JSON'
    )

    # Health command
    health_parser = subparsers.add_parser(
        'health', help='Full health report'
    )
    health_parser.add_argument(
        '--json', action='store_true', help='Output as JSON'
    )

    # Pause command
    pause_parser = subparsers.add_parser(
        'pause', help='Pause trading'
    )
    pause_parser.add_argument(
        '--reason', default='Manual intervention', help='Pause reason'
    )

    # Resume command
    subparsers.add_parser('resume', help='Resume trading')

    # Stop command
    subparsers.add_parser('stop', help='Stop daemon')

    # Start command
    subparsers.add_parser('start', help='Start daemon')

    # Logs command
    logs_parser = subparsers.add_parser(
        'logs', help='View recent logs'
    )
    logs_parser.add_argument(
        '--lines', type=int, default=50, help='Number of lines'
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    monitor = DaemonMonitor()

    if args.command == 'status':
        monitor.status(as_json=args.json)
    elif args.command == 'health':
        monitor.health(as_json=args.json)
    elif args.command == 'pause':
        monitor.pause(reason=args.reason)
    elif args.command == 'resume':
        monitor.resume()
    elif args.command == 'stop':
        monitor.stop()
    elif args.command == 'start':
        monitor.start()
    elif args.command == 'logs':
        monitor.logs(lines=args.lines)


if __name__ == '__main__':
    main()
