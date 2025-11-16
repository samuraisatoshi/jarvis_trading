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
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.application.services.monitoring_application_service import (  # noqa: E402
    MonitoringApplicationService
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
BASE_DIR = Path(__file__).parent.parent
PID_FILE = BASE_DIR / "paper_trading.pid"
CONTROL_FILE = BASE_DIR / "paper_trading.control"
DB_PATH = BASE_DIR / "paper_trading.db"
LOG_FILE = BASE_DIR / "logs" / "paper_trading.log"


def print_status(service: MonitoringApplicationService, as_json: bool = False):
    """Print daemon status."""
    status = service.get_daemon_status()

    if as_json:
        data = {
            "running": status.running,
            "pid": status.pid,
            "uptime_seconds": status.uptime_seconds,
            "uptime_human": service.format_duration(status.uptime_seconds)
        }
        print(json.dumps(data, indent=2))
    else:
        emoji = "🟢" if status.running else "🔴"
        text = "RUNNING" if status.running else "STOPPED"
        print(f"\n{emoji} Paper Trading Daemon: {text}")
        if status.running:
            print(f"   PID: {status.pid}")
            print(f"   Uptime: {service.format_duration(status.uptime_seconds)}")
        print()


def print_health(service: MonitoringApplicationService, as_json: bool = False):
    """Print health report."""
    report = service.get_health_report()

    if as_json:
        print(json.dumps(report.to_dict(), indent=2))
        return

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
    print("\n📊 DAEMON")
    daemon_status = "RUNNING" if report.daemon_running else "STOPPED"
    print(f"   Status: {daemon_status}")
    if report.daemon_pid:
        print(f"   PID: {report.daemon_pid}")
        print(f"   Uptime: {service.format_duration(report.daemon_uptime_seconds)}")

    # Metrics
    m = report.metrics
    print("\n💰 PERFORMANCE")
    print(f"   Portfolio: ${m.portfolio_value:,.2f}")
    print(f"   Daily P&L: ${m.daily_pnl:+,.2f} ({m.daily_pnl_pct:+.2%})")
    print(f"   Drawdown: {m.drawdown:.2%}")
    print(f"   Win Rate: {m.win_rate:.1%}")
    print(f"   Sharpe: {m.sharpe_ratio:.2f}")
    print(f"   Active: {m.active_positions} positions")
    print(f"   Consecutive Losses: {m.consecutive_losses}")

    # Circuit breakers
    active_breakers = [cb for cb in report.circuit_breakers if cb.state.value == "open"]
    if active_breakers:
        print(f"\n⚠️  CIRCUIT BREAKERS ({len(active_breakers)} ACTIVE)")
        for cb in active_breakers:
            print(f"   • {cb.name}: {cb.description}")
            print(f"     Current: {cb.current_value:.2f} | Threshold: {cb.threshold:.2f}")

    # Alerts
    if report.active_alerts:
        print(f"\n🚨 ALERTS ({len(report.active_alerts)})")
        for alert in report.active_alerts[:5]:
            severity_emoji = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}
            emoji = severity_emoji.get(alert.severity.value, "•")
            print(f"   {emoji} {alert.title}: {alert.message}")

    # Recommendations
    print("\n💡 RECOMMENDATIONS")
    for rec in report.recommendations:
        print(f"   • {rec}")

    # Actions
    print("\n🎯 SUGGESTED ACTIONS")
    if report.should_stop:
        print("   🛑 STOP DAEMON (critical risk)")
    elif report.should_pause:
        print("   ⏸️  PAUSE TRADING (high risk)")
    else:
        print("   ✅ CONTINUE MONITORING")
    print()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Paper Trading Daemon Monitor (for JARVIS)"
    )
    subparsers = parser.add_subparsers(dest='command', help='Command')

    # Status command
    status_parser = subparsers.add_parser('status', help='Check daemon status')
    status_parser.add_argument('--json', action='store_true', help='Output as JSON')

    # Health command
    health_parser = subparsers.add_parser('health', help='Full health report')
    health_parser.add_argument('--json', action='store_true', help='Output as JSON')

    # Pause command
    pause_parser = subparsers.add_parser('pause', help='Pause trading')
    pause_parser.add_argument('--reason', default='Manual intervention', help='Pause reason')

    # Resume command
    subparsers.add_parser('resume', help='Resume trading')

    # Stop command
    subparsers.add_parser('stop', help='Stop daemon')

    # Start command
    subparsers.add_parser('start', help='Start daemon')

    # Logs command
    logs_parser = subparsers.add_parser('logs', help='View recent logs')
    logs_parser.add_argument('--lines', type=int, default=50, help='Number of lines')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Initialize service
    service = MonitoringApplicationService(
        db_path=DB_PATH,
        pid_file=PID_FILE,
        control_file=CONTROL_FILE,
        log_file=LOG_FILE
    )

    # Execute command
    if args.command == 'status':
        print_status(service, as_json=args.json)
    elif args.command == 'health':
        print_health(service, as_json=args.json)
    elif args.command == 'pause':
        if service.pause_trading(reason=args.reason):
            print(f"✅ Trading paused: {args.reason}")
        else:
            print("❌ Failed to pause trading")
            sys.exit(1)
    elif args.command == 'resume':
        if service.resume_trading():
            print("✅ Trading resumed")
        else:
            print("❌ Failed to resume trading")
            sys.exit(1)
    elif args.command == 'stop':
        if service.stop_daemon():
            print("✅ Daemon stopped")
        else:
            print("❌ Failed to stop daemon")
            sys.exit(1)
    elif args.command == 'start':
        if not service.start_daemon():
            print("⚠️  Start command not implemented")
            print("   Run daemon manually from jarvis_trading directory")
            sys.exit(1)
    elif args.command == 'logs':
        lines = service.read_logs(lines=args.lines)
        if lines:
            print(f"\n📋 Last {args.lines} log lines:\n")
            for line in lines:
                print(line.rstrip())
        else:
            print("❌ No logs found")
            sys.exit(1)


if __name__ == '__main__':
    main()
