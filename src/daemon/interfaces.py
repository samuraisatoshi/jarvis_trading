"""
Abstract interfaces (protocols) for daemon dependencies.

Defines contracts for infrastructure components using Protocol pattern
to enable dependency injection and testability.
"""

from typing import Protocol, Dict, List, Optional
from .models import Signal, Position


class ExchangeClient(Protocol):
    """
    Exchange API client protocol.

    Defines interface for market data and order execution.
    """

    def get_24h_ticker(self, symbol: str) -> Dict:
        """
        Get 24-hour ticker statistics for symbol.

        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')

        Returns:
            Dict with ticker data including 'lastPrice'
        """
        ...

    def get_klines(
        self,
        symbol: str,
        interval: str,
        limit: int
    ) -> List:
        """
        Get historical candlestick data.

        Args:
            symbol: Trading pair symbol
            interval: Timeframe (1h, 4h, 1d, etc.)
            limit: Number of candles to fetch

        Returns:
            List of kline data
        """
        ...


class BalanceRepository(Protocol):
    """
    Balance repository protocol.

    Handles CRUD operations for account balances.
    """

    def get_balance(self, currency: str) -> float:
        """
        Get available balance for specific currency.

        Args:
            currency: Currency code (e.g., 'USDT', 'BTC')

        Returns:
            Available balance amount
        """
        ...

    def get_all_balances(self) -> Dict[str, float]:
        """
        Get all account balances.

        Returns:
            Dict mapping currency code to available balance
        """
        ...

    def update_balance(
        self,
        currency: str,
        amount: float,
        operation: str
    ) -> bool:
        """
        Update balance (add or subtract).

        Args:
            currency: Currency code
            amount: Amount to add/subtract (positive value)
            operation: 'add' or 'subtract'

        Returns:
            True if successful, False otherwise
        """
        ...


class OrderRepository(Protocol):
    """
    Order repository protocol.

    Handles creation and persistence of orders.
    """

    def create_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        order_type: str = "MARKET"
    ) -> str:
        """
        Create and persist order.

        Args:
            symbol: Trading pair symbol
            side: 'BUY' or 'SELL'
            quantity: Order quantity
            price: Execution price
            order_type: Order type (default: 'MARKET')

        Returns:
            Generated order ID

        Raises:
            Exception: If order creation fails
        """
        ...


class PositionRepository(Protocol):
    """
    Position repository protocol.

    Handles queries for current asset positions.
    """

    def get_position(self, symbol: str) -> Optional[Position]:
        """
        Get current position for symbol.

        Args:
            symbol: Trading pair symbol

        Returns:
            Position if exists and quantity > 0, None otherwise
        """
        ...

    def get_all_positions(self) -> List[Position]:
        """
        Get all open positions.

        Returns:
            List of positions with quantity > 0
        """
        ...


class NotificationService(Protocol):
    """
    Notification service protocol.

    Handles sending alerts and status updates.
    """

    def send_message(self, message: str) -> bool:
        """
        Send generic text message.

        Args:
            message: Message content

        Returns:
            True if sent successfully
        """
        ...

    def notify_trade_executed(
        self,
        trade_type: str,
        symbol: str,
        quantity: float,
        price: float,
        timeframe: str,
        reason: Optional[str] = None
    ) -> bool:
        """
        Send trade execution notification.

        Args:
            trade_type: 'BUY' or 'SELL'
            symbol: Trading pair symbol
            quantity: Trade quantity
            price: Execution price
            timeframe: Signal timeframe
            reason: Optional reason for trade

        Returns:
            True if sent successfully
        """
        ...

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
            True if sent successfully
        """
        ...

    def notify_signals_found(self, signals: List[Signal]) -> bool:
        """
        Send signals detected notification.

        Args:
            signals: List of detected signals

        Returns:
            True if sent successfully
        """
        ...


class SignalStrategy(Protocol):
    """
    Signal generation strategy protocol.

    Defines interface for pluggable signal generation algorithms.
    """

    def generate_signal(
        self,
        symbol: str,
        timeframe: str,
        exchange_client: ExchangeClient,
        position_repo: PositionRepository
    ) -> Optional[Signal]:
        """
        Generate trading signal for symbol/timeframe.

        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe to analyze
            exchange_client: Exchange client for market data
            position_repo: Position repository for current holdings

        Returns:
            Signal if opportunity detected, None otherwise
        """
        ...


class WatchlistManager(Protocol):
    """
    Watchlist manager protocol.

    Manages list of symbols to monitor and their parameters.
    """

    @property
    def symbols(self) -> List[str]:
        """Get list of watched symbols."""
        ...

    def get_params(self, symbol: str, timeframe: str) -> Optional[Dict]:
        """
        Get optimized parameters for symbol/timeframe.

        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe identifier

        Returns:
            Dict with parameters (ma_period, buy_threshold, sell_threshold)
            or None if not configured
        """
        ...
