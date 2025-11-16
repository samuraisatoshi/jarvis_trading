"""
Bot Manager Module
Main orchestrator for the Telegram trading bot.
Handles initialization, registration of handlers, and bot lifecycle.
Dependency Injection pattern ensures loose coupling.
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)
from loguru import logger

from src.infrastructure.exchange.binance_rest_client import BinanceRESTClient
from src.infrastructure.telegram.formatters.message_formatter import MessageFormatter
from src.infrastructure.telegram.handlers.command_handlers import CommandHandlers
from src.infrastructure.telegram.handlers.callback_handlers import CallbackHandlers
from src.infrastructure.telegram.handlers.message_handlers import MessageHandlers


class BotManager:
    """
    Main bot orchestrator with dependency injection.
    Responsibilities:
    - Initialize bot with token
    - Set up handler pipeline
    - Manage bot lifecycle
    """

    def __init__(self, token: Optional[str] = None):
        """
        Initialize bot manager.

        Args:
            token: Bot token (uses TELEGRAM_BOT_TOKEN env var if not provided)
        """
        self.db_path = 'data/jarvis_trading.db'
        self.account_id = '868e0dd8-37f5-43ea-a956-7cc05e6bad66'

        # Load token
        self.token = token or self._load_token()

        # Initialize dependencies
        self.client = BinanceRESTClient(testnet=False)
        self.formatter = MessageFormatter()

        # Initialize handler instances with dependency injection
        self.command_handlers = CommandHandlers(
            db_path=self.db_path,
            account_id=self.account_id,
            client=self.client,
            formatter=self.formatter
        )

        self.callback_handlers = CallbackHandlers(
            db_path=self.db_path,
            account_id=self.account_id,
            client=self.client,
            formatter=self.formatter,
            command_handlers=self.command_handlers
        )

        self.message_handlers = MessageHandlers(
            db_path=self.db_path,
            account_id=self.account_id,
            client=self.client,
            formatter=self.formatter
        )

        logger.info("Bot Manager initialized successfully")

    def _load_token(self) -> str:
        """Load bot token from .env file."""
        load_dotenv()
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found in .env file")
        return token

    def _register_handlers(self, application: Application):
        """
        Register all handlers with the application.
        Handler registration order is important: specific before general.
        """

        # Command handlers (specific)
        application.add_handler(CommandHandler("start", self.command_handlers.start))
        application.add_handler(CommandHandler("help", self.command_handlers.help))
        application.add_handler(CommandHandler("status", self.command_handlers.status))
        application.add_handler(CommandHandler("portfolio", self.command_handlers.portfolio))
        application.add_handler(CommandHandler("p", self.command_handlers.portfolio))
        application.add_handler(CommandHandler("watchlist", self.command_handlers.watchlist))
        application.add_handler(CommandHandler("w", self.command_handlers.watchlist))
        application.add_handler(CommandHandler("signals", self.command_handlers.signals))
        application.add_handler(CommandHandler("s", self.command_handlers.signals))
        application.add_handler(CommandHandler("performance", self.command_handlers.performance))

        # Trading commands
        application.add_handler(CommandHandler("buy", self.message_handlers.buy_market))
        application.add_handler(CommandHandler("sell", self.message_handlers.sell_market))
        application.add_handler(CommandHandler("candles", self.message_handlers.candles))
        application.add_handler(CommandHandler("add", self.message_handlers.add_symbol))
        application.add_handler(CommandHandler("remove", self.message_handlers.remove_symbol))

        # Settings
        application.add_handler(CommandHandler("settings", self.command_handlers.handle_settings))

        # Button callbacks (specific)
        application.add_handler(CallbackQueryHandler(self.callback_handlers.button_handler))

        # Unknown command handler (general - must be last)
        application.add_handler(MessageHandler(
            filters.COMMAND,
            self.command_handlers.unknown_command
        ))

    def run(self):
        """Start the bot with polling."""
        application = Application.builder().token(self.token).build()

        # Register all handlers
        self._register_handlers(application)

        logger.info("Bot starting with polling mode...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

    def run_webhook(self, webhook_url: str, port: int = 8080):
        """
        Start the bot in webhook mode.

        Args:
            webhook_url: Full webhook URL
            port: Port to listen on
        """
        application = Application.builder().token(self.token).build()

        # Register all handlers
        self._register_handlers(application)

        logger.info(f"Bot starting with webhook mode (URL: {webhook_url}, port: {port})...")
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=self.token,
            webhook_url=webhook_url
        )


def create_bot(token: Optional[str] = None) -> BotManager:
    """
    Factory function to create bot instance.

    Args:
        token: Bot token (optional)

    Returns:
        BotManager instance
    """
    return BotManager(token=token)
