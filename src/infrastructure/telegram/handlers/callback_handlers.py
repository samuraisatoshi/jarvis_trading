"""
Callback Handlers Module
Handles inline button callbacks (when users click buttons).
Follows Single Responsibility: only button callbacks, delegates to command handlers.
"""

import asyncio
import sqlite3
import os
from typing import Callable, Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction

from src.infrastructure.exchange.binance_rest_client import BinanceRESTClient
from src.utils.chart_generator import ChartGenerator
from src.infrastructure.telegram.formatters.message_formatter import MessageFormatter
from .command_handlers import CommandHandlers


class CallbackHandlers:
    """Handles button/inline keyboard callbacks."""

    def __init__(
        self,
        db_path: str,
        account_id: str,
        client: BinanceRESTClient,
        formatter: MessageFormatter,
        command_handlers: CommandHandlers
    ):
        """Initialize with dependencies."""
        self.db_path = db_path
        self.account_id = account_id
        self.client = client
        self.formatter = formatter
        self.command_handlers = command_handlers

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Main button handler - dispatcher for all button callbacks."""
        query = update.callback_query
        await query.answer()

        # Map callbacks to handler methods
        callback_map: Dict[str, Callable] = {
            'portfolio': self._handle_portfolio,
            'signals': self._handle_signals,
            'watchlist': self._handle_watchlist,
            'history': self._handle_history,
            'performance': self._handle_performance,
            'settings': self._handle_settings,
            'buy_menu': self._handle_buy_menu,
            'sell_menu': self._handle_sell_menu,
        }

        handler = callback_map.get(query.data)
        if handler:
            await handler(update, context)

    async def _handle_portfolio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle portfolio button callback."""
        # Reuse command handler by creating fake message update
        update.message = update.callback_query.message
        await self.command_handlers.portfolio(update, context)

    async def _handle_signals(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle signals button callback."""
        update.message = update.callback_query.message
        await self.command_handlers.signals(update, context)

    async def _handle_watchlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle watchlist button callback."""
        update.message = update.callback_query.message
        await self.command_handlers.watchlist(update, context)

    async def _handle_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle history button callback."""
        update.message = update.callback_query.message
        await self.command_handlers.history(update, context)

    async def _handle_performance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle performance button callback."""
        update.message = update.callback_query.message
        await self.command_handlers.performance(update, context)

    async def _handle_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle settings button callback."""
        update.message = update.callback_query.message
        await self.command_handlers.handle_settings(update, context)

    async def _handle_buy_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle buy menu button - show instructions."""
        query = update.callback_query
        await query.edit_message_text(
            "💰 *Para comprar:*\n\n"
            "Use o comando:\n"
            "`/buy SYMBOL AMOUNT`\n\n"
            "Exemplo:\n"
            "`/buy BTCUSDT 100`\n\n"
            "(AMOUNT em USDT)",
            parse_mode=ParseMode.MARKDOWN
        )

    async def _handle_sell_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle sell menu button - show instructions."""
        query = update.callback_query
        await query.edit_message_text(
            "💵 *Para vender:*\n\n"
            "Use o comando:\n"
            "`/sell SYMBOL PERCENT`\n\n"
            "Exemplo:\n"
            "`/sell BTCUSDT 50`\n\n"
            "(PERCENT = % da posição)",
            parse_mode=ParseMode.MARKDOWN
        )
