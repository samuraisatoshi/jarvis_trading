#!/usr/bin/env python3
"""
Multi-Asset Trading Daemon - Entry Point

Orchestrates automated trading across multiple assets and timeframes
using a modular, SOLID-compliant architecture.

This is the main entry point that wires together all dependencies
and starts the daemon.
"""

import sys
import argparse
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

from src.daemon import (
    DaemonManager,
    DaemonConfig,
    SignalProcessor,
    TradeExecutor,
    PortfolioService,
    MonitoringService,
    NotificationHandler
)
from src.infrastructure.exchange.binance_rest_client import BinanceRESTClient
from src.infrastructure.repositories import (
    BalanceRepositoryImpl,
    OrderRepositoryImpl,
    PositionRepositoryImpl
)
from src.infrastructure.notifications.telegram_helper import TradingTelegramNotifier
from scripts.watchlist_manager import WatchlistManager


class NullNotificationService:
    """
    Null object pattern for disabled notifications.

    Provides same interface as real notification service but does nothing.
    Used when Telegram or other notification services are unavailable.
    """

    def send_message(self, message: str) -> bool:
        """Send message (no-op)."""
        return True

    def notify_trade_executed(self, **kwargs) -> bool:
        """Notify trade execution (no-op)."""
        return True

    def notify_daemon_started(self, **kwargs) -> bool:
        """Notify daemon started (no-op)."""
        return True

    def notify_signals_found(self, signals) -> bool:
        """Notify signals found (no-op)."""
        return True


def create_daemon(
    account_id: str,
    db_path: str = 'data/jarvis_trading.db'
) -> DaemonManager:
    """
    Factory function to create daemon with all dependencies wired.

    This function demonstrates proper dependency injection setup,
    creating all infrastructure components and injecting them into
    domain services.

    Args:
        account_id: Trading account ID
        db_path: Path to SQLite database

    Returns:
        Configured DaemonManager instance ready to run
    """
    logger.info("Initializing daemon components...")

    # ============================================================
    # Infrastructure Layer
    # ============================================================

    # Exchange client for market data
    exchange_client = BinanceRESTClient(testnet=False)
    logger.info("Exchange client initialized (Binance mainnet)")

    # Watchlist manager for symbols and parameters
    watchlist = WatchlistManager()
    logger.info(f"Watchlist loaded: {len(watchlist.symbols)} symbols")

    # ============================================================
    # Repository Layer
    # ============================================================

    balance_repo = BalanceRepositoryImpl(db_path, account_id)
    order_repo = OrderRepositoryImpl(db_path, account_id)
    position_repo = PositionRepositoryImpl(db_path, account_id)
    logger.info("Repositories initialized (SQLite)")

    # ============================================================
    # Notification Service
    # ============================================================

    # Try to initialize Telegram (optional)
    try:
        telegram = TradingTelegramNotifier()
        notification_service = telegram
        logger.info("✅ Telegram notifications enabled")
    except Exception as e:
        logger.warning(f"⚠️  Telegram disabled: {e}")
        logger.info("Using null notification service (no alerts)")
        notification_service = NullNotificationService()

    # ============================================================
    # Domain Services Layer
    # ============================================================

    # Portfolio service
    portfolio_service = PortfolioService(
        balance_repo=balance_repo,
        position_repo=position_repo,
        exchange_client=exchange_client
    )
    logger.info("Portfolio service initialized")

    # Signal processor
    signal_processor = SignalProcessor(
        exchange_client=exchange_client,
        position_repo=position_repo,
        watchlist_manager=watchlist
    )
    logger.info("Signal processor initialized")

    # Trade executor
    trade_executor = TradeExecutor(
        balance_repo=balance_repo,
        order_repo=order_repo,
        position_repo=position_repo,
        notification_service=notification_service
    )
    logger.info("Trade executor initialized")

    # Notification handler
    notification_handler = NotificationHandler(
        notification_service=notification_service
    )
    logger.info("Notification handler initialized")

    # Monitoring service
    monitoring_service = MonitoringService(
        portfolio_service=portfolio_service,
        notification_handler=notification_handler
    )
    logger.info("Monitoring service initialized")

    # ============================================================
    # Daemon Configuration
    # ============================================================

    config = DaemonConfig(
        timeframes=['1h', '4h', '1d'],
        check_interval=3600,  # 1 hour
        position_sizes={'1h': 0.1, '4h': 0.2, '1d': 0.3},
        min_check_intervals={'1h': 300, '4h': 1200, '1d': 3600},
        min_trade_value=10.0,
        status_report_interval=6  # hours
    )
    logger.info(f"Configuration loaded: {config.timeframes}")

    # ============================================================
    # Daemon Manager (Orchestrator)
    # ============================================================

    daemon = DaemonManager(
        signal_processor=signal_processor,
        trade_executor=trade_executor,
        portfolio_service=portfolio_service,
        monitoring_service=monitoring_service,
        notification_handler=notification_handler,
        config=config
    )

    logger.info("✅ Daemon manager created successfully")
    logger.info(f"Account ID: {account_id}")
    logger.info(f"Database: {db_path}")
    logger.info(f"Watchlist: {watchlist.symbols}")

    return daemon


def configure_logging(log_level: str = "INFO"):
    """
    Configure logging for daemon.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    # Remove default logger
    logger.remove()

    # Console logger with colors
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level=log_level
    )

    # File logger with rotation
    logger.add(
        "logs/multi_asset_trading.log",
        rotation="100 MB",
        retention="30 days",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}"
    )

    logger.info("Logging configured")


def main():
    """
    Main entry point.

    Parses command line arguments, configures logging,
    creates daemon, and starts main loop.
    """
    parser = argparse.ArgumentParser(
        description="Multi-asset trading daemon with automated signal detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default account
  python scripts/multi_asset_trading_daemon.py

  # Run with specific account
  python scripts/multi_asset_trading_daemon.py --account-id YOUR_ACCOUNT_ID

  # Run with custom database path
  python scripts/multi_asset_trading_daemon.py --db-path /path/to/db.sqlite

  # Run with debug logging
  python scripts/multi_asset_trading_daemon.py --log-level DEBUG
        """
    )

    parser.add_argument(
        "--account-id",
        type=str,
        default="868e0dd8-37f5-43ea-a956-7cc05e6bad66",
        help="Trading account ID (default: paper trading account)"
    )

    parser.add_argument(
        "--db-path",
        type=str,
        default="data/jarvis_trading.db",
        help="Path to SQLite database (default: data/jarvis_trading.db)"
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)"
    )

    args = parser.parse_args()

    # Configure logging
    configure_logging(args.log_level)

    logger.info("=" * 60)
    logger.info("Multi-Asset Trading Daemon")
    logger.info("=" * 60)

    # Create daemon with dependency injection
    try:
        daemon = create_daemon(
            account_id=args.account_id,
            db_path=args.db_path
        )
    except Exception as e:
        logger.error(f"Failed to create daemon: {e}")
        logger.exception("Traceback:")
        sys.exit(1)

    # Run daemon
    try:
        daemon.run()
    except KeyboardInterrupt:
        logger.info("\nShutdown signal received")
        daemon.stop()
    except Exception as e:
        logger.error(f"Daemon crashed: {e}")
        logger.exception("Traceback:")
        daemon.stop()
        sys.exit(1)

    logger.info("Daemon shut down gracefully")


if __name__ == "__main__":
    main()
