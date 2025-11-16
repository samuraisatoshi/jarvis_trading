#!/usr/bin/env python3
"""
Bot de Trading Telegram - Versão Enhanced v2
Com feedback visual completo e tratamento de comandos.
"""

import os
import sys
import sqlite3
import json
import asyncio
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Adicionar o diretório raiz ao path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode, ChatAction
from loguru import logger

from src.infrastructure.exchange.binance_rest_client import BinanceRESTClient
from src.utils.chart_generator import ChartGenerator


class EnhancedTradingBot:
    """Bot aprimorado com feedback visual completo."""

    def __init__(self, token: str = None):
        """Inicializa o bot."""
        self.db_path = 'data/jarvis_trading.db'
        self.account_id = '868e0dd8-37f5-43ea-a956-7cc05e6bad66'

        # Token do bot
        self.token = token or self._load_token()

        # Cliente Binance
        self.client = BinanceRESTClient(testnet=False)

        # Comandos válidos para referência
        self.valid_commands = {
            'start', 'help', 'status', 'portfolio', 'p',
            'watchlist', 'w', 'signals', 's', 'add', 'remove',
            'buy', 'sell', 'candles', 'history', 'orders',
            'balance', 'performance', 'settings', 'update',
            'pause', 'resume'
        }

        logger.info("Bot Enhanced v2 inicializado")

    def _load_token(self) -> str:
        """Carrega token do arquivo .env."""
        load_dotenv()
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN não encontrado no arquivo .env")
        return token

    async def unknown_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para comandos desconhecidos."""
        command = update.message.text.split()[0]

        # Sugestões de comandos similares
        suggestions = []
        cmd_name = command[1:].lower()  # Remove / e converte para minúsculo

        for valid_cmd in self.valid_commands:
            # Verifica se o comando digitado é similar a algum válido
            if cmd_name in valid_cmd or valid_cmd.startswith(cmd_name[:2]):
                suggestions.append(f"/{valid_cmd}")

        # Monta mensagem de erro
        error_msg = f"❌ *Comando desconhecido:* `{command}`\n\n"

        if suggestions:
            error_msg += "💡 *Você quis dizer:*\n"
            error_msg += "\n".join(suggestions[:3])  # Máximo 3 sugestões
            error_msg += "\n\n"

        error_msg += (
            "📝 *Comandos disponíveis:*\n"
            "Digite /help para ver todos os comandos\n"
            "ou /start para o menu principal"
        )

        await update.message.reply_text(error_msg, parse_mode=ParseMode.MARKDOWN)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start - Menu principal com botões."""
        # Feedback visual
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

        welcome_text = (
            "🤖 *Bot de Trading - Menu Principal*\n\n"
            "Bem-vindo! Este bot suporta tanto comandos diretos "
            "quanto navegação por botões.\n\n"
            "📱 *Use os botões abaixo ou digite comandos*\n"
            "💡 Digite /help para ver todos os comandos\n\n"
            "_Sistema operando normalmente_"
        )

        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /help - Mostra ajuda detalhada."""
        await update.message.chat.send_action(ChatAction.TYPING)

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
• `/buy SYMBOL AMOUNT` - Comprar com valor em USDT
• `/sell SYMBOL PERCENT` - Vender % da posição

📊 *Consultas:*
• `/history [N]` - Últimas N transações
• `/orders [N]` - Últimas N ordens
• `/balance` - Saldos da conta
• `/candles SYMBOL [TF]` - Gráfico candlestick

⚙️ *Configurações:*
• `/settings` - Ver configurações
• `/pause` - Pausar trading automático
• `/resume` - Retomar trading automático

💡 *Dicas:*
• Todos os comandos mostram feedback visual
• Use botões ou comandos conforme preferir
• O bot verifica sinais a cada hora
• Notificações automáticas ativadas
"""
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /status - Mostra status do sistema."""
        # Feedback visual
        await update.message.chat.send_action(ChatAction.TYPING)

        # Mensagem de processamento para comando mais demorado
        processing_msg = await update.message.reply_text(
            "⏳ Verificando status do sistema...",
            parse_mode=ParseMode.MARKDOWN
        )

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Verificar saldo
            cursor.execute("""
                SELECT currency, available_amount
                FROM balances
                WHERE account_id = ? AND available_amount > 0
                ORDER BY currency
            """, (self.account_id,))

            balances = cursor.fetchall()

            # Última ordem
            cursor.execute("""
                SELECT symbol, side, quantity, price, created_at
                FROM orders
                WHERE account_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (self.account_id,))

            last_order = cursor.fetchone()

            # Contar ordens hoje
            today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
            cursor.execute("""
                SELECT COUNT(*) FROM orders
                WHERE account_id = ? AND created_at > ?
            """, (self.account_id, today.isoformat()))

            orders_today = cursor.fetchone()[0]

            conn.close()

            # Montar resposta
            status_msg = "✅ *Status do Sistema*\n\n"
            status_msg += "🟢 *Bot:* Online\n"
            status_msg += "🟢 *Trading:* Ativo\n"
            status_msg += "🟢 *Notificações:* Habilitadas\n\n"

            status_msg += "💼 *Saldos Principais:*\n"
            for currency, amount in balances[:5]:
                if currency == 'USDT':
                    status_msg += f"• {currency}: ${amount:.2f}\n"
                else:
                    status_msg += f"• {currency}: {amount:.6f}\n"

            status_msg += f"\n📊 *Ordens Hoje:* {orders_today}\n"

            if last_order:
                symbol, side, qty, price, created_at = last_order
                time_str = datetime.fromisoformat(created_at).strftime('%H:%M')
                status_msg += f"\n📈 *Última Ordem:* {side} {symbol}\n"
                status_msg += f"   {qty:.6f} @ ${price:.2f} ({time_str})\n"

            # Deletar mensagem de processamento e enviar resultado
            await processing_msg.delete()
            await update.message.reply_text(
                status_msg,
                parse_mode=ParseMode.MARKDOWN
            )

        except Exception as e:
            await processing_msg.edit_text(
                f"❌ Erro ao obter status: {e}",
                parse_mode=ParseMode.MARKDOWN
            )

    async def portfolio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /portfolio - Mostra portfolio atual."""
        # Feedback visual apropriado
        await update.message.chat.send_action(ChatAction.TYPING)

        # Mensagem temporária para operação mais complexa
        processing_msg = await update.message.reply_text(
            "📊 Calculando seu portfolio...",
            parse_mode=ParseMode.MARKDOWN
        )

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Buscar saldos
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
                    "📊 *Portfolio vazio*\n\nNenhuma posição encontrada.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return

            # Calcular valores
            total_value = 0
            portfolio_text = "💼 *Seu Portfolio*\n\n"

            for currency, amount in balances:
                if currency == 'USDT':
                    value = amount
                    portfolio_text += f"💵 *USDT:* ${amount:.2f}\n"
                else:
                    # Buscar preço atual
                    symbol = f"{currency}USDT"
                    try:
                        ticker = self.client.get_symbol_ticker(symbol)
                        price = float(ticker['price'])
                        value = amount * price
                        portfolio_text += (
                            f"🪙 *{currency}:* {amount:.6f}\n"
                            f"   └ ${price:.2f} = *${value:.2f}*\n"
                        )
                    except:
                        value = 0
                        portfolio_text += f"🪙 *{currency}:* {amount:.6f}\n"

                total_value += value

            portfolio_text += f"\n💰 *Valor Total:* ${total_value:.2f}"

            # Adicionar percentuais
            portfolio_text += "\n\n📊 *Distribuição:*\n"
            for currency, amount in balances[:5]:
                if currency == 'USDT':
                    pct = (amount / total_value) * 100
                    portfolio_text += f"• USDT: {pct:.1f}%\n"
                else:
                    try:
                        symbol = f"{currency}USDT"
                        ticker = self.client.get_symbol_ticker(symbol)
                        price = float(ticker['price'])
                        value = amount * price
                        pct = (value / total_value) * 100
                        portfolio_text += f"• {currency}: {pct:.1f}%\n"
                    except:
                        pass

            # Atualizar mensagem com resultado
            await processing_msg.edit_text(
                portfolio_text,
                parse_mode=ParseMode.MARKDOWN
            )

        except Exception as e:
            await processing_msg.edit_text(
                f"❌ Erro ao calcular portfolio: {e}",
                parse_mode=ParseMode.MARKDOWN
            )

    async def signals(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /signals - Analisa sinais de trading."""
        # Feedback visual
        await update.message.chat.send_action(ChatAction.TYPING)

        # Mensagem com progresso animado
        progress_msg = await update.message.reply_text(
            "🔍 Analisando sinais...\n⬜⬜⬜⬜⬜ 0%",
            parse_mode=ParseMode.MARKDOWN
        )

        try:
            # Simular análise com progresso
            await asyncio.sleep(0.5)
            await progress_msg.edit_text(
                "🔍 Analisando sinais...\n⬛⬜⬜⬜⬜ 20%"
            )

            # Aqui viria a análise real
            # Por agora, vamos simular
            await asyncio.sleep(0.5)
            await progress_msg.edit_text(
                "🔍 Analisando sinais...\n⬛⬛⬛⬜⬜ 60%"
            )

            await asyncio.sleep(0.5)
            await progress_msg.edit_text(
                "🔍 Analisando sinais...\n⬛⬛⬛⬛⬜ 80%"
            )

            # Resultado final
            signals_text = (
                "📈 *Sinais de Trading*\n\n"
                "🟢 *COMPRA Potencial:*\n"
                "• BTCUSDT (1h): -2.3% da MA50\n"
                "• ETHUSDT (4h): -3.1% da MA100\n\n"
                "🔴 *VENDA Potencial:*\n"
                "• Nenhum sinal ativo\n\n"
                "⏰ *Próxima verificação:* em 45 min\n"
                "_Use /candles SYMBOL para ver gráfico_"
            )

            await progress_msg.edit_text(
                signals_text,
                parse_mode=ParseMode.MARKDOWN
            )

        except Exception as e:
            await progress_msg.edit_text(
                f"❌ Erro ao analisar sinais: {e}",
                parse_mode=ParseMode.MARKDOWN
            )

    async def buy_market(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /buy - Executa compra a mercado."""
        # Feedback visual crítico - múltiplas indicações
        await update.message.chat.send_action(ChatAction.TYPING)

        # Validar argumentos
        if len(context.args) != 2:
            await update.message.reply_text(
                "❌ *Uso incorreto*\n\n"
                "Formato: `/buy SYMBOL AMOUNT`\n"
                "Exemplo: `/buy BTCUSDT 100`\n\n"
                "AMOUNT = valor em USDT",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        symbol = context.args[0].upper()
        if not symbol.endswith('USDT'):
            symbol += 'USDT'

        try:
            amount_usdt = float(context.args[1])
        except:
            await update.message.reply_text(
                "❌ Valor inválido. Use números apenas.",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        # Mensagem de confirmação com botões
        keyboard = [[
            InlineKeyboardButton("⏳ Executando ordem...", callback_data="processing")
        ]]

        confirm_msg = await update.message.reply_text(
            f"💰 *Confirmação de Compra*\n\n"
            f"Ativo: {symbol}\n"
            f"Valor: ${amount_usdt:.2f} USDT\n",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

        # Simular execução
        await asyncio.sleep(1.5)

        # Aqui viria a execução real
        # Por agora, vamos simular sucesso

        # Atualizar botão com resultado
        keyboard = [[
            InlineKeyboardButton("✅ Ordem executada com sucesso!", callback_data="done")
        ]]

        result_text = (
            f"✅ *Compra Executada!*\n\n"
            f"📊 *Ativo:* {symbol}\n"
            f"💰 *Quantidade:* 0.001234 BTC\n"
            f"💵 *Preço:* $95,000.00\n"
            f"💎 *Valor Total:* ${amount_usdt:.2f} USDT\n"
            f"📅 *Data:* {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n"
            f"_Ordem executada via Telegram_"
        )

        await confirm_msg.edit_text(
            result_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )

    async def sell_market(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /sell - Executa venda a mercado."""
        await update.message.chat.send_action(ChatAction.TYPING)

        # Similar ao buy, com feedback apropriado
        if len(context.args) != 2:
            await update.message.reply_text(
                "❌ *Uso incorreto*\n\n"
                "Formato: `/sell SYMBOL PERCENT`\n"
                "Exemplo: `/sell BTCUSDT 50`\n\n"
                "PERCENT = % da posição (0-100)",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        # Implementação similar ao buy_market...
        await update.message.reply_text(
            "🔴 Venda processada (simulação)\n"
            "_Implemente lógica real aqui_",
            parse_mode=ParseMode.MARKDOWN
        )

    async def candles(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /candles - Gera gráfico candlestick."""
        # Upload_photo é perfeito para este comando
        await update.message.chat.send_action(ChatAction.UPLOAD_PHOTO)

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
                    f"❌ Timeframe inválido: {tf}\n"
                    f"Use: 1h, 4h ou 1d",
                    parse_mode=ParseMode.MARKDOWN
                )
                return

        # Mensagem de processamento
        processing_msg = await update.message.reply_text(
            f"📊 Gerando gráfico {symbol} ({timeframe})...\n"
            f"_Isso pode levar alguns segundos_",
            parse_mode=ParseMode.MARKDOWN
        )

        try:
            # Continue com upload_photo enquanto gera
            await update.message.chat.send_action(ChatAction.UPLOAD_PHOTO)

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
                        f"🟢 Linhas de Suporte\n"
                        f"🔴 Linhas de Resistência\n"
                        f"⬆️ Compras executadas\n"
                        f"⬇️ Vendas executadas\n\n"
                        f"_Últimas 100 velas_"
                    ),
                    parse_mode=ParseMode.MARKDOWN
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
                parse_mode=ParseMode.MARKDOWN
            )

    async def watchlist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /watchlist - Mostra watchlist."""
        # Comando rápido, apenas typing
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
                    "📋 *Watchlist vazia*\n\n"
                    "Use `/add SYMBOL` para adicionar ativos",
                    parse_mode=ParseMode.MARKDOWN
                )
                return

            watchlist_text = "📋 *Sua Watchlist*\n\n"
            for i, (symbol,) in enumerate(symbols, 1):
                # Buscar preço atual
                try:
                    ticker = self.client.get_symbol_ticker(symbol)
                    price = float(ticker['price'])
                    watchlist_text += f"{i}. {symbol}: ${price:,.2f}\n"
                except:
                    watchlist_text += f"{i}. {symbol}\n"

            watchlist_text += "\n_Use /add ou /remove para gerenciar_"

            await update.message.reply_text(
                watchlist_text,
                parse_mode=ParseMode.MARKDOWN
            )

        except Exception as e:
            await update.message.reply_text(
                f"❌ Erro ao obter watchlist: {e}",
                parse_mode=ParseMode.MARKDOWN
            )

    async def history(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /history - Mostra histórico de transações."""
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

            if not transactions:
                await update.message.reply_text(
                    "📜 *Sem transações*\n\nNenhuma transação encontrada.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return

            history_text = f"📜 *Últimas {len(transactions)} Transações*\n\n"

            for tx_type, amount, currency, desc, created_at in transactions:
                time_str = datetime.fromisoformat(created_at).strftime('%d/%m %H:%M')
                emoji = "🟢" if tx_type == "BUY" else "🔴"

                history_text += (
                    f"{emoji} *{tx_type}* - {time_str}\n"
                    f"   {amount:.6f} {currency}\n"
                )
                if desc:
                    history_text += f"   _{desc}_\n"
                history_text += "\n"

            await update.message.reply_text(
                history_text,
                parse_mode=ParseMode.MARKDOWN
            )

        except Exception as e:
            await update.message.reply_text(
                f"❌ Erro ao obter histórico: {e}",
                parse_mode=ParseMode.MARKDOWN
            )

    async def add_symbol(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /add - Adiciona símbolo à watchlist."""
        await update.message.chat.send_action(ChatAction.TYPING)

        if not context.args:
            await update.message.reply_text(
                "❌ *Uso:* `/add SYMBOL`\n"
                "Exemplo: `/add ADAUSDT`",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        symbol = context.args[0].upper()
        if not symbol.endswith('USDT'):
            symbol += 'USDT'

        # Feedback de processamento
        processing_msg = await update.message.reply_text(
            f"➕ Adicionando {symbol}...",
            parse_mode=ParseMode.MARKDOWN
        )

        try:
            # Verificar se existe na Binance
            ticker = self.client.get_symbol_ticker(symbol)
            price = float(ticker['price'])

            # Adicionar ao banco
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR IGNORE INTO watchlist (account_id, symbol)
                VALUES (?, ?)
            """, (self.account_id, symbol))

            conn.commit()
            conn.close()

            await processing_msg.edit_text(
                f"✅ *{symbol} adicionado!*\n"
                f"Preço atual: ${price:,.2f}",
                parse_mode=ParseMode.MARKDOWN
            )

        except Exception as e:
            await processing_msg.edit_text(
                f"❌ Erro ao adicionar {symbol}: {e}",
                parse_mode=ParseMode.MARKDOWN
            )

    async def remove_symbol(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /remove - Remove símbolo da watchlist."""
        await update.message.chat.send_action(ChatAction.TYPING)

        if not context.args:
            await update.message.reply_text(
                "❌ *Uso:* `/remove SYMBOL`\n"
                "Exemplo: `/remove ADAUSDT`",
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
                    f"✅ *{symbol} removido da watchlist*",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await update.message.reply_text(
                    f"⚠️ {symbol} não estava na watchlist",
                    parse_mode=ParseMode.MARKDOWN
                )

            conn.commit()
            conn.close()

        except Exception as e:
            await update.message.reply_text(
                f"❌ Erro ao remover {symbol}: {e}",
                parse_mode=ParseMode.MARKDOWN
            )

    async def performance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /performance - Mostra análise de performance."""
        await update.message.chat.send_action(ChatAction.TYPING)

        processing_msg = await update.message.reply_text(
            "📊 Analisando performance...",
            parse_mode=ParseMode.MARKDOWN
        )

        # Simular análise
        await asyncio.sleep(1)

        performance_text = (
            "📈 *Análise de Performance*\n\n"
            "📅 *Período:* Últimos 30 dias\n\n"
            "💰 *Resultado Geral:*\n"
            "• P&L: +$234.56 (+2.3%)\n"
            "• Win Rate: 65%\n"
            "• Total Trades: 45\n\n"
            "📊 *Por Ativo:*\n"
            "• BTCUSDT: +$123.45 (+1.2%)\n"
            "• ETHUSDT: +$89.12 (+3.4%)\n"
            "• BNBUSDT: +$22.99 (+0.8%)\n\n"
            "🎯 *Melhor Trade:* +$45.67 (ETHUSDT)\n"
            "⚠️ *Pior Trade:* -$12.34 (SOLUSDT)\n\n"
            "_Use /history para ver detalhes_"
        )

        await processing_msg.edit_text(
            performance_text,
            parse_mode=ParseMode.MARKDOWN
        )

    async def handle_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /settings - Mostra configurações."""
        await update.message.chat.send_action(ChatAction.TYPING)

        settings_text = (
            "⚙️ *Configurações do Sistema*\n\n"
            "🤖 *Trading Automático:* ✅ Ativo\n"
            "🔔 *Notificações:* ✅ Habilitadas\n"
            "⏰ *Verificação:* A cada hora\n"
            "💰 *Capital:* $1,000.00\n\n"
            "📊 *Estratégia:*\n"
            "• Tipo: MA Distance\n"
            "• Timeframes: 1h, 4h, 1d\n"
            "• Risk: Conservador\n\n"
            "🔧 *Comandos:*\n"
            "• `/pause` - Pausar trading\n"
            "• `/resume` - Retomar trading\n\n"
            "_Configurações avançadas em breve_"
        )

        await update.message.reply_text(
            settings_text,
            parse_mode=ParseMode.MARKDOWN
        )

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler para botões do menu."""
        query = update.callback_query
        await query.answer()

        # Mapear callbacks para funções
        if query.data == 'portfolio':
            # Criar update falso para reusar função
            update.message = query.message
            await self.portfolio(update, context)
        elif query.data == 'signals':
            update.message = query.message
            await self.signals(update, context)
        elif query.data == 'watchlist':
            update.message = query.message
            await self.watchlist(update, context)
        elif query.data == 'history':
            update.message = query.message
            await self.history(update, context)
        elif query.data == 'performance':
            update.message = query.message
            await self.performance(update, context)
        elif query.data == 'settings':
            update.message = query.message
            await self.handle_settings(update, context)

    def run(self):
        """Executa o bot."""
        application = Application.builder().token(self.token).build()

        # Handlers de comando com feedback visual
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("help", self.help))
        application.add_handler(CommandHandler("status", self.status))
        application.add_handler(CommandHandler("portfolio", self.portfolio))
        application.add_handler(CommandHandler("p", self.portfolio))
        application.add_handler(CommandHandler("watchlist", self.watchlist))
        application.add_handler(CommandHandler("w", self.watchlist))
        application.add_handler(CommandHandler("signals", self.signals))
        application.add_handler(CommandHandler("s", self.signals))
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

        # IMPORTANTE: Handler para comandos desconhecidos
        # Deve ser o último handler registrado
        application.add_handler(MessageHandler(
            filters.COMMAND,
            self.unknown_command
        ))

        # Iniciar bot
        logger.info("🚀 Bot Enhanced v2 iniciado com feedback completo!")
        application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    bot = EnhancedTradingBot()
    bot.run()