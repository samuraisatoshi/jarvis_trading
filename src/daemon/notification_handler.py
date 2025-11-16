"""
Notification handling service.

Centralizes all notification logic and formatting.
"""

from typing import List
from loguru import logger
from datetime import datetime

from .models import Signal, PortfolioStatus, TradeResult
from .interfaces import NotificationService


class NotificationHandler:
    """
    Notification handling service.

    Routes and formats notifications for various daemon events.
    Provides consistent notification interface across the system.
    """

    def __init__(self, notification_service: NotificationService):
        """
        Initialize notification handler.

        Args:
            notification_service: Underlying notification service
        """
        self.notification_service = notification_service

    def notify_daemon_started(
        self,
        watchlist: List[str],
        capital: float
    ) -> bool:
        """
        Send daemon startup notification.

        Args:
            watchlist: List of monitored symbols
            capital: Total portfolio value

        Returns:
            True if notification sent successfully
        """
        try:
            return self.notification_service.notify_daemon_started(
                watchlist=watchlist,
                capital=capital
            )
        except Exception as e:
            logger.error(f"Failed to notify daemon start: {e}")
            return False

    def notify_signals_found(self, signals: List[Signal]) -> bool:
        """
        Send signals detected notification.

        Args:
            signals: List of detected signals

        Returns:
            True if notification sent successfully
        """
        if not signals:
            return True

        try:
            return self.notification_service.notify_signals_found(signals)
        except Exception as e:
            logger.error(f"Failed to notify signals: {e}")
            return False

    def notify_trade_executed(self, result: TradeResult) -> bool:
        """
        Send trade execution notification.

        Only sends notification if trade was successful.

        Args:
            result: Trade execution result

        Returns:
            True if notification sent successfully
        """
        if not result.success:
            return True

        try:
            return self.notification_service.notify_trade_executed(
                trade_type=result.signal.action.value,
                symbol=result.signal.symbol,
                quantity=result.quantity or 0.0,
                price=result.signal.price,
                timeframe=result.signal.timeframe,
                reason=result.signal.reason
            )
        except Exception as e:
            logger.error(f"Failed to notify trade execution: {e}")
            return False

    def send_status_update(self, portfolio: PortfolioStatus) -> bool:
        """
        Send portfolio status update.

        Formats portfolio data into readable message.

        Args:
            portfolio: Portfolio status snapshot

        Returns:
            True if notification sent successfully
        """
        try:
            message = self._format_status_message(portfolio)
            return self.notification_service.send_message(message)
        except Exception as e:
            logger.error(f"Failed to send status update: {e}")
            return False

    def send_error_alert(self, error: str, context: str = "") -> bool:
        """
        Send error alert notification.

        Args:
            error: Error message
            context: Additional context

        Returns:
            True if notification sent successfully
        """
        try:
            message = f"⚠️ **ERROR ALERT**\n\n{error}"
            if context:
                message += f"\n\nContext: {context}"

            return self.notification_service.send_message(message)
        except Exception as e:
            logger.error(f"Failed to send error alert: {e}")
            return False

    def _format_status_message(self, portfolio: PortfolioStatus) -> str:
        """
        Format portfolio status as readable message.

        Args:
            portfolio: Portfolio status snapshot

        Returns:
            Formatted message string
        """
        message = "📊 **PORTFOLIO STATUS**\n\n"
        message += f"💰 Total Value: ${portfolio.total_value:.2f}\n"
        message += f"💵 USDT Available: ${portfolio.usdt_balance:.2f}\n"
        message += f"📈 Invested: ${portfolio.invested_value:.2f} "
        message += f"({portfolio.allocation_percent:.1f}%)\n\n"

        if portfolio.positions:
            message += f"**Open Positions ({portfolio.num_positions}):**\n"
            for pos in portfolio.positions:
                message += (
                    f"• {pos.symbol}: {pos.quantity:.4f} {pos.currency}\n"
                )
        else:
            message += "📉 No open positions\n"

        message += (
            f"\n⏰ {portfolio.timestamp.strftime('%Y-%m-%d %H:%M')} UTC"
        )

        return message

    def _format_signal_message(self, signals: List[Signal]) -> str:
        """
        Format signals as readable message.

        Args:
            signals: List of signals

        Returns:
            Formatted message string
        """
        message = f"🔔 **{len(signals)} SIGNALS DETECTED**\n\n"

        for signal in signals:
            emoji = "🟢" if signal.action.value == "BUY" else "🔴"
            message += (
                f"{emoji} {signal.action.value} {signal.symbol} "
                f"({signal.timeframe})\n"
                f"  Price: ${signal.price:.2f}\n"
                f"  Reason: {signal.reason}\n\n"
            )

        return message
