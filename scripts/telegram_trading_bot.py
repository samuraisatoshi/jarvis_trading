#!/usr/bin/env python3
"""
Bot Telegram Completo para Trading Multi-Ativo

Comandos disponíveis:
- /status - Status do portfólio
- /balance - Balanços detalhados
- /trades - Últimas transações
- /watchlist - Gerenciar watchlist
- /add <symbol> - Adicionar ativo
- /remove <symbol> - Remover ativo
- /performance - Métricas de performance
- /pause - Pausar trading
- /resume - Retomar trading
- /help - Ajuda
"""

import sys
import os
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from scripts.watchlist_manager import WatchlistManager
from src.infrastructure.exchange.binance_rest_client import BinanceRESTClient


class TradingBot:
    """Bot Telegram para gerenciar trading multi-ativo."""

    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.allowed_chat_id = int(chat_id)
        self.db_path = 'data/jarvis_trading.db'
        self.account_id = '868e0dd8-37f5-43ea-a956-7cc05e6bad66'

        self.watchlist = WatchlistManager()
        self.client = BinanceRESTClient(testnet=False)

        # Estado do daemon
        self.daemon_paused = False

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start."""
        if update.effective_chat.id != self.allowed_chat_id:
            return

        await update.message.reply_text(
            "🤖 *Bot de Trading Multi-Ativo*\n\n"
            "Comandos disponíveis:\n"
            "/status - Status do portfólio\n"
            "/balance - Balanços detalhados\n"
            "/trades - Últimas transações\n"
            "/watchlist - Lista de ativos\n"
            "/add SYMBOL - Adicionar ativo\n"
            "/remove SYMBOL - Remover ativo\n"
            "/performance - Métricas\n"
            "/pause - Pausar trading\n"
            "/resume - Retomar trading\n"
            "/help - Ajuda",
            parse_mode='Markdown'
        )

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /status - Status geral do portfólio."""
        if update.effective_chat.id != self.allowed_chat_id:
            return

        try:
            # Obter balanços
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT currency, available_amount
                FROM balances
                WHERE account_id = ?
            """, (self.account_id,))

            balances = dict(cursor.fetchall())
            usdt_balance = balances.get('USDT', 0.0)
            total_value = usdt_balance

            # Calcular valor das posições
            positions_text = ""
            for symbol in self.watchlist.symbols:
                base_currency = symbol.replace('USDT', '')
                if base_currency in balances and balances[base_currency] > 0:
                    quantity = balances[base_currency]
                    ticker = self.client.get_24h_ticker(symbol)
                    price = float(ticker['lastPrice'])
                    value = quantity * price
                    total_value += value
                    change_pct = float(ticker['priceChangePercent'])

                    emoji = "🟢" if change_pct > 0 else "🔴"
                    positions_text += f"{emoji} {base_currency}: {quantity:.4f} @ ${price:.2f} ({change_pct:+.1f}%)\n"

            # Calcular P&L
            initial_capital = 5000.0
            pnl = total_value - initial_capital
            pnl_pct = (pnl / initial_capital) * 100

            message = f"📊 *STATUS DO PORTFÓLIO*\n\n"
            message += f"💰 Valor Total: *${total_value:.2f}*\n"
            message += f"📈 P&L: ${pnl:.2f} ({pnl_pct:+.2f}%)\n"
            message += f"💵 USDT Livre: ${usdt_balance:.2f}\n\n"

            if positions_text:
                message += f"*Posições Abertas:*\n{positions_text}\n"
            else:
                message += "Sem posições abertas\n\n"

            # Watchlist
            message += f"📋 *Watchlist:* {', '.join(self.watchlist.symbols)}\n"

            # Status do daemon
            status_emoji = "⚠️" if self.daemon_paused else "✅"
            message += f"\n{status_emoji} Trading: {'Pausado' if self.daemon_paused else 'Ativo'}"

            conn.close()

            await update.message.reply_text(message, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Erro no comando status: {e}")
            await update.message.reply_text(f"❌ Erro ao obter status: {e}")

    async def balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /balance - Balanços detalhados."""
        if update.effective_chat.id != self.allowed_chat_id:
            return

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

            if not balances:
                await update.message.reply_text("💰 Sem balanços")
                return

            message = "💰 *BALANÇOS*\n\n"
            total_usd = 0

            for currency, available, reserved in balances:
                total = available + reserved

                if currency == 'USDT':
                    value = total
                    message += f"*{currency}:* {total:.2f}\n"
                else:
                    # Obter preço atual
                    symbol = f"{currency}USDT"
                    try:
                        ticker = self.client.get_24h_ticker(symbol)
                        price = float(ticker['lastPrice'])
                        value = total * price
                        message += f"*{currency}:* {total:.6f} @ ${price:.2f} = ${value:.2f}\n"
                    except:
                        value = 0
                        message += f"*{currency}:* {total:.6f}\n"

                total_usd += value

            message += f"\n💎 *Total em USD:* ${total_usd:.2f}"

            await update.message.reply_text(message, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Erro no comando balance: {e}")
            await update.message.reply_text(f"❌ Erro: {e}")

    async def trades(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /trades - Últimas transações."""
        if update.effective_chat.id != self.allowed_chat_id:
            return

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
                await update.message.reply_text("📊 Sem transações")
                return

            message = "📊 *ÚLTIMAS TRANSAÇÕES*\n\n"

            for symbol, order_type, quantity, price, created_at in trades:
                dt = datetime.fromisoformat(created_at)
                time_str = dt.strftime("%d/%m %H:%M")
                emoji = "🟢" if order_type == 'BUY' else "🔴"

                message += f"{emoji} {time_str}\n"
                message += f"{order_type} {quantity:.4f} {symbol.replace('USDT', '')}\n"
                message += f"@ ${price:.2f}\n\n"

            await update.message.reply_text(message, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Erro no comando trades: {e}")
            await update.message.reply_text(f"❌ Erro: {e}")

    async def watchlist_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /watchlist - Lista ativos monitorados."""
        if update.effective_chat.id != self.allowed_chat_id:
            return

        try:
            symbols_data = self.watchlist.list_symbols()

            if not symbols_data:
                await update.message.reply_text("📋 Watchlist vazia")
                return

            message = "📋 *WATCHLIST*\n\n"

            for item in symbols_data:
                symbol = item['symbol']
                base = symbol.replace('USDT', '')

                # Obter preço atual
                ticker = self.client.get_24h_ticker(symbol)
                price = float(ticker['lastPrice'])
                change = float(ticker['priceChangePercent'])

                emoji = "🟢" if change > 0 else "🔴"
                message += f"{emoji} *{base}*: ${price:.2f} ({change:+.1f}%)\n"

                # Parâmetros
                if item['params_1h']:
                    message += f"  1H: {item['params_1h']['buy_threshold']:.1f}% / {item['params_1h']['sell_threshold']:.1f}%\n"
                if item['params_4h']:
                    message += f"  4H: {item['params_4h']['buy_threshold']:.1f}% / {item['params_4h']['sell_threshold']:.1f}%\n"
                if item['params_1d']:
                    message += f"  1D: {item['params_1d']['buy_threshold']:.1f}% / {item['params_1d']['sell_threshold']:.1f}%\n"

                message += "\n"

            message += f"Total: {len(symbols_data)} ativos"

            await update.message.reply_text(message, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Erro no comando watchlist: {e}")
            await update.message.reply_text(f"❌ Erro: {e}")

    async def add_symbol(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /add <symbol> - Adiciona ativo à watchlist."""
        if update.effective_chat.id != self.allowed_chat_id:
            return

        if not context.args:
            await update.message.reply_text("Uso: /add SYMBOL\nEx: /add SOLUSDT")
            return

        symbol = context.args[0].upper().replace('/', '').replace('_', '')

        # Garantir que termina com USDT
        if not symbol.endswith('USDT'):
            symbol += 'USDT'

        await update.message.reply_text(f"⏳ Adicionando {symbol}...")

        try:
            result = self.watchlist.add_symbol(symbol)

            if result['status'] == 'success':
                params = result.get('params', {})
                message = f"✅ *{symbol} adicionado com sucesso!*\n\n"

                if params:
                    message += "*Parâmetros calculados:*\n"
                    for tf in ['1h', '4h', '1d']:
                        if tf in params:
                            p = params[tf]
                            message += f"{tf.upper()}: Compra {p['buy_threshold']:.1f}%, Venda {p['sell_threshold']:.1f}%\n"

                await update.message.reply_text(message, parse_mode='Markdown')
            else:
                await update.message.reply_text(f"❌ {result['message']}")

        except Exception as e:
            logger.error(f"Erro ao adicionar {symbol}: {e}")
            await update.message.reply_text(f"❌ Erro: {e}")

    async def remove_symbol(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /remove <symbol> - Remove ativo da watchlist."""
        if update.effective_chat.id != self.allowed_chat_id:
            return

        if not context.args:
            await update.message.reply_text("Uso: /remove SYMBOL\nEx: /remove SOLUSDT")
            return

        symbol = context.args[0].upper().replace('/', '').replace('_', '')

        if not symbol.endswith('USDT'):
            symbol += 'USDT'

        try:
            result = self.watchlist.remove_symbol(symbol)

            if result['status'] == 'success':
                await update.message.reply_text(f"✅ {symbol} removido da watchlist")
            else:
                await update.message.reply_text(f"❌ {result['message']}")

        except Exception as e:
            logger.error(f"Erro ao remover {symbol}: {e}")
            await update.message.reply_text(f"❌ Erro: {e}")

    async def performance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /performance - Métricas de performance."""
        if update.effective_chat.id != self.allowed_chat_id:
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Estatísticas de trades
            cursor.execute("""
                SELECT
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN order_type = 'BUY' THEN 1 ELSE 0 END) as buys,
                    SUM(CASE WHEN order_type = 'SELL' THEN 1 ELSE 0 END) as sells
                FROM orders
                WHERE account_id = ? AND status = 'FILLED'
                AND created_at > datetime('now', '-7 days')
            """, (self.account_id,))

            stats = cursor.fetchone()
            total_trades, buys, sells = stats

            # Win rate (simplificado)
            cursor.execute("""
                SELECT COUNT(*) FROM transactions
                WHERE account_id = ? AND transaction_type = 'SELL'
                AND amount > 0
                AND created_at > datetime('now', '-7 days')
            """, (self.account_id,))

            profitable_trades = cursor.fetchone()[0]

            conn.close()

            win_rate = (profitable_trades / sells * 100) if sells > 0 else 0

            message = "📈 *PERFORMANCE (7 DIAS)*\n\n"
            message += f"Total de Trades: {total_trades}\n"
            message += f"Compras: {buys}\n"
            message += f"Vendas: {sells}\n"
            message += f"Taxa de Acerto: {win_rate:.1f}%\n"

            await update.message.reply_text(message, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Erro no comando performance: {e}")
            await update.message.reply_text(f"❌ Erro: {e}")

    async def pause(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /pause - Pausa o trading."""
        if update.effective_chat.id != self.allowed_chat_id:
            return

        self.daemon_paused = True
        await update.message.reply_text("⏸️ Trading pausado")

    async def resume(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /resume - Retoma o trading."""
        if update.effective_chat.id != self.allowed_chat_id:
            return

        self.daemon_paused = False
        await update.message.reply_text("▶️ Trading retomado")

    async def help_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /help."""
        if update.effective_chat.id != self.allowed_chat_id:
            return

        message = """
*📚 AJUDA - Bot de Trading*

*Comandos Principais:*
/status - Status completo do portfólio
/balance - Balanços detalhados por moeda
/trades - Últimas 10 transações

*Gerenciar Watchlist:*
/watchlist - Lista ativos monitorados
/add SYMBOL - Adicionar ativo (ex: /add SOLUSDT)
/remove SYMBOL - Remover ativo

*Controle:*
/pause - Pausar trading automático
/resume - Retomar trading
/performance - Métricas de performance

*Estratégia:*
O bot monitora múltiplos ativos em 3 timeframes (1h, 4h, 1d) e executa trades baseado em distâncias otimizadas das médias móveis.

*Parâmetros:*
• 1H: Trades rápidos (10% capital)
• 4H: Swing trades (20% capital)
• 1D: Position trades (30% capital)
        """

        await update.message.reply_text(message, parse_mode='Markdown')


def main():
    """Main entry point."""
    # Obter credenciais do .env
    from dotenv import load_dotenv
    load_dotenv()

    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')

    if not token or not chat_id:
        logger.error("Configure TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID no .env")
        return

    # Criar bot
    bot = TradingBot(token, chat_id)

    # Criar application
    app = Application.builder().token(token).build()

    # Adicionar handlers
    app.add_handler(CommandHandler("start", bot.start))
    app.add_handler(CommandHandler("status", bot.status))
    app.add_handler(CommandHandler("balance", bot.balance))
    app.add_handler(CommandHandler("trades", bot.trades))
    app.add_handler(CommandHandler("watchlist", bot.watchlist_cmd))
    app.add_handler(CommandHandler("add", bot.add_symbol))
    app.add_handler(CommandHandler("remove", bot.remove_symbol))
    app.add_handler(CommandHandler("performance", bot.performance))
    app.add_handler(CommandHandler("pause", bot.pause))
    app.add_handler(CommandHandler("resume", bot.resume))
    app.add_handler(CommandHandler("help", bot.help_cmd))

    logger.info("🤖 Bot Telegram iniciado")
    logger.info(f"Chat ID autorizado: {chat_id}")

    # Executar bot
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()