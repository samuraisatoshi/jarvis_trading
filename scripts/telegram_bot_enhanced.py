#!/usr/bin/env python3
"""
Enhanced Telegram Bot Wrapper

Thin wrapper for the refactored BotManager with enhanced UI features.
All logic is in src/infrastructure/telegram/.

Usage:
    python scripts/telegram_bot_enhanced.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from loguru import logger
from src.infrastructure.telegram import BotManager


def main():
    """Main entry point for enhanced bot."""
    # Load environment
    load_dotenv()

    # Configure logging
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO",
    )
    logger.add(
        project_root / "logs" / "telegram_bot_enhanced.log",
        rotation="1 day",
        retention="30 days",
        level="DEBUG",
    )

    # Get bot token
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not found in .env file")
        sys.exit(1)

    # Create and run bot
    logger.info("Starting Enhanced Telegram Bot...")
    bot = BotManager(token=token)
    bot.run()


if __name__ == "__main__":
    main()
