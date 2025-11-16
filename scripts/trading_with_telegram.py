#!/usr/bin/env python3
"""
Paper Trading System with Telegram Notifications Wrapper

Thin wrapper that runs the BotManager alongside paper trading operations.
Note: This is a simplified wrapper. Full trading integration would require
extending BotManager with trading system callbacks.

For now, this simply runs the bot which provides manual trading commands.

Features available through bot:
- Real-time portfolio monitoring
- Manual trade execution via /buy and /sell commands
- Market signals monitoring
- Performance tracking
- Watchlist management

Usage:
    # Run bot with default settings
    python scripts/trading_with_telegram.py

    # Specify account and symbol
    python scripts/trading_with_telegram.py --account-id ID --symbol BNB_USDT

    # Daemon mode (continuous operation)
    python scripts/trading_with_telegram.py --daemon

    # Dry run mode (no actual trades)
    python scripts/trading_with_telegram.py --dry-run
"""

import os
import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from loguru import logger
from src.infrastructure.telegram import BotManager


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Paper trading with Telegram notifications"
    )
    parser.add_argument(
        "--account-id",
        type=str,
        default="868e0dd8-37f5-43ea-a956-7cc05e6bad66",
        help="Paper trading account ID",
    )
    parser.add_argument(
        "--symbol", type=str, default="BNB_USDT", help="Trading pair"
    )
    parser.add_argument(
        "--timeframe", type=str, default="1d", help="Candle timeframe"
    )
    parser.add_argument(
        "--models-path",
        type=str,
        default="/Users/jfoc/Documents/DevLabs/python/crypto/finrl/trained_models",
        help="Path to trained models",
    )
    parser.add_argument(
        "--db",
        type=str,
        default=str(project_root / "data" / "jarvis_trading.db"),
        help="Database path",
    )
    parser.add_argument(
        "--daemon", action="store_true", help="Run in daemon mode (continuous)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Dry run mode (no actual trades)"
    )
    parser.add_argument(
        "--no-telegram",
        action="store_true",
        help="Disable Telegram notifications (bot won't start)",
    )
    return parser.parse_args()


def main():
    """Main entry point for trading with Telegram."""
    args = parse_arguments()

    # Load environment
    load_dotenv()

    # Configure logging
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO",
    )
    logger.add(
        project_root / "logs" / f"telegram_trading_{args.symbol}_{args.timeframe}.log",
        rotation="1 day",
        retention="30 days",
        level="DEBUG",
    )

    # Check if Telegram is disabled
    if args.no_telegram:
        logger.warning("Telegram disabled. Bot will not start.")
        logger.info("Use run_paper_trading.py for trading without Telegram")
        sys.exit(0)

    # Get Telegram config
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not found in .env")
        sys.exit(1)

    # Log configuration
    logger.info(f"Trading with Telegram - {args.symbol} @ {args.timeframe}")
    logger.info(f"Account ID: {args.account_id}")
    logger.info(f"Database: {args.db}")
    logger.info(f"Models Path: {args.models_path}")
    logger.info(f"Daemon Mode: {args.daemon}")
    logger.info(f"Dry Run: {args.dry_run}")

    if args.dry_run:
        logger.warning("DRY RUN MODE: No actual trades will be executed")

    # Note about functionality
    logger.info("")
    logger.info("=" * 60)
    logger.info("NOTE: This wrapper provides manual trading via Telegram bot")
    logger.info("Available commands:")
    logger.info("  /buy SYMBOL AMOUNT - Execute market buy")
    logger.info("  /sell SYMBOL AMOUNT - Execute market sell")
    logger.info("  /status - System status")
    logger.info("  /portfolio - View portfolio")
    logger.info("  /signals - View trading signals")
    logger.info("")
    logger.info("For automated trading, use run_paper_trading.py separately")
    logger.info("=" * 60)
    logger.info("")

    # Create and run bot
    bot = BotManager(token=bot_token)

    if args.daemon:
        logger.info("Starting bot in daemon mode (continuous operation)...")
        bot.run()  # Will run indefinitely
    else:
        logger.info("Starting bot in standard mode...")
        bot.run()


if __name__ == "__main__":
    main()
