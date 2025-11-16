"""
Helper simplificado para notificações Telegram no daemon de trading.
"""

import os
from typing import Optional, Dict
from datetime import datetime
from dotenv import load_dotenv
from loguru import logger

from .telegram_notifier import TelegramNotifier


class TradingTelegramNotifier:
    """Adaptador simplificado do TelegramNotifier para trading."""

    def __init__(self):
        """Inicializa o notificador."""
        load_dotenv()

        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')

        if not self.bot_token or not self.chat_id:
            raise ValueError("TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID são obrigatórios no .env")

        # Usar o notificador existente
        self.notifier = TelegramNotifier(
            bot_token=self.bot_token,
            chat_id=self.chat_id,
            parse_mode="Markdown"
        )

        logger.info(f"Trading Telegram Notifier inicializado")

    def notify_trade_executed(self, trade_type: str, symbol: str, quantity: float,
                            price: float, timeframe: str, reason: str = None) -> bool:
        """Notifica execução de trade com formatação rica."""
        emoji = "🟢" if trade_type == "BUY" else "🔴"
        total_value = quantity * price

        message = (
            f"{emoji} *{trade_type} Order Executada*\n\n"
            f"📊 *Ativo:* {symbol}\n"
            f"💰 *Quantidade:* {quantity:.6f}\n"
            f"💵 *Preço:* ${price:.2f}\n"
            f"💎 *Valor Total:* ${total_value:.2f}\n"
            f"⏰ *Timeframe:* {timeframe}\n"
            f"📅 *Data/Hora:* {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
        )

        if reason:
            message += f"\n📝 *Motivo:* {reason}"

        # Adicionar resumo de performance se for SELL
        if trade_type == "SELL":
            message += "\n\n💹 *Performance será calculada*"

        return self.notifier.send_message(message)

    def notify_signals_found(self, signals: list) -> bool:
        """Notifica quando sinais são encontrados."""
        if not signals:
            return False

        message = f"📡 *{len(signals)} Sinais Ativos Detectados*\n\n"

        # Agrupar por ação
        buy_signals = [s for s in signals if s['action'] == 'BUY']
        sell_signals = [s for s in signals if s['action'] == 'SELL']

        if buy_signals:
            message += "🟢 *Sinais de COMPRA:*\n"
            for signal in buy_signals[:3]:  # Máximo 3
                message += (
                    f"• {signal['symbol']} ({signal['timeframe']}): "
                    f"{signal['distance']:.1f}%\n"
                )
            if len(buy_signals) > 3:
                message += f"  _...e {len(buy_signals) - 3} mais_\n"

        if sell_signals:
            message += "\n🔴 *Sinais de VENDA:*\n"
            for signal in sell_signals[:3]:
                message += (
                    f"• {signal['symbol']} ({signal['timeframe']}): "
                    f"{signal['distance']:.1f}%\n"
                )
            if len(sell_signals) > 3:
                message += f"  _...e {len(sell_signals) - 3} mais_\n"

        message += "\n_Daemon analisando sinais..._"

        return self.notifier.send_message(message)

    def notify_portfolio_status(self, portfolio: Dict) -> bool:
        """Notifica status do portfolio após trades."""
        message = "💼 *Portfolio Atualizado*\n\n"

        # Valor total
        total_value = portfolio.get('total_value', 0)
        message += f"💰 *Valor Total:* ${total_value:.2f}\n\n"

        # USDT disponível
        usdt_balance = portfolio.get('usdt_balance', 0)
        message += f"💵 *USDT Disponível:* ${usdt_balance:.2f}\n"

        # Posições
        positions = portfolio.get('positions', {})
        if positions:
            message += "\n📊 *Posições Ativas:*\n"
            for currency, info in positions.items():
                if info['quantity'] > 0:
                    value = info.get('value', 0)
                    message += f"• *{currency}:* {info['quantity']:.6f} (${value:.2f})\n"

        # Trades hoje
        trades_today = portfolio.get('trades_today', 0)
        if trades_today:
            message += f"\n📈 *Trades Hoje:* {trades_today}"

        return self.notifier.send_message(message)

    def notify_daemon_started(self, watchlist: list, capital: float) -> bool:
        """Notifica quando o daemon inicia."""
        message = (
            "🚀 *Trading Daemon Iniciado*\n\n"
            f"💰 *Capital:* ${capital:.2f}\n"
            f"📋 *Watchlist:* {', '.join(watchlist)}\n"
            f"⏰ *Verificação:* A cada hora\n"
            f"📊 *Timeframes:* 1h, 4h, 1d\n\n"
            "_Você receberá notificações automáticas quando trades forem executados_"
        )

        return self.notifier.send_message(message)

    def notify_daemon_stopped(self, reason: str = None) -> bool:
        """Notifica quando o daemon para."""
        message = "🛑 *Trading Daemon Parado*"

        if reason:
            message += f"\n\n📝 *Motivo:* {reason}"

        return self.notifier.send_message(message)

    def notify_error(self, error_msg: str) -> bool:
        """Notifica erro crítico."""
        message = (
            "❌ *Erro no Trading Daemon*\n\n"
            f"📝 *Detalhes:* {error_msg}\n\n"
            "_Verifique os logs para mais informações_"
        )

        return self.notifier.send_message(message)

    def send_message(self, message: str) -> bool:
        """Envia mensagem direta ao Telegram."""
        return self.notifier.send_message(message)

    def notify_daily_summary(self, summary: Dict) -> bool:
        """Envia resumo diário."""
        message = (
            "📊 *Resumo Diário de Trading*\n"
            f"📅 *Data:* {datetime.now().strftime('%d/%m/%Y')}\n\n"
        )

        # Trades executados
        total_trades = summary.get('total_trades', 0)
        buy_trades = summary.get('buy_trades', 0)
        sell_trades = summary.get('sell_trades', 0)

        message += (
            f"📈 *Trades Executados:* {total_trades}\n"
            f"  🟢 Compras: {buy_trades}\n"
            f"  🔴 Vendas: {sell_trades}\n\n"
        )

        # Performance
        pnl = summary.get('pnl', 0)
        pnl_percent = summary.get('pnl_percent', 0)
        emoji_pnl = "📈" if pnl >= 0 else "📉"

        message += (
            f"{emoji_pnl} *P&L do Dia:*\n"
            f"  Valor: ${pnl:+.2f}\n"
            f"  Percentual: {pnl_percent:+.2f}%\n\n"
        )

        # Portfolio
        total_value = summary.get('total_value', 0)
        message += f"💰 *Valor Total do Portfolio:* ${total_value:.2f}"

        return self.notifier.send_message(message)