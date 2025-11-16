#!/usr/bin/env python3
"""
Bot Telegram Aprimorado para Trading Multi-Ativo.

Interface melhorada com botões inline e menus interativos.
"""

import os
import sys
import sqlite3
import asyncio
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from decimal import Decimal
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from loguru import logger

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButton,
    MenuButtonCommands,
    BotCommand
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)

from src.infrastructure.exchange.binance_rest_client import BinanceRESTClient
from scripts.watchlist_manager import WatchlistManager


class EnhancedTradingBot:
    """Bot Telegram com interface aprimorada."""

    def __init__(self):
        """Inicializa o bot."""
        load_dotenv()

        # Configurações
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.allowed_chat_id = int(os.getenv('TELEGRAM_CHAT_ID', 0))

        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN não configurado")

        # Account e DB
        self.account_id = '868e0dd8-37f5-43ea-a956-7cc05e6bad66'
        self.db_path = 'data/jarvis_trading.db'

        # Clientes
        self.client = BinanceRESTClient(testnet=False)
        self.watchlist = WatchlistManager()

        # Estado do daemon
        self.daemon_active = True

        logger.info(f"Bot inicializado - Chat ID: {self.allowed_chat_id}")


    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start - Menu principal com botões."""
        if update.effective_chat.id != self.allowed_chat_id:
            return

        keyboard = [
            [
                InlineKeyboardButton("📊 Status", callback_data='status'),
                InlineKeyboardButton("💼 Portfólio", callback_data='portfolio')
            ],
            [
                InlineKeyboardButton("📋 Watchlist", callback_data='watchlist'),
                InlineKeyboardButton("📡 Sinais", callback_data='signals')
            ],
            [
                InlineKeyboardButton("📈 Performance", callback_data='performance'),
                InlineKeyboardButton("📜 Histórico", callback_data='history')
            ],
            [
                InlineKeyboardButton("⚙️ Configurações", callback_data='settings'),
                InlineKeyboardButton("🔄 Atualizar", callback_data='refresh')
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        welcome_msg = (
            "*🤖 Bot de Trading Multi-Ativo*\n\n"
            "Bem-vindo! Use os botões abaixo para navegar:\n\n"
            f"💰 Capital: $5,000 USDT\n"
            f"📊 Ativos: {len(self.watchlist.symbols)}\n"
            f"🟢 Status: {'Ativo' if self.daemon_active else 'Pausado'}\n\n"
            "_Escolha uma opção:_"
        )

        await update.message.reply_text(
            welcome_msg,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processa cliques nos botões."""
        query = update.callback_query
        await query.answer()

        # Mapeamento de callbacks
        handlers = {
            'status': self.handle_status,
            'portfolio': self.handle_portfolio,
            'watchlist': self.handle_watchlist,
            'signals': self.handle_signals,
            'performance': self.handle_performance,
            'history': self.handle_history,
            'settings': self.handle_settings,
            'refresh': self.handle_refresh,
            'pause_trading': self.handle_pause,
            'resume_trading': self.handle_resume,
            'back_main': self.back_to_main
        }

        # Processar callbacks de watchlist
        if query.data.startswith('add_'):
            await self.handle_add_symbol(query, query.data.split('_')[1])
            return
        elif query.data.startswith('remove_'):
            await self.handle_remove_symbol(query, query.data.split('_')[1])
            return
        elif query.data.startswith('details_'):
            await self.handle_symbol_details(query, query.data.split('_')[1])
            return

        # Executar handler apropriado
        handler = handlers.get(query.data)
        if handler:
            await handler(query)

    async def handle_status(self, query):
        """Exibe status do sistema."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Balanço total
            cursor.execute("""
                SELECT SUM(available_amount)
                FROM balances
                WHERE account_id = ? AND currency = 'USDT'
            """, (self.account_id,))

            usdt_balance = cursor.fetchone()[0] or 0

            # Contar trades hoje
            cursor.execute("""
                SELECT COUNT(*)
                FROM orders
                WHERE account_id = ?
                AND DATE(created_at) = DATE('now')
                AND status = 'FILLED'
            """, (self.account_id,))

            trades_today = cursor.fetchone()[0]

            conn.close()

            # Verificar sinais ativos
            active_signals = self._check_active_signals()

            message = (
                "*📊 STATUS DO SISTEMA*\n\n"
                f"💰 *Capital Disponível:* ${usdt_balance:.2f} USDT\n"
                f"📈 *Trades Hoje:* {trades_today}\n"
                f"📡 *Sinais Ativos:* {len(active_signals)}\n"
                f"👁 *Ativos Monitorados:* {len(self.watchlist.symbols)}\n"
                f"🤖 *Trading Bot:* {'🟢 Ativo' if self.daemon_active else '🔴 Pausado'}\n\n"
                f"⏰ *Última Atualização:* {datetime.now().strftime('%H:%M:%S')}"
            )

            keyboard = [[InlineKeyboardButton("🔙 Voltar", callback_data='back_main')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                text=message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Erro no status: {e}")
            await query.edit_message_text(f"❌ Erro: {e}")

    async def handle_portfolio(self, query):
        """Exibe portfólio detalhado."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT currency, available_amount, reserved_amount
                FROM balances
                WHERE account_id = ? AND (available_amount > 0 OR reserved_amount > 0)
                ORDER BY currency
            """, (self.account_id,))

            balances = cursor.fetchall()
            conn.close()

            message = "*💼 PORTFÓLIO*\n\n"
            total_usd = 0

            for currency, available, reserved in balances:
                total = available + reserved

                if currency == 'USDT':
                    value_usd = total
                    message += f"💵 *{currency}:* {total:.2f}\n"
                else:
                    # Obter preço atual
                    ticker = self.client.get_klines(f"{currency}USDT", '1m', limit=1)
                    if ticker:
                        price = float(ticker[0]['close'])
                        value_usd = total * price
                        message += f"🪙 *{currency}:* {total:.4f} (${value_usd:.2f})\n"
                    else:
                        value_usd = 0

                total_usd += value_usd

                if reserved > 0:
                    message += f"   ↳ Disponível: {available:.4f}\n"
                    message += f"   ↳ Reservado: {reserved:.4f}\n"

            message += f"\n💰 *Valor Total:* ${total_usd:.2f}"

            # P&L
            initial_capital = 5000.0
            pnl = total_usd - initial_capital
            pnl_pct = (pnl / initial_capital) * 100

            emoji = "🟢" if pnl >= 0 else "🔴"
            message += f"\n{emoji} *P&L:* {pnl:+.2f} USD ({pnl_pct:+.2f}%)"

            keyboard = [[InlineKeyboardButton("🔙 Voltar", callback_data='back_main')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                text=message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Erro no portfólio: {e}")
            await query.edit_message_text(f"❌ Erro: {e}")

    async def handle_watchlist(self, query):
        """Gerencia watchlist com botões."""
        try:
            symbols_data = self.watchlist.list_symbols()

            message = "*📋 WATCHLIST*\n\n"
            keyboard = []

            for item in symbols_data:
                symbol = item['symbol']
                base = symbol.replace('USDT', '')

                # Obter preço atual
                ticker = self.client.get_klines(symbol, '1m', limit=1)
                if ticker:
                    price = float(ticker[0]['close'])
                    message += f"• *{base}:* ${price:.2f}\n"

                # Botão para detalhes
                keyboard.append([
                    InlineKeyboardButton(
                        f"📊 {base} Detalhes",
                        callback_data=f'details_{symbol}'
                    ),
                    InlineKeyboardButton(
                        f"❌ Remover",
                        callback_data=f'remove_{symbol}'
                    )
                ])

            # Botões de ação
            keyboard.append([
                InlineKeyboardButton("➕ Adicionar Ativo", callback_data='add_new')
            ])
            keyboard.append([
                InlineKeyboardButton("🔙 Voltar", callback_data='back_main')
            ])

            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                text=message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Erro na watchlist: {e}")
            await query.edit_message_text(f"❌ Erro: {e}")

    async def handle_signals(self, query):
        """Mostra sinais de trading ativos."""
        try:
            signals = self._check_active_signals()

            if not signals:
                message = "*📡 SINAIS ATIVOS*\n\n_Nenhum sinal ativo no momento_"
            else:
                message = "*📡 SINAIS ATIVOS*\n\n"

                for signal in signals:
                    emoji = "🟢" if signal['type'] == 'BUY' else "🔴"
                    message += (
                        f"{emoji} *{signal['symbol']}* - {signal['timeframe']}\n"
                        f"   Tipo: {signal['type']}\n"
                        f"   Distância MA: {signal['distance']:.2f}%\n"
                        f"   Threshold: {signal['threshold']:.2f}%\n\n"
                    )

            keyboard = [
                [InlineKeyboardButton("🔄 Atualizar", callback_data='signals')],
                [InlineKeyboardButton("🔙 Voltar", callback_data='back_main')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                text=message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Erro nos sinais: {e}")
            await query.edit_message_text(f"❌ Erro: {e}")

    async def handle_performance(self, query):
        """Mostra performance dos últimos 7 dias."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Performance por dia
            cursor.execute("""
                SELECT
                    DATE(created_at) as date,
                    COUNT(*) as trades,
                    SUM(CASE WHEN order_type = 'SELL' THEN
                        (price - (SELECT price FROM orders o2
                         WHERE o2.symbol = orders.symbol
                         AND o2.order_type = 'BUY'
                         AND o2.created_at < orders.created_at
                         ORDER BY o2.created_at DESC LIMIT 1)) * quantity
                    ELSE 0 END) as profit
                FROM orders
                WHERE account_id = ?
                AND created_at >= datetime('now', '-7 days')
                AND status = 'FILLED'
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            """, (self.account_id,))

            performance = cursor.fetchall()
            conn.close()

            message = "*📈 PERFORMANCE - 7 DIAS*\n\n"

            total_trades = 0
            total_profit = 0

            for date, trades, profit in performance:
                total_trades += trades
                total_profit += profit or 0

                dt = datetime.fromisoformat(date)
                date_str = dt.strftime("%d/%m")

                emoji = "🟢" if (profit or 0) >= 0 else "🔴"
                message += f"{emoji} *{date_str}:* {trades} trades"
                if profit:
                    message += f" ({profit:+.2f} USD)"
                message += "\n"

            message += f"\n📊 *Total:* {total_trades} trades"
            if total_profit != 0:
                message += f" ({total_profit:+.2f} USD)"

            keyboard = [[InlineKeyboardButton("🔙 Voltar", callback_data='back_main')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                text=message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Erro na performance: {e}")
            await query.edit_message_text(f"❌ Erro: {e}")

    async def handle_history(self, query):
        """Mostra histórico de trades."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT symbol, order_type, quantity, price, created_at
                FROM orders
                WHERE account_id = ? AND status = 'FILLED'
                ORDER BY created_at DESC
                LIMIT 10
            """, (self.account_id,))

            trades = cursor.fetchall()
            conn.close()

            if not trades:
                message = "*📜 HISTÓRICO*\n\n_Sem transações ainda_"
            else:
                message = "*📜 ÚLTIMAS 10 TRANSAÇÕES*\n\n"

                for symbol, order_type, quantity, price, created_at in trades:
                    dt = datetime.fromisoformat(created_at)
                    time_str = dt.strftime("%d/%m %H:%M")
                    emoji = "🟢" if order_type == 'BUY' else "🔴"

                    message += (
                        f"{emoji} {time_str}\n"
                        f"{order_type} {quantity:.4f} {symbol.replace('USDT', '')}\n"
                        f"@ ${price:.2f}\n\n"
                    )

            keyboard = [[InlineKeyboardButton("🔙 Voltar", callback_data='back_main')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                text=message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Erro no histórico: {e}")
            await query.edit_message_text(f"❌ Erro: {e}")

    async def handle_settings(self, query):
        """Menu de configurações."""
        message = "*⚙️ CONFIGURAÇÕES*\n\n"
        message += f"🤖 *Trading Bot:* {'Ativo' if self.daemon_active else 'Pausado'}\n"
        message += f"💰 *Capital Inicial:* $5,000 USDT\n"
        message += f"📊 *Ativos Monitorados:* {len(self.watchlist.symbols)}\n\n"

        keyboard = []

        if self.daemon_active:
            keyboard.append([
                InlineKeyboardButton("⏸ Pausar Trading", callback_data='pause_trading')
            ])
        else:
            keyboard.append([
                InlineKeyboardButton("▶️ Retomar Trading", callback_data='resume_trading')
            ])

        keyboard.append([
            InlineKeyboardButton("📋 Gerenciar Watchlist", callback_data='watchlist')
        ])
        keyboard.append([
            InlineKeyboardButton("🔙 Voltar", callback_data='back_main')
        ])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text=message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def handle_pause(self, query):
        """Pausa o trading."""
        self.daemon_active = False
        await query.answer("⏸ Trading pausado!")
        await self.handle_settings(query)

    async def handle_resume(self, query):
        """Retoma o trading."""
        self.daemon_active = True
        await query.answer("▶️ Trading retomado!")
        await self.handle_settings(query)

    async def handle_refresh(self, query):
        """Atualiza o menu principal."""
        await query.answer("🔄 Atualizando...")
        await self.back_to_main(query)

    async def back_to_main(self, query):
        """Volta ao menu principal."""
        keyboard = [
            [
                InlineKeyboardButton("📊 Status", callback_data='status'),
                InlineKeyboardButton("💼 Portfólio", callback_data='portfolio')
            ],
            [
                InlineKeyboardButton("📋 Watchlist", callback_data='watchlist'),
                InlineKeyboardButton("📡 Sinais", callback_data='signals')
            ],
            [
                InlineKeyboardButton("📈 Performance", callback_data='performance'),
                InlineKeyboardButton("📜 Histórico", callback_data='history')
            ],
            [
                InlineKeyboardButton("⚙️ Configurações", callback_data='settings'),
                InlineKeyboardButton("🔄 Atualizar", callback_data='refresh')
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        message = (
            "*🤖 Bot de Trading Multi-Ativo*\n\n"
            f"💰 Capital: $5,000 USDT\n"
            f"📊 Ativos: {len(self.watchlist.symbols)}\n"
            f"🟢 Status: {'Ativo' if self.daemon_active else 'Pausado'}\n\n"
            "_Escolha uma opção:_"
        )

        await query.edit_message_text(
            text=message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def handle_symbol_details(self, query, symbol: str):
        """Mostra detalhes de um símbolo."""
        try:
            params = {
                '1h': self.watchlist.get_params(symbol, '1h'),
                '4h': self.watchlist.get_params(symbol, '4h'),
                '1d': self.watchlist.get_params(symbol, '1d')
            }

            message = f"*📊 DETALHES - {symbol}*\n\n"

            # Preço atual
            ticker = self.client.get_klines(symbol, '1m', limit=1)
            if ticker:
                price = float(ticker[0]['close'])
                message += f"💵 *Preço Atual:* ${price:.2f}\n\n"

            # Parâmetros por timeframe
            message += "*Parâmetros de Trading:*\n\n"

            for tf, p in params.items():
                if p:
                    message += f"*{tf.upper()}:*\n"
                    message += f"  • MA{p['ma_period']}\n"
                    message += f"  • Compra: < {p['buy_threshold']:.1f}%\n"
                    message += f"  • Venda: > {p['sell_threshold']:.1f}%\n\n"

            keyboard = [[InlineKeyboardButton("🔙 Voltar", callback_data='watchlist')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                text=message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Erro nos detalhes: {e}")
            await query.edit_message_text(f"❌ Erro: {e}")

    def _check_active_signals(self) -> List[Dict]:
        """Verifica sinais ativos no momento."""
        signals = []

        for symbol in self.watchlist.symbols:
            for tf in ['1h', '4h', '1d']:
                params = self.watchlist.get_params(symbol, tf)
                if not params:
                    continue

                # Obter MA e preço atual
                ma_period = params['ma_period']
                klines = self.client.get_klines(symbol, tf, limit=ma_period + 1)

                if len(klines) >= ma_period:
                    closes = [float(k['close']) for k in klines[:-1]]
                    ma = sum(closes[-ma_period:]) / ma_period
                    current_price = float(klines[-1]['close'])
                    distance = ((current_price - ma) / ma) * 100

                    # Verificar sinais
                    if distance < params['buy_threshold']:
                        signals.append({
                            'symbol': symbol,
                            'timeframe': tf,
                            'type': 'BUY',
                            'distance': distance,
                            'threshold': params['buy_threshold']
                        })
                    elif distance > params['sell_threshold']:
                        signals.append({
                            'symbol': symbol,
                            'timeframe': tf,
                            'type': 'SELL',
                            'distance': distance,
                            'threshold': params['sell_threshold']
                        })

        return signals

    def run(self):
        """Executa o bot."""
        application = Application.builder().token(self.token).build()

        # Handlers
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CallbackQueryHandler(self.button_handler))

        # Iniciar bot
        logger.info("🤖 Bot Telegram Enhanced iniciado!")
        application.run_polling()


def main():
    """Main entry point."""
    bot = EnhancedTradingBot()
    bot.run()


if __name__ == "__main__":
    main()