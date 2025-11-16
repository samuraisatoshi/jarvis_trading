#!/usr/bin/env python3
"""
Telegram Status Bot - Interactive Trading Monitor Wrapper

Thin wrapper for the refactored BotManager.
Provides interactive commands to monitor and control trading system.

Commands (when bot is running):
    /status - System status and health
    /portfolio or /p - Account balance and positions
    /watchlist or /w - Watchlist monitoring
    /signals or /s - Trading signals
    /performance - Performance metrics
    /settings - Bot configuration

Usage:
    python scripts/telegram_status_bot.py [--account-id ID] [--symbol SYMBOL] [--db PATH]
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
    parser = argparse.ArgumentParser(description="Telegram status bot")
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
        "--db",
        type=str,
        default=str(project_root / "data" / "jarvis_trading.db"),
        help="Database path",
    )
    return parser.parse_args()


def main():
    """Main entry point for status bot."""
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
        project_root / "logs" / f"telegram_status_{args.symbol}.log",
        rotation="1 day",
        retention="30 days",
        level="DEBUG",
    )

    # Get Telegram config
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not found in .env")
        sys.exit(1)

    if not chat_id:
        logger.warning("TELEGRAM_CHAT_ID not found in .env (bot will respond to any chat)")

    # Create and run bot
    logger.info(f"Starting Telegram Status Bot for {args.symbol}...")
    logger.info(f"Account ID: {args.account_id}")
    logger.info(f"Database: {args.db}")

    bot = BotManager(token=bot_token)
    bot.run()


if __name__ == "__main__":
    main()
