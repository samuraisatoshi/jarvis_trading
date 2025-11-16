"""
Command Handlers Module
Handles /start, /help, /status, /portfolio, /signals, and other command handlers.
Follows Single Responsibility: each method handles one command.
"""

import asyncio
import sqlite3
from datetime import datetime, timezone
from typing import List, Tuple, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction

from src.infrastructure.exchange.binance_rest_client import BinanceRESTClient
from src.utils.chart_generator import ChartGenerator
from src.infrastructure.telegram.formatters.message_formatter import MessageFormatter


class CommandHandlers:
    """Handles slash commands (/start, /help, /status, etc)."""

    def __init__(
        self,
        db_path: str,
        account_id: str,
        client: BinanceRESTClient,
        formatter: MessageFormatter
    ):
        """Initialize with dependencies (Dependency Injection)."""
        self.db_path = db_path
        self.account_id = account_id
        self.client = client
        self.formatter = formatter
        self.valid_commands = {
            'start', 'help', 'status', 'portfolio', 'p',
            'watchlist', 'w', 'signals', 's', 'add', 'remove',
            'buy', 'sell', 'candles', 'history', 'orders',
            'balance', 'performance', 'settings', 'update',
            'pause', 'resume'
        }

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /start command - Main menu."""
        await update.message.chat.send_action(ChatAction.TYPING)

        keyboard = [
            [
                InlineKeyboardButton("📊 Portfolio", callback_data='portfolio'),
                InlineKeyboardButton("📈 Sinais", callback_data='signals')
            ],
            [
                InlineKeyboardButton("📋 Watchlist", callback_data='watchlist'),
                InlineKeyboardButton("💹 Performance", callback_data='performance')
            ],
            [
                InlineKeyboardButton("📜 Histórico", callback_data='history'),
                InlineKeyboardButton("⚙️ Configurações", callback_data='settings')
            ],
            [
                InlineKeyboardButton("💰 Comprar", callback_data='buy_menu'),
                InlineKeyboardButton("💵 Vender", callback_data='sell_menu')
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        welcome_text = self.formatter.format_welcome()

        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /help command."""
        await update.message.chat.send_action(ChatAction.TYPING)
        help_text = self.formatter.format_help()
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /status command."""
        await update.message.chat.send_action(ChatAction.TYPING)

        processing_msg = await update.message.reply_text(
            self.formatter.format_processing("Verificando status do sistema..."),
            parse_mode=ParseMode.MARKDOWN
        )

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Fetch balance
            cursor.execute("""
                SELECT currency, available_amount
                FROM balances
                WHERE account_id = ? AND available_amount > 0
                ORDER BY currency
            """, (self.account_id,))

            balances = cursor.fetchall()

            # Fetch last order
            cursor.execute("""
                SELECT symbol, side, quantity, price, created_at
                FROM orders
                WHERE account_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (self.account_id,))

            last_order = cursor.fetchone()

            # Count orders today
            today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
            cursor.execute("""
                SELECT COUNT(*) FROM orders
                WHERE account_id = ? AND created_at > ?
            """, (self.account_id, today.isoformat()))

            orders_today = cursor.fetchone()[0]
            conn.close()

            status_msg = self.formatter.format_status(balances, last_order, orders_today)

            await processing_msg.delete()
            await update.message.reply_text(
                status_msg,
                parse_mode=ParseMode.MARKDOWN
            )

        except Exception as e:
            await processing_msg.edit_text(
                self.formatter.format_error_generic(str(e)),
                parse_mode=ParseMode.MARKDOWN
            )

    async def portfolio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /portfolio and /p command."""
        await update.message.chat.send_action(ChatAction.TYPING)

        processing_msg = await update.message.reply_text(
            self.formatter.format_processing("Calculando seu portfolio..."),
            parse_mode=ParseMode.MARKDOWN
        )

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT currency, available_amount
                FROM balances
                WHERE account_id = ? AND available_amount > 0.0001
                ORDER BY currency
            """, (self.account_id,))

            balances = cursor.fetchall()
            conn.close()

            if not balances:
                await processing_msg.edit_text(
                    self.formatter.format_portfolio([], 0, {}),
                    parse_mode=ParseMode.MARKDOWN
                )
                return

            # Calculate values
            total_value = 0
            price_data = {}

            for currency, amount in balances:
                if currency == 'USDT':
                    total_value += amount
                else:
                    symbol = f"{currency}USDT"
                    try:
                        ticker = self.client.get_symbol_ticker(symbol)
                        price = float(ticker['price'])
                        price_data[symbol] = price
                        total_value += amount * price
                    except:
                        price_data[symbol] = 0

            portfolio_text = self.formatter.format_portfolio(balances, total_value, price_data)

            await processing_msg.edit_text(
                portfolio_text,
                parse_mode=ParseMode.MARKDOWN
            )

        except Exception as e:
            await processing_msg.edit_text(
                self.formatter.format_error_generic(f"Erro ao calcular portfolio: {e}"),
                parse_mode=ParseMode.MARKDOWN
            )

    async def signals(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /signals and /s command."""
        await update.message.chat.send_action(ChatAction.TYPING)

        progress_msg = await update.message.reply_text(
            "🔍 Analisando sinais...\n⬜⬜⬜⬜⬜ 0%",
            parse_mode=ParseMode.MARKDOWN
        )

        try:
            await asyncio.sleep(0.5)
            await progress_msg.edit_text(
                "🔍 Analisando sinais...\n⬛⬜⬜⬜⬜ 20%"
            )

            await asyncio.sleep(0.5)
            await progress_msg.edit_text(
                "🔍 Analisando sinais...\n⬛⬛⬛⬜⬜ 60%"
            )

            await asyncio.sleep(0.5)
            await progress_msg.edit_text(
                "🔍 Analisando sinais...\n⬛⬛⬛⬛⬜ 80%"
            )

            signals_text = self.formatter.format_signals()

            await progress_msg.edit_text(
                signals_text,
                parse_mode=ParseMode.MARKDOWN
            )

        except Exception as e:
            await progress_msg.edit_text(
                self.formatter.format_error_generic(f"Erro ao analisar sinais: {e}"),
                parse_mode=ParseMode.MARKDOWN
            )

    async def watchlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /watchlist and /w command."""
        await update.message.chat.send_action(ChatAction.TYPING)

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT symbol FROM watchlist
                WHERE account_id = ?
                ORDER BY symbol
            """, (self.account_id,))

            symbols = cursor.fetchall()
            conn.close()

            if not symbols:
                await update.message.reply_text(
                    self.formatter.format_watchlist([]),
                    parse_mode=ParseMode.MARKDOWN
                )
                return

            # Get prices
            symbols_with_prices = []
            for (symbol,) in symbols:
                try:
                    ticker = self.client.get_symbol_ticker(symbol)
                    price = float(ticker['price'])
                    symbols_with_prices.append((symbol, price))
                except:
                    symbols_with_prices.append((symbol, None))

            watchlist_text = self.formatter.format_watchlist(symbols_with_prices)

            await update.message.reply_text(
                watchlist_text,
                parse_mode=ParseMode.MARKDOWN
            )

        except Exception as e:
            await update.message.reply_text(
                self.formatter.format_error_generic(f"Erro ao obter watchlist: {e}"),
                parse_mode=ParseMode.MARKDOWN
            )

    async def history(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /history command."""
        await update.message.chat.send_action(ChatAction.TYPING)

        limit = 10
        if context.args and context.args[0].isdigit():
            limit = int(context.args[0])

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    transaction_type,
                    amount,
                    currency,
                    description,
                    created_at
                FROM transactions
                WHERE account_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (self.account_id, limit))

            transactions = cursor.fetchall()
            conn.close()

            history_text = self.formatter.format_history(transactions)

            await update.message.reply_text(
                history_text,
                parse_mode=ParseMode.MARKDOWN
            )

        except Exception as e:
            await update.message.reply_text(
                self.formatter.format_error_generic(f"Erro ao obter histórico: {e}"),
                parse_mode=ParseMode.MARKDOWN
            )

    async def performance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /performance command."""
        await update.message.chat.send_action(ChatAction.TYPING)

        processing_msg = await update.message.reply_text(
            self.formatter.format_processing("Analisando performance..."),
            parse_mode=ParseMode.MARKDOWN
        )

        await asyncio.sleep(1)

        performance_text = self.formatter.format_performance()

        await processing_msg.edit_text(
            performance_text,
            parse_mode=ParseMode.MARKDOWN
        )

    async def handle_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /settings command."""
        await update.message.chat.send_action(ChatAction.TYPING)

        settings_text = self.formatter.format_settings()

        await update.message.reply_text(
            settings_text,
            parse_mode=ParseMode.MARKDOWN
        )

    async def unknown_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for unknown commands."""
        command = update.message.text.split()[0]

        # Find similar commands
        suggestions = []
        cmd_name = command[1:].lower()  # Remove / and lowercase

        for valid_cmd in self.valid_commands:
            if cmd_name in valid_cmd or valid_cmd.startswith(cmd_name[:2]):
                suggestions.append(f"/{valid_cmd}")

        error_msg = self.formatter.format_error_unknown_command(command, suggestions)

        await update.message.reply_text(error_msg, parse_mode=ParseMode.MARKDOWN)
