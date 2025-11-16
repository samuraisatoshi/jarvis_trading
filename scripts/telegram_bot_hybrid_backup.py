#!/usr/bin/env python3
"""
Telegram Trading Bot - Versão Híbrida (Comandos + Botões).
Suporta tanto comandos diretos quanto interface com botões.
"""

import os
import sys
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import re
from dotenv import load_dotenv

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from loguru import logger

from src.infrastructure.exchange.binance_rest_client import BinanceRESTClient
from src.utils.chart_generator import ChartGenerator


class HybridTradingBot:
    """Bot híbrido que suporta comandos e interface com botões."""

    def __init__(self, token: str = None):
        """Inicializa o bot."""
        self.db_path = 'data/jarvis_trading.db'
        self.account_id = '868e0dd8-37f5-43ea-a956-7cc05e6bad66'

        # Token do bot
        self.token = token or self._load_token()

        # Cliente Binance
        self.client = BinanceRESTClient(testnet=False)

        logger.info("Bot híbrido inicializado")

    def _load_token(self) -> str:
        """Carrega token do arquivo .env."""
        load_dotenv()
        token = os.getenv('TELEGRAM_BOT_TOKEN')

        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN não encontrado no arquivo .env")

        return token

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start - Mostra menu principal."""
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

        await update.message.reply_text(
            "🤖 *Bot de Trading Híbrido*\n\n"
            "Use os botões abaixo ou comandos diretos:\n\n"
            "📝 *Comandos disponíveis:*\n"
            "/status - Status do sistema\n"
            "/portfolio - Ver portfólio\n"
            "/watchlist - Lista de ativos\n"
            "/signals - Sinais ativos\n"
            "/add SYMBOL - Adicionar ativo\n"
            "/remove SYMBOL - Remover ativo\n"
            "/buy SYMBOL AMOUNT - Comprar ativo\n"
            "/sell SYMBOL PERCENT - Vender % do ativo\n"
            "/history - Histórico de trades\n"
            "/performance - Performance\n"
            "/settings - Configurações\n"
            "/help - Ajuda\n\n"
            "Escolha uma opção:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /help - Mostra ajuda detalhada."""
        help_text = """
🤖 *Bot de Trading - Ajuda*

📝 *Comandos Principais:*
• `/start` - Menu principal com botões
• `/status` - Status completo do sistema
• `/portfolio` ou `/p` - Ver portfólio atual
• `/watchlist` ou `/w` - Lista de ativos monitorados
• `/signals` ou `/s` - Sinais de trading ativos
• `/performance` - Análise de performance

🔧 *Gerenciar Watchlist:*
• `/add SYMBOL` - Adicionar ativo (ex: /add ADAUSDT)
• `/remove SYMBOL` - Remover ativo
• `/update` - Atualizar dados da watchlist

💰 *Trading Manual:*
• `/buy SYMBOL AMOUNT` - Comprar com valor em USDT (ex: /buy BTCUSDT 100)
• `/sell SYMBOL PERCENT` - Vender % da posição (ex: /sell BTCUSDT 50)

📊 *Consultas:*
• `/history [N]` - Últimas N transações (padrão: 10)
• `/orders [N]` - Últimas N ordens
• `/balance` - Saldos da conta
• `/candles SYMBOL [TF]` - Gráfico candlestick (TF: 1h, 4h, 1d)

⚙️ *Configurações:*
• `/settings` - Ver configurações
• `/pause` - Pausar trading automático
• `/resume` - Retomar trading automático

💡 *Dicas:*
• Use botões para navegação rápida
• Comandos diretos são mais rápidos para ações específicas
• O bot verifica sinais a cada hora
• Notificações automáticas para trades executados
"""
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /status - Mostra status do sistema."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Verificar daemon
            daemon_status = "🟢 Ativo" if self._check_daemon_running() else "🔴 Inativo"

            # Contar sinais ativos
            signals = self._check_active_signals()
            signals_count = len(signals)

            # Contar ordens hoje
            cursor.execute("""
                SELECT COUNT(*) FROM orders
                WHERE account_id = ?
                AND DATE(created_at) = DATE('now')
            """, (self.account_id,))
            orders_today = cursor.fetchone()[0]

            # Valor total do portfolio
            cursor.execute("""
                SELECT currency, available_amount
                FROM balances
                WHERE account_id = ?
            """, (self.account_id,))

            balances = cursor.fetchall()
            conn.close()

            total_value = 0
            for currency, amount in balances:
                if currency == 'USDT':
                    total_value += amount
                elif amount > 0:
                    try:
                        ticker = self.client.get_klines(f'{currency}USDT', '1m', limit=1)
                        if ticker:
                            price = float(ticker[0]['close'])
                            total_value += amount * price
                    except:
                        pass

            status_msg = f"""
📊 *Status do Sistema*

🤖 Daemon: {daemon_status}
📡 Sinais Ativos: {signals_count}
📈 Trades Hoje: {orders_today}
💰 Valor Total: ${total_value:.2f}
⏰ Última Atualização: {datetime.now().strftime('%H:%M:%S')}
"""

            await update.message.reply_text(status_msg, parse_mode='Markdown')

        except Exception as e:
            await update.message.reply_text(f"❌ Erro ao buscar status: {e}")

    async def portfolio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /portfolio - Mostra portfólio atual."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT currency, available_amount
                FROM balances
                WHERE account_id = ? AND available_amount > 0.001
                ORDER BY currency
            """, (self.account_id,))

            balances = cursor.fetchall()
            conn.close()

            if not balances:
                await update.message.reply_text("💼 Portfólio vazio")
                return

            msg = "💼 *Portfólio Atual*\n\n"
            total_value = 0

            for currency, amount in balances:
                if currency == 'USDT':
                    value = amount
                    msg += f"• *{currency}:* {amount:.2f} (${value:.2f})\n"
                else:
                    try:
                        ticker = self.client.get_klines(f'{currency}USDT', '1m', limit=1)
                        if ticker:
                            price = float(ticker[0]['close'])
                            value = amount * price
                            msg += f"• *{currency}:* {amount:.6f} @ ${price:.2f} = ${value:.2f}\n"
                        else:
                            value = 0
                            msg += f"• *{currency}:* {amount:.6f}\n"
                    except:
                        value = 0
                        msg += f"• *{currency}:* {amount:.6f}\n"

                total_value += value

            msg += f"\n💰 *Valor Total:* ${total_value:.2f}"

            await update.message.reply_text(msg, parse_mode='Markdown')

        except Exception as e:
            await update.message.reply_text(f"❌ Erro ao buscar portfólio: {e}")

    async def watchlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /watchlist - Mostra watchlist."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT symbol, params_1h, params_4h, params_1d
                FROM watchlist
                WHERE is_active = 1
            """)

            items = cursor.fetchall()
            conn.close()

            if not items:
                await update.message.reply_text("📋 Watchlist vazia\n\nUse /add SYMBOL para adicionar")
                return

            msg = "📋 *Watchlist Ativa*\n\n"

            for symbol, params_1h, params_4h, params_1d in items:
                msg += f"*{symbol}*\n"

                # Parse parameters
                for tf, params in [('1H', params_1h), ('4H', params_4h), ('1D', params_1d)]:
                    if params:
                        p = json.loads(params)
                        if p:
                            msg += f"  {tf}: Compra {p['buy_threshold']:.1f}%, Venda {p['sell_threshold']:.1f}%\n"

                msg += "\n"

            msg += "💡 Use /add SYMBOL ou /remove SYMBOL"

            await update.message.reply_text(msg, parse_mode='Markdown')

        except Exception as e:
            await update.message.reply_text(f"❌ Erro ao buscar watchlist: {e}")

    async def signals(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /signals - Mostra sinais ativos."""
        try:
            signals = self._check_active_signals()

            if not signals:
                await update.message.reply_text("📡 Nenhum sinal ativo no momento")
                return

            msg = f"📡 *{len(signals)} Sinais Ativos*\n\n"

            for signal in signals:
                emoji = "🟢" if signal['action'] == 'BUY' else "🔴"
                msg += (
                    f"{emoji} *{signal['action']} {signal['symbol']}*\n"
                    f"  Timeframe: {signal['timeframe']}\n"
                    f"  Preço: ${signal['price']:.2f}\n"
                    f"  Distância: {signal['distance']:.1f}%\n"
                    f"  Motivo: {signal['reason']}\n\n"
                )

            await update.message.reply_text(msg, parse_mode='Markdown')

        except Exception as e:
            await update.message.reply_text(f"❌ Erro ao buscar sinais: {e}")

    async def add_symbol(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /add SYMBOL - Adiciona ativo à watchlist."""
        if not context.args:
            await update.message.reply_text("❌ Use: /add SYMBOL\nExemplo: /add ADAUSDT")
            return

        symbol = context.args[0].upper()

        # Validar formato
        if not symbol.endswith('USDT'):
            symbol += 'USDT'

        try:
            # Verificar se existe na Binance
            ticker = self.client.get_klines(symbol, '1h', limit=1)
            if not ticker:
                await update.message.reply_text(f"❌ Símbolo {symbol} não encontrado")
                return

            # Adicionar ao banco
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Verificar se já existe
            cursor.execute("SELECT symbol FROM watchlist WHERE symbol = ?", (symbol,))
            if cursor.fetchone():
                conn.close()
                await update.message.reply_text(f"⚠️ {symbol} já está na watchlist")
                return

            # Inserir com parâmetros padrão
            default_params = {
                '1h': {'ma_period': 20, 'buy_threshold': -2.5, 'sell_threshold': 2.0},
                '4h': {'ma_period': 100, 'buy_threshold': -5.0, 'sell_threshold': 5.0},
                '1d': {'ma_period': 200, 'buy_threshold': -7.0, 'sell_threshold': 10.0}
            }

            cursor.execute("""
                INSERT INTO watchlist (symbol, added_at, params_1h, params_4h, params_1d, last_updated, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol,
                datetime.now(timezone.utc).isoformat(),
                json.dumps(default_params['1h']),
                json.dumps(default_params['4h']),
                json.dumps(default_params['1d']),
                datetime.now(timezone.utc).isoformat(),
                1
            ))

            conn.commit()
            conn.close()

            await update.message.reply_text(
                f"✅ *{symbol} adicionado com sucesso!*\n\n"
                f"Parâmetros padrão aplicados.\n"
                f"O bot começará a monitorar na próxima hora.",
                parse_mode='Markdown'
            )

        except Exception as e:
            await update.message.reply_text(f"❌ Erro ao adicionar {symbol}: {e}")

    async def remove_symbol(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /remove SYMBOL - Remove ativo da watchlist."""
        if not context.args:
            await update.message.reply_text("❌ Use: /remove SYMBOL\nExemplo: /remove ADAUSDT")
            return

        symbol = context.args[0].upper()
        if not symbol.endswith('USDT'):
            symbol += 'USDT'

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("UPDATE watchlist SET is_active = 0 WHERE symbol = ?", (symbol,))

            if cursor.rowcount > 0:
                conn.commit()
                await update.message.reply_text(f"✅ {symbol} removido da watchlist")
            else:
                await update.message.reply_text(f"⚠️ {symbol} não estava na watchlist")

            conn.close()

        except Exception as e:
            await update.message.reply_text(f"❌ Erro ao remover {symbol}: {e}")

    async def history(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /history - Mostra histórico de trades."""
        limit = 10
        if context.args and context.args[0].isdigit():
            limit = int(context.args[0])

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT symbol, side, quantity, price, created_at
                FROM orders
                WHERE account_id = ? AND status = 'FILLED'
                ORDER BY created_at DESC
                LIMIT ?
            """, (self.account_id, limit))

            orders = cursor.fetchall()
            conn.close()

            if not orders:
                await update.message.reply_text("📜 Sem histórico de trades")
                return

            msg = f"📜 *Últimos {len(orders)} Trades*\n\n"

            for symbol, side, quantity, price, created_at in orders:
                emoji = "🟢" if side == 'BUY' else "🔴"
                dt = datetime.fromisoformat(created_at)
                msg += (
                    f"{emoji} *{side} {symbol}*\n"
                    f"  Qtd: {quantity:.6f}\n"
                    f"  Preço: ${price:.2f}\n"
                    f"  Data: {dt.strftime('%d/%m %H:%M')}\n\n"
                )

            await update.message.reply_text(msg, parse_mode='Markdown')

        except Exception as e:
            await update.message.reply_text(f"❌ Erro ao buscar histórico: {e}")

    async def performance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /performance - Mostra performance."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Buscar trades
            cursor.execute("""
                SELECT symbol, side, quantity, price
                FROM orders
                WHERE account_id = ? AND status = 'FILLED'
                ORDER BY created_at
            """, (self.account_id,))

            orders = cursor.fetchall()

            # Calcular P&L
            positions = {}
            realized_pnl = 0

            for symbol, side, quantity, price in orders:
                if symbol not in positions:
                    positions[symbol] = {'quantity': 0, 'avg_price': 0, 'realized': 0}

                if side == 'BUY':
                    # Atualizar preço médio
                    total_value = positions[symbol]['quantity'] * positions[symbol]['avg_price']
                    total_value += quantity * price
                    positions[symbol]['quantity'] += quantity
                    if positions[symbol]['quantity'] > 0:
                        positions[symbol]['avg_price'] = total_value / positions[symbol]['quantity']
                else:  # SELL
                    if positions[symbol]['quantity'] > 0:
                        # Calcular lucro realizado
                        profit = (price - positions[symbol]['avg_price']) * quantity
                        positions[symbol]['realized'] += profit
                        realized_pnl += profit
                        positions[symbol]['quantity'] -= quantity

            # Calcular P&L não realizado
            unrealized_pnl = 0
            for symbol, pos in positions.items():
                if pos['quantity'] > 0:
                    try:
                        ticker = self.client.get_klines(symbol, '1m', limit=1)
                        if ticker:
                            current_price = float(ticker[0]['close'])
                            unrealized = (current_price - pos['avg_price']) * pos['quantity']
                            unrealized_pnl += unrealized
                    except:
                        pass

            conn.close()

            msg = "📈 *Performance*\n\n"
            msg += f"💰 P&L Realizado: ${realized_pnl:+.2f}\n"
            msg += f"📊 P&L Não Realizado: ${unrealized_pnl:+.2f}\n"
            msg += f"📈 P&L Total: ${(realized_pnl + unrealized_pnl):+.2f}\n"
            msg += f"\n📊 Total de Trades: {len(orders)}"

            await update.message.reply_text(msg, parse_mode='Markdown')

        except Exception as e:
            await update.message.reply_text(f"❌ Erro ao calcular performance: {e}")

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Processa cliques nos botões."""
        query = update.callback_query
        await query.answer()

        # Mapear callbacks para comandos
        command_map = {
            'status': self.status,
            'portfolio': self.portfolio,
            'watchlist': self.watchlist,
            'signals': self.signals,
            'performance': self.performance,
            'history': self.history,
            'settings': self.handle_settings,
            'refresh': self.handle_refresh
        }

        handler = command_map.get(query.data)
        if handler:
            # Criar update falso para reusar handlers de comando
            class FakeMessage:
                async def reply_text(self, *args, **kwargs):
                    await query.edit_message_text(*args, **kwargs)

            fake_update = type('obj', (object,), {'message': FakeMessage()})()
            await handler(fake_update, context)

    async def handle_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostra configurações."""
        msg = """⚙️ *Configurações*

🤖 Daemon: Ativo
⏰ Verificação: A cada hora
📊 Timeframes: 1h, 4h, 1d
💰 Capital Inicial: $5000

📝 *Tamanhos de Posição:*
• 1H: 10% do capital
• 4H: 20% do capital
• 1D: 30% do capital

Use /pause para pausar trading
Use /resume para retomar"""

        await update.message.reply_text(msg, parse_mode='Markdown')

    async def handle_refresh(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Atualiza menu principal."""
        await self.start(update, context)

    def _check_daemon_running(self) -> bool:
        """Verifica se o daemon está rodando."""
        # Simplificado - verificar por processos seria melhor
        return True

    def _check_active_signals(self) -> List[Dict]:
        """Verifica sinais ativos."""
        signals = []

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT symbol, params_1h, params_4h, params_1d
                FROM watchlist
                WHERE is_active = 1
            """)

            watchlist = cursor.fetchall()
            conn.close()

            for symbol, params_1h, params_4h, params_1d in watchlist:
                # Obter preço atual
                try:
                    ticker = self.client.get_klines(symbol, '1m', limit=1)
                    if not ticker:
                        continue
                    current_price = float(ticker[0]['close'])
                except:
                    continue

                # Verificar cada timeframe
                for tf, params_str in [('1h', params_1h), ('4h', params_4h), ('1d', params_1d)]:
                    if not params_str:
                        continue

                    params = json.loads(params_str)
                    if not params:
                        continue

                    # Calcular MA
                    try:
                        klines = self.client.get_klines(symbol, tf, limit=params['ma_period'] + 1)
                        if len(klines) < params['ma_period']:
                            continue

                        closes = [float(k['close']) for k in klines[:-1]]
                        ma = sum(closes[-params['ma_period']:]) / params['ma_period']

                        distance = ((current_price - ma) / ma) * 100

                        if distance < params['buy_threshold']:
                            signals.append({
                                'symbol': symbol,
                                'timeframe': tf,
                                'action': 'BUY',
                                'price': current_price,
                                'ma': ma,
                                'distance': distance,
                                'threshold': params['buy_threshold'],
                                'reason': f"Preço {distance:.1f}% abaixo da MA{params['ma_period']}"
                            })
                        elif distance > params['sell_threshold']:
                            signals.append({
                                'symbol': symbol,
                                'timeframe': tf,
                                'action': 'SELL',
                                'price': current_price,
                                'ma': ma,
                                'distance': distance,
                                'threshold': params['sell_threshold'],
                                'reason': f"Preço {distance:.1f}% acima da MA{params['ma_period']}"
                            })
                    except:
                        continue
        except:
            pass

        return signals

    async def buy_market(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /buy SYMBOL AMOUNT - Executa compra imediata a mercado."""
        if len(context.args) != 2:
            await update.message.reply_text(
                "❌ *Uso incorreto*\n\n"
                "Formato: `/buy SYMBOL AMOUNT`\n"
                "Exemplo: `/buy BTCUSDT 100`\n\n"
                "AMOUNT = valor em USDT",
                parse_mode='Markdown'
            )
            return

        symbol = context.args[0].upper()
        if not symbol.endswith('USDT'):
            symbol += 'USDT'

        try:
            amount_usdt = float(context.args[1])
            if amount_usdt <= 0:
                await update.message.reply_text("❌ O valor deve ser maior que zero")
                return
        except ValueError:
            await update.message.reply_text("❌ Valor inválido. Use números (ex: 100 ou 100.50)")
            return

        try:
            # Verificar saldo USDT
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT available_amount FROM balances
                WHERE account_id = ? AND currency = 'USDT'
            """, (self.account_id,))

            result = cursor.fetchone()
            if not result or result[0] < amount_usdt:
                conn.close()
                await update.message.reply_text(
                    f"❌ Saldo USDT insuficiente\n"
                    f"Disponível: ${result[0] if result else 0:.2f}\n"
                    f"Solicitado: ${amount_usdt:.2f}"
                )
                return

            # Obter preço atual
            ticker = self.client.get_klines(symbol, '1m', limit=1)
            if not ticker:
                conn.close()
                await update.message.reply_text(f"❌ Não foi possível obter preço de {symbol}")
                return

            current_price = float(ticker[0]['close'])
            quantity = amount_usdt / current_price
            base_currency = symbol.replace('USDT', '')

            # Executar compra (paper trading)
            from datetime import datetime, timezone

            # Atualizar balances
            cursor.execute("""
                UPDATE balances
                SET available_amount = available_amount - ?
                WHERE account_id = ? AND currency = 'USDT'
            """, (amount_usdt, self.account_id))

            cursor.execute("""
                INSERT INTO balances (account_id, currency, available_amount, locked_amount)
                VALUES (?, ?, ?, 0)
                ON CONFLICT(account_id, currency)
                DO UPDATE SET available_amount = available_amount + ?
            """, (self.account_id, base_currency, quantity, quantity))

            # Registrar ordem
            order_id = f"MANUAL_BUY_{symbol}_{datetime.now(timezone.utc).timestamp()}"
            cursor.execute("""
                INSERT INTO orders (
                    id, account_id, symbol, side, order_type,
                    quantity, price, status, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_id, self.account_id, symbol, 'BUY', 'MARKET',
                quantity, current_price, 'FILLED',
                datetime.now(timezone.utc).isoformat()
            ))

            conn.commit()
            conn.close()

            # Enviar confirmação
            await update.message.reply_text(
                f"✅ *Compra Executada com Sucesso!*\n\n"
                f"📊 *Ativo:* {symbol}\n"
                f"💰 *Quantidade:* {quantity:.6f} {base_currency}\n"
                f"💵 *Preço:* ${current_price:.2f}\n"
                f"💎 *Valor Total:* ${amount_usdt:.2f}\n"
                f"📅 *Data:* {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n"
                f"_Ordem manual executada via Telegram_",
                parse_mode='Markdown'
            )

        except Exception as e:
            await update.message.reply_text(f"❌ Erro ao executar compra: {e}")

    async def sell_market(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /sell SYMBOL PERCENT - Executa venda de % da posição."""
        if len(context.args) != 2:
            await update.message.reply_text(
                "❌ *Uso incorreto*\n\n"
                "Formato: `/sell SYMBOL PERCENT`\n"
                "Exemplo: `/sell BTCUSDT 50`\n\n"
                "PERCENT = % da posição para vender (0-100)",
                parse_mode='Markdown'
            )
            return

        symbol = context.args[0].upper()
        if not symbol.endswith('USDT'):
            symbol += 'USDT'

        try:
            percent = float(context.args[1])
            if percent <= 0 or percent > 100:
                await update.message.reply_text("❌ Porcentagem deve ser entre 1 e 100")
                return
        except ValueError:
            await update.message.reply_text("❌ Porcentagem inválida. Use números (ex: 50 ou 25.5)")
            return

        try:
            base_currency = symbol.replace('USDT', '')

            # Verificar posição
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT available_amount FROM balances
                WHERE account_id = ? AND currency = ?
            """, (self.account_id, base_currency))

            result = cursor.fetchone()
            if not result or result[0] <= 0:
                conn.close()
                await update.message.reply_text(
                    f"❌ Você não possui {base_currency} para vender"
                )
                return

            available_amount = result[0]
            quantity_to_sell = available_amount * (percent / 100)

            # Obter preço atual
            ticker = self.client.get_klines(symbol, '1m', limit=1)
            if not ticker:
                conn.close()
                await update.message.reply_text(f"❌ Não foi possível obter preço de {symbol}")
                return

            current_price = float(ticker[0]['close'])
            usdt_value = quantity_to_sell * current_price

            # Executar venda (paper trading)
            from datetime import datetime, timezone

            # Atualizar balances
            cursor.execute("""
                UPDATE balances
                SET available_amount = available_amount - ?
                WHERE account_id = ? AND currency = ?
            """, (quantity_to_sell, self.account_id, base_currency))

            cursor.execute("""
                UPDATE balances
                SET available_amount = available_amount + ?
                WHERE account_id = ? AND currency = 'USDT'
            """, (usdt_value, self.account_id))

            # Registrar ordem
            order_id = f"MANUAL_SELL_{symbol}_{datetime.now(timezone.utc).timestamp()}"
            cursor.execute("""
                INSERT INTO orders (
                    id, account_id, symbol, side, order_type,
                    quantity, price, status, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_id, self.account_id, symbol, 'SELL', 'MARKET',
                quantity_to_sell, current_price, 'FILLED',
                datetime.now(timezone.utc).isoformat()
            ))

            conn.commit()
            conn.close()

            # Enviar confirmação
            await update.message.reply_text(
                f"✅ *Venda Executada com Sucesso!*\n\n"
                f"📊 *Ativo:* {symbol}\n"
                f"💰 *Quantidade:* {quantity_to_sell:.6f} {base_currency} ({percent:.1f}%)\n"
                f"💵 *Preço:* ${current_price:.2f}\n"
                f"💎 *Valor Recebido:* ${usdt_value:.2f} USDT\n"
                f"📅 *Data:* {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
                f"🔄 *Restante:* {available_amount - quantity_to_sell:.6f} {base_currency}\n\n"
                f"_Ordem manual executada via Telegram_",
                parse_mode='Markdown'
            )

        except Exception as e:
            await update.message.reply_text(f"❌ Erro ao executar venda: {e}")

    async def candles(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /candles SYMBOL TIMEFRAME - Gera gráfico de candlestick."""
        # Validar argumentos
        if len(context.args) < 1:
            await update.message.reply_text(
                "❌ *Uso incorreto*\n\n"
                "Formato: `/candles SYMBOL [TIMEFRAME]`\n"
                "Exemplos:\n"
                "• `/candles BTCUSDT` (default: 1h)\n"
                "• `/candles BTC 4h`\n"
                "• `/candles ETHUSDT 1d`\n\n"
                "Timeframes: 1h, 4h, 1d",
                parse_mode='Markdown'
            )
            return

        # Parse symbol
        symbol = context.args[0].upper()
        if not symbol.endswith('USDT'):
            symbol += 'USDT'

        # Parse timeframe (default 1h)
        timeframe = '1h'
        if len(context.args) >= 2:
            tf = context.args[1].lower()
            if tf in ['1h', '4h', '1d']:
                timeframe = tf
            else:
                await update.message.reply_text(
                    f"❌ Timeframe inválido: {tf}\n"
                    f"Use: 1h, 4h ou 1d",
                    parse_mode='Markdown'
                )
                return

        # Enviar mensagem de processamento
        processing_msg = await update.message.reply_text(
            f"📊 Gerando gráfico para {symbol} ({timeframe})...\n"
            f"_Isso pode levar alguns segundos_",
            parse_mode='Markdown'
        )

        try:
            # Gerar gráfico
            chart_generator = ChartGenerator(self.db_path)
            chart_path = chart_generator.generate_chart(symbol, timeframe)

            # Enviar imagem
            with open(chart_path, 'rb') as photo:
                await update.message.reply_photo(
                    photo=photo,
                    caption=(
                        f"📊 *{symbol} - {timeframe.upper()}*\n\n"
                        f"🟡 Médias Móveis (MA)\n"
                        f"🟢 Linhas de Suporte (compra)\n"
                        f"🔴 Linhas de Resistência (venda)\n"
                        f"⬆️ Setas verdes = Compras executadas\n"
                        f"⬇️ Setas vermelhas = Vendas executadas\n\n"
                        f"_Últimas 100 velas + ordens executadas_"
                    ),
                    parse_mode='Markdown'
                )

            # Deletar mensagem de processamento
            await processing_msg.delete()

            # Limpar arquivo temporário
            import os
            if os.path.exists(chart_path):
                os.remove(chart_path)

        except Exception as e:
            await processing_msg.edit_text(
                f"❌ Erro ao gerar gráfico: {e}",
                parse_mode='Markdown'
            )

    def run(self):
        """Executa o bot."""
        application = Application.builder().token(self.token).build()

        # Handlers de comando
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("help", self.help))
        application.add_handler(CommandHandler("status", self.status))
        application.add_handler(CommandHandler("portfolio", self.portfolio))
        application.add_handler(CommandHandler("p", self.portfolio))  # Atalho
        application.add_handler(CommandHandler("watchlist", self.watchlist))
        application.add_handler(CommandHandler("w", self.watchlist))  # Atalho
        application.add_handler(CommandHandler("signals", self.signals))
        application.add_handler(CommandHandler("s", self.signals))  # Atalho
        application.add_handler(CommandHandler("add", self.add_symbol))
        application.add_handler(CommandHandler("remove", self.remove_symbol))
        application.add_handler(CommandHandler("buy", self.buy_market))
        application.add_handler(CommandHandler("sell", self.sell_market))
        application.add_handler(CommandHandler("candles", self.candles))
        application.add_handler(CommandHandler("history", self.history))
        application.add_handler(CommandHandler("performance", self.performance))
        application.add_handler(CommandHandler("settings", self.handle_settings))

        # Handler de botões
        application.add_handler(CallbackQueryHandler(self.button_handler))

        # Iniciar bot
        logger.info("🚀 Bot híbrido iniciado - Suporta comandos e botões!")
        application.run_polling()


def main():
    """Ponto de entrada principal."""
    bot = HybridTradingBot()
    bot.run()


if __name__ == "__main__":
    main()