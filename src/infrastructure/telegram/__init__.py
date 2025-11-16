"""
Telegram Infrastructure Module
Provides telegram bot management with clean architecture and dependency injection.

Components:
- BotManager: Main orchestrator
- CommandHandlers: Slash command handlers
- CallbackHandlers: Button callback handlers
- MessageHandlers: Trading message handlers
- MessageFormatter: Message formatting and templates

Usage:
    from src.infrastructure.telegram import BotManager

    bot = BotManager()
    bot.run()
"""

from src.infrastructure.telegram.bot_manager import BotManager, create_bot
from src.infrastructure.telegram.formatters.message_formatter import MessageFormatter
from src.infrastructure.telegram.handlers.command_handlers import CommandHandlers
from src.infrastructure.telegram.handlers.callback_handlers import CallbackHandlers
from src.infrastructure.telegram.handlers.message_handlers import MessageHandlers

__all__ = [
    'BotManager',
    'create_bot',
    'MessageFormatter',
    'CommandHandlers',
    'CallbackHandlers',
    'MessageHandlers',
]
