"""
Message Templates for Trading Notifications

Provides pre-formatted message templates for various trading events.
Supports both Markdown and HTML formatting.

Template types:
- System events (startup, shutdown, errors)
- Market analysis (signals, indicators)
- Trade execution (buy, sell, hold)
- Performance reports (daily, weekly, monthly)
- Alerts (circuit breaker, risk limits, anomalies)
"""

from datetime import datetime
from typing import Dict, Optional
from enum import Enum


class MessageFormat(Enum):
    """Message formatting options."""

    MARKDOWN = "Markdown"
    MARKDOWNV2 = "MarkdownV2"
    HTML = "HTML"


class TradingMessageTemplates:
    """
    Trading message templates for Telegram notifications.

    All methods return formatted strings ready to send via TelegramNotifier.
    """

    @staticmethod
    def _escape_markdown_v2(text: str) -> str:
        """Escape special characters for MarkdownV2."""
        special_chars = [
            "_",
            "*",
            "[",
            "]",
            "(",
            ")",
            "~",
            "`",
            ">",
            "#",
            "+",
            "-",
            "=",
            "|",
            "{",
            "}",
            ".",
            "!",
        ]
        for char in special_chars:
            text = text.replace(char, f"\\{char}")
        return text

    @classmethod
    def system_startup(
        cls,
        symbol: str,
        timeframe: str,
        account_id: str,
        initial_balance: float,
        format: MessageFormat = MessageFormat.MARKDOWNV2,
    ) -> str:
        """System startup notification."""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

        if format == MessageFormat.MARKDOWNV2:
            symbol_esc = cls._escape_markdown_v2(symbol)
            timeframe_esc = cls._escape_markdown_v2(timeframe)
            timestamp_esc = cls._escape_markdown_v2(timestamp)

            return (
                f"🚀 *SISTEMA INICIADO*\n\n"
                f"📊 *Par:* {symbol_esc}\n"
                f"⏰ *Timeframe:* {timeframe_esc}\n"
                f"💰 *Saldo inicial:* ${initial_balance:,.2f} USDT\n"
                f"🆔 *Conta:* `{account_id}`\n\n"
                f"✅ Sistema operacional e monitorando mercado\n"
                f"⏰ {timestamp_esc}"
            )
        else:
            return (
                f"🚀 <b>SISTEMA INICIADO</b>\n\n"
                f"📊 <b>Par:</b> {symbol}\n"
                f"⏰ <b>Timeframe:</b> {timeframe}\n"
                f"💰 <b>Saldo inicial:</b> ${initial_balance:,.2f} USDT\n"
                f"🆔 <b>Conta:</b> <code>{account_id}</code>\n\n"
                f"✅ Sistema operacional e monitorando mercado\n"
                f"⏰ {timestamp}"
            )

    @classmethod
    def market_analysis(
        cls,
        symbol: str,
        price: float,
        indicators: Dict[str, float],
        volume_change: float,
        format: MessageFormat = MessageFormat.MARKDOWNV2,
    ) -> str:
        """Market analysis notification."""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

        # Extract indicators
        rsi = indicators.get("rsi", 0)
        macd = indicators.get("macd", 0)
        macd_signal = indicators.get("macd_signal", 0)
        bb_position = indicators.get("bb_position", 50)

        # Determine market conditions
        rsi_status = "sobrevendido" if rsi < 30 else "sobrecomprado" if rsi > 70 else "neutro"
        macd_status = "alta" if macd > macd_signal else "baixa"
        volume_status = "acima" if volume_change > 0 else "abaixo"

        if format == MessageFormat.MARKDOWNV2:
            symbol_esc = cls._escape_markdown_v2(symbol)
            timestamp_esc = cls._escape_markdown_v2(timestamp)
            rsi_status_esc = cls._escape_markdown_v2(rsi_status)
            macd_status_esc = cls._escape_markdown_v2(macd_status)
            volume_status_esc = cls._escape_markdown_v2(volume_status)

            return (
                f"📊 *ANÁLISE DE MERCADO*\n\n"
                f"🪙 *Ativo:* {symbol_esc}\n"
                f"💵 *Preço:* ${price:,.2f}\n\n"
                f"📈 *Indicadores:*\n"
                f"• *RSI:* {rsi:.1f} \\({rsi_status_esc}\\)\n"
                f"• *MACD:* {macd:.2f} / {macd_signal:.2f} \\({macd_status_esc}\\)\n"
                f"• *BB Position:* {bb_position:.1f}%\n"
                f"• *Volume:* {volume_change:+.1f}% \\({volume_status_esc} média\\)\n\n"
                f"⏰ {timestamp_esc}"
            )
        else:
            return (
                f"📊 <b>ANÁLISE DE MERCADO</b>\n\n"
                f"🪙 <b>Ativo:</b> {symbol}\n"
                f"💵 <b>Preço:</b> ${price:,.2f}\n\n"
                f"📈 <b>Indicadores:</b>\n"
                f"• <b>RSI:</b> {rsi:.1f} ({rsi_status})\n"
                f"• <b>MACD:</b> {macd:.2f} / {macd_signal:.2f} ({macd_status})\n"
                f"• <b>BB Position:</b> {bb_position:.1f}%\n"
                f"• <b>Volume:</b> {volume_change:+.1f}% ({volume_status} média)\n\n"
                f"⏰ {timestamp}"
            )

    @classmethod
    def trade_signal(
        cls,
        symbol: str,
        action: str,
        confidence: float,
        price: float,
        indicators: Dict[str, float],
        reasoning: Optional[str] = None,
        format: MessageFormat = MessageFormat.MARKDOWNV2,
    ) -> str:
        """Trading signal notification."""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

        # Action emoji and color
        action_emoji = {
            "BUY": "💚",
            "SELL": "❌",
            "HOLD": "⏸️",
        }.get(action, "❓")

        # Extract key indicators
        rsi = indicators.get("rsi", 0)
        macd = indicators.get("macd", 0)
        macd_signal = indicators.get("macd_signal", 0)
        volume_change = indicators.get("volume_change_pct", 0)

        if format == MessageFormat.MARKDOWNV2:
            symbol_esc = cls._escape_markdown_v2(symbol)
            action_esc = cls._escape_markdown_v2(action)
            timestamp_esc = cls._escape_markdown_v2(timestamp)

            msg = (
                f"🎯 *SINAL DE TRADING* \\- {symbol_esc}\n\n"
                f"📊 *Análise do Modelo:*\n"
                f"• *Ação:* {action_esc} {action_emoji}\n"
                f"• *Confiança:* {confidence:.1%}\n"
                f"• *Preço atual:* ${price:,.2f}\n\n"
                f"📈 *Indicadores:*\n"
                f"• *RSI:* {rsi:.1f}\n"
                f"• *MACD:* cruzamento {cls._escape_markdown_v2('alta' if macd > macd_signal else 'baixa')}\n"
                f"• *Volume:* {volume_change:+.1f}%\n\n"
            )

            if reasoning:
                msg += f"💡 *Razão:* {cls._escape_markdown_v2(reasoning)}\n\n"

            msg += f"⏰ {timestamp_esc}"
            return msg

        else:
            msg = (
                f"🎯 <b>SINAL DE TRADING - {symbol}</b>\n\n"
                f"📊 <b>Análise do Modelo:</b>\n"
                f"• <b>Ação:</b> {action} {action_emoji}\n"
                f"• <b>Confiança:</b> {confidence:.1%}\n"
                f"• <b>Preço atual:</b> ${price:,.2f}\n\n"
                f"📈 <b>Indicadores:</b>\n"
                f"• <b>RSI:</b> {rsi:.1f}\n"
                f"• <b>MACD:</b> cruzamento {'alta' if macd > macd_signal else 'baixa'}\n"
                f"• <b>Volume:</b> {volume_change:+.1f}%\n\n"
            )

            if reasoning:
                msg += f"💡 <b>Razão:</b> {reasoning}\n\n"

            msg += f"⏰ {timestamp}"
            return msg

    @classmethod
    def trade_executed(
        cls,
        trade_type: str,
        symbol: str,
        quantity: float,
        price: float,
        total_cost: float,
        new_balance_usdt: float,
        new_balance_asset: float,
        total_value: float,
        format: MessageFormat = MessageFormat.MARKDOWNV2,
    ) -> str:
        """Trade execution notification."""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

        # Extract asset symbol
        asset = symbol.split("_")[0] if "_" in symbol else symbol.replace("USDT", "")

        if format == MessageFormat.MARKDOWNV2:
            symbol_esc = cls._escape_markdown_v2(symbol)
            trade_type_esc = cls._escape_markdown_v2(trade_type)
            asset_esc = cls._escape_markdown_v2(asset)
            timestamp_esc = cls._escape_markdown_v2(timestamp)

            return (
                f"✅ *TRADE EXECUTADO*\n\n"
                f"🪙 *Ativo:* {symbol_esc}\n"
                f"📝 *Tipo:* {trade_type_esc}\n"
                f"📊 *Quantidade:* {quantity:.6f} {asset_esc}\n"
                f"💵 *Preço:* ${price:,.2f}\n"
                f"💰 *Total:* ${total_cost:,.2f} USDT\n\n"
                f"📈 *Novo Saldo:*\n"
                f"• *USDT:* ${new_balance_usdt:,.2f}\n"
                f"• *{asset_esc}:* {new_balance_asset:.6f}\n"
                f"• *Valor total:* ${total_value:,.2f}\n\n"
                f"⏰ {timestamp_esc}"
            )
        else:
            return (
                f"✅ <b>TRADE EXECUTADO</b>\n\n"
                f"🪙 <b>Ativo:</b> {symbol}\n"
                f"📝 <b>Tipo:</b> {trade_type}\n"
                f"📊 <b>Quantidade:</b> {quantity:.6f} {asset}\n"
                f"💵 <b>Preço:</b> ${price:,.2f}\n"
                f"💰 <b>Total:</b> ${total_cost:,.2f} USDT\n\n"
                f"📈 <b>Novo Saldo:</b>\n"
                f"• <b>USDT:</b> ${new_balance_usdt:,.2f}\n"
                f"• <b>{asset}:</b> {new_balance_asset:.6f}\n"
                f"• <b>Valor total:</b> ${total_value:,.2f}\n\n"
                f"⏰ {timestamp}"
            )

    @classmethod
    def circuit_breaker_triggered(
        cls,
        reason: str,
        current_drawdown: float,
        max_drawdown: float,
        format: MessageFormat = MessageFormat.MARKDOWNV2,
    ) -> str:
        """Circuit breaker alert."""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

        if format == MessageFormat.MARKDOWNV2:
            reason_esc = cls._escape_markdown_v2(reason)
            timestamp_esc = cls._escape_markdown_v2(timestamp)

            return (
                f"🚨 *CIRCUIT BREAKER ATIVADO*\n\n"
                f"⚠️ *Razão:* {reason_esc}\n"
                f"📉 *Drawdown atual:* {current_drawdown:.1%}\n"
                f"🛑 *Limite máximo:* {max_drawdown:.1%}\n\n"
                f"🔒 *Trading pausado até revisão manual*\n\n"
                f"⏰ {timestamp_esc}"
            )
        else:
            return (
                f"🚨 <b>CIRCUIT BREAKER ATIVADO</b>\n\n"
                f"⚠️ <b>Razão:</b> {reason}\n"
                f"📉 <b>Drawdown atual:</b> {current_drawdown:.1%}\n"
                f"🛑 <b>Limite máximo:</b> {max_drawdown:.1%}\n\n"
                f"🔒 <b>Trading pausado até revisão manual</b>\n\n"
                f"⏰ {timestamp}"
            )

    @classmethod
    def daily_report(
        cls,
        trades_today: int,
        wins: int,
        losses: int,
        profit_loss: float,
        profit_loss_pct: float,
        total_value: float,
        format: MessageFormat = MessageFormat.MARKDOWNV2,
    ) -> str:
        """Daily performance report."""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d")
        win_rate = (wins / trades_today * 100) if trades_today > 0 else 0
        profit_emoji = "📈" if profit_loss >= 0 else "📉"

        if format == MessageFormat.MARKDOWNV2:
            timestamp_esc = cls._escape_markdown_v2(timestamp)

            return (
                f"📊 *RELATÓRIO DIÁRIO*\n"
                f"📅 {timestamp_esc}\n\n"
                f"📝 *Trades:* {trades_today}\n"
                f"✅ *Wins:* {wins}\n"
                f"❌ *Losses:* {losses}\n"
                f"🎯 *Win Rate:* {win_rate:.1f}%\n\n"
                f"{profit_emoji} *P&L:* ${profit_loss:+,.2f} \\({profit_loss_pct:+.2f}%\\)\n"
                f"💰 *Valor total:* ${total_value:,.2f}\n"
            )
        else:
            return (
                f"📊 <b>RELATÓRIO DIÁRIO</b>\n"
                f"📅 {timestamp}\n\n"
                f"📝 <b>Trades:</b> {trades_today}\n"
                f"✅ <b>Wins:</b> {wins}\n"
                f"❌ <b>Losses:</b> {losses}\n"
                f"🎯 <b>Win Rate:</b> {win_rate:.1f}%\n\n"
                f"{profit_emoji} <b>P&L:</b> ${profit_loss:+,.2f} ({profit_loss_pct:+.2f}%)\n"
                f"💰 <b>Valor total:</b> ${total_value:,.2f}\n"
            )

    @classmethod
    def error_alert(
        cls,
        error_type: str,
        error_message: str,
        context: Optional[str] = None,
        format: MessageFormat = MessageFormat.MARKDOWNV2,
    ) -> str:
        """Error alert notification."""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

        if format == MessageFormat.MARKDOWNV2:
            error_type_esc = cls._escape_markdown_v2(error_type)
            error_message_esc = cls._escape_markdown_v2(error_message)
            timestamp_esc = cls._escape_markdown_v2(timestamp)

            msg = (
                f"⚠️ *ERRO DETECTADO*\n\n"
                f"🔴 *Tipo:* {error_type_esc}\n"
                f"📝 *Mensagem:* {error_message_esc}\n"
            )

            if context:
                context_esc = cls._escape_markdown_v2(context)
                msg += f"📍 *Contexto:* {context_esc}\n"

            msg += f"\n⏰ {timestamp_esc}"
            return msg

        else:
            msg = (
                f"⚠️ <b>ERRO DETECTADO</b>\n\n"
                f"🔴 <b>Tipo:</b> {error_type}\n"
                f"📝 <b>Mensagem:</b> {error_message}\n"
            )

            if context:
                msg += f"📍 <b>Contexto:</b> {context}\n"

            msg += f"\n⏰ {timestamp}"
            return msg
