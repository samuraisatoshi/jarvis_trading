"""
Message Handlers Module
Handles trading commands: /buy, /sell, /candles, /add, /remove
Follows Single Responsibility: trading operations only.
"""

import asyncio
import sqlite3
import os
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction
from datetime import datetime

from src.infrastructure.exchange.binance_rest_client import BinanceRESTClient
from src.utils.chart_generator import ChartGenerator
from src.infrastructure.telegram.formatters.message_formatter import MessageFormatter


class MessageHandlers:
    """Handles trading messages (buy, sell, add, remove, candles)."""

    def __init__(
        self,
        db_path: str,
        account_id: str,
        client: BinanceRESTClient,
        formatter: MessageFormatter
    ):
        """Initialize with dependencies."""
        self.db_path = db_path
        self.account_id = account_id
        self.client = client
        self.formatter = formatter

    async def buy_market(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /buy command - Execute market buy."""
        await update.message.chat.send_action(ChatAction.TYPING)

        # Validate arguments
        if len(context.args) != 2:
            await update.message.reply_text(
                self.formatter.format_error_invalid_command(),
                parse_mode=ParseMode.MARKDOWN
            )
            return

        symbol = context.args[0].upper()
        if not symbol.endswith('USDT'):
            symbol += 'USDT'

        try:
            amount_usdt = float(context.args[1])
        except ValueError:
            await update.message.reply_text(
                self.formatter.format_error_invalid_amount(),
                parse_mode=ParseMode.MARKDOWN
            )
            return

        # Show confirmation with button
        keyboard = [[
            InlineKeyboardButton("⏳ Executando ordem...", callback_data="processing")
        ]]

        confirm_msg = await update.message.reply_text(
            self.formatter.format_buy_confirmation(symbol, amount_usdt),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

        # Simulate execution
        await asyncio.sleep(1.5)

        # Update button with result
        keyboard = [[
            InlineKeyboardButton("✅ Ordem executada com sucesso!", callback_data="done")
        ]]

        result_text = self.formatter.format_buy_result(
            symbol,
            0.001234,  # Simulated quantity
            95000.00,  # Simulated price
            amount_usdt
        )

        await confirm_msg.edit_text(
            result_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    async def sell_market(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /sell command - Execute market sell."""
        await update.message.chat.send_action(ChatAction.TYPING)

        if len(context.args) != 2:
            await update.message.reply_text(
                self.formatter.format_error_invalid_sell_command(),
                parse_mode=ParseMode.MARKDOWN
            )
            return

        symbol = context.args[0].upper()
        if not symbol.endswith('USDT'):
            symbol += 'USDT'

        try:
            percent = float(context.args[1])
            if not (0 <= percent <= 100):
                await update.message.reply_text(
                    "❌ Percentual deve estar entre 0 e 100",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
        except ValueError:
            await update.message.reply_text(
                self.formatter.format_error_invalid_amount(),
                parse_mode=ParseMode.MARKDOWN
            )
            return

        await update.message.reply_text(
            self.formatter.format_sell_instruction(),
            parse_mode=ParseMode.MARKDOWN
        )

    async def candles(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /candles command - Generate candlestick chart."""
        await update.message.chat.send_action(ChatAction.UPLOAD_PHOTO)

        # Validate arguments
        if len(context.args) < 1:
            await update.message.reply_text(
                self.formatter.format_error_candles_command(),
                parse_mode=ParseMode.MARKDOWN
            )
            return

        symbol = context.args[0].upper()
        if not symbol.endswith('USDT'):
            symbol += 'USDT'

        timeframe = '1h'
        if len(context.args) >= 2:
            tf = context.args[1].lower()
            if tf in ['1h', '4h', '1d']:
                timeframe = tf
            else:
                await update.message.reply_text(
                    self.formatter.format_error_invalid_timeframe(tf),
                    parse_mode=ParseMode.MARKDOWN
                )
                return

        # Show processing message
        processing_msg = await update.message.reply_text(
            self.formatter.format_candles_processing(symbol, timeframe),
            parse_mode=ParseMode.MARKDOWN
        )

        try:
            await update.message.chat.send_action(ChatAction.UPLOAD_PHOTO)

            # Generate chart
            chart_generator = ChartGenerator(self.db_path)
            chart_path = chart_generator.generate_chart(symbol, timeframe)

            # Send image
            with open(chart_path, 'rb') as photo:
                await update.message.reply_photo(
                    photo=photo,
                    caption=self.formatter.format_candles_caption(symbol, timeframe),
                    parse_mode=ParseMode.MARKDOWN
                )

            # Delete processing message
            await processing_msg.delete()

            # Clean up temporary file
            if os.path.exists(chart_path):
                os.remove(chart_path)

        except Exception as e:
            await processing_msg.edit_text(
                self.formatter.format_error_generic(f"Erro ao gerar gráfico: {e}"),
                parse_mode=ParseMode.MARKDOWN
            )

    async def add_symbol(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /add command - Add symbol to watchlist."""
        await update.message.chat.send_action(ChatAction.TYPING)

        if not context.args:
            await update.message.reply_text(
                self.formatter.format_error_add_command(),
                parse_mode=ParseMode.MARKDOWN
            )
            return

        symbol = context.args[0].upper()
        if not symbol.endswith('USDT'):
            symbol += 'USDT'

        # Show processing message
        processing_msg = await update.message.reply_text(
            f"➕ Adicionando {symbol}...",
            parse_mode=ParseMode.MARKDOWN
        )

        try:
            # Verify symbol exists on Binance
            ticker = self.client.get_symbol_ticker(symbol)
            price = float(ticker['price'])

            # Add to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR IGNORE INTO watchlist (account_id, symbol)
                VALUES (?, ?)
            """, (self.account_id, symbol))

            conn.commit()
            conn.close()

            await processing_msg.edit_text(
                self.formatter.format_success_symbol_added(symbol, price),
                parse_mode=ParseMode.MARKDOWN
            )

        except Exception as e:
            await processing_msg.edit_text(
                self.formatter.format_error_generic(f"Erro ao adicionar {symbol}: {e}"),
                parse_mode=ParseMode.MARKDOWN
            )

    async def remove_symbol(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /remove command - Remove symbol from watchlist."""
        await update.message.chat.send_action(ChatAction.TYPING)

        if not context.args:
            await update.message.reply_text(
                self.formatter.format_error_remove_command(),
                parse_mode=ParseMode.MARKDOWN
            )
            return

        symbol = context.args[0].upper()
        if not symbol.endswith('USDT'):
            symbol += 'USDT'

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM watchlist
                WHERE account_id = ? AND symbol = ?
            """, (self.account_id, symbol))

            if cursor.rowcount > 0:
                await update.message.reply_text(
                    self.formatter.format_success_symbol_removed(symbol),
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await update.message.reply_text(
                    self.formatter.format_warning_symbol_not_in_watchlist(symbol),
                    parse_mode=ParseMode.MARKDOWN
                )

            conn.commit()
            conn.close()

        except Exception as e:
            await update.message.reply_text(
                self.formatter.format_error_generic(f"Erro ao remover {symbol}: {e}"),
                parse_mode=ParseMode.MARKDOWN
            )
