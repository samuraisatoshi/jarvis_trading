"""Order repository for paper trading."""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import List, Optional


class OrderStatus(str, Enum):
    """Order status enumeration."""

    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class OrderSide(str, Enum):
    """Order side enumeration."""

    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    """Order type enumeration."""

    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"


class Order:
    """
    Order entity for paper trading.

    Represents a single trade order with pricing and execution details.
    """

    def __init__(
        self,
        order_id: str,
        account_id: str,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
    ):
        """
        Initialize Order.

        Args:
            order_id: Unique order identifier
            account_id: Associated account ID
            symbol: Trading pair (e.g., BTCUSDT)
            side: BUY or SELL
            order_type: MARKET, LIMIT, or STOP_LOSS
            quantity: Order quantity
            price: Limit price (if LIMIT order)
            stop_price: Stop price (if STOP_LOSS order)
        """
        self.order_id = order_id
        self.account_id = account_id
        self.symbol = symbol
        self.side = side
        self.order_type = order_type
        self.quantity = quantity
        self.price = price
        self.stop_price = stop_price
        self.status = OrderStatus.PENDING
        self.filled_quantity = 0.0
        self.executed_price: Optional[float] = None
        self.fee_amount = 0.0
        self.fee_currency = "USDT"
        self.created_at = datetime.utcnow()
        self.executed_at: Optional[datetime] = None
        self.metadata = {}

    def execute(self, executed_price: float, filled_qty: Optional[float] = None):
        """
        Execute order.

        Args:
            executed_price: Price at execution
            filled_qty: Quantity filled (None = full fill)
        """
        filled = filled_qty if filled_qty is not None else self.quantity
        self.filled_quantity = filled
        self.executed_price = executed_price
        self.executed_at = datetime.utcnow()

        if filled >= self.quantity:
            self.status = OrderStatus.FILLED
        else:
            self.status = OrderStatus.PARTIALLY_FILLED

    def cancel(self):
        """Cancel order."""
        if self.status not in (
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
        ):
            self.status = OrderStatus.CANCELLED

    def get_summary(self) -> dict:
        """Get order summary."""
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "type": self.order_type.value,
            "quantity": self.quantity,
            "price": self.price,
            "status": self.status.value,
            "filled_quantity": self.filled_quantity,
            "executed_price": self.executed_price,
            "fee_amount": self.fee_amount,
            "created_at": self.created_at.isoformat(),
            "executed_at": (
                self.executed_at.isoformat() if self.executed_at else None
            ),
        }


class OrderRepository(ABC):
    """
    Repository abstraction for Order persistence.

    Manages paper trading orders with status tracking and history.
    """

    @abstractmethod
    def save(self, order: Order) -> None:
        """
        Save order.

        Args:
            order: Order to save

        Raises:
            RepositoryException: If save fails
        """
        pass

    @abstractmethod
    def find_by_id(self, order_id: str) -> Optional[Order]:
        """
        Find order by ID.

        Args:
            order_id: Order ID

        Returns:
            Order if found, None otherwise

        Raises:
            RepositoryException: If query fails
        """
        pass

    @abstractmethod
    def find_by_account(self, account_id: str, limit: int = 100) -> List[Order]:
        """
        Find orders for account.

        Args:
            account_id: Account ID
            limit: Maximum results

        Returns:
            List of orders

        Raises:
            RepositoryException: If query fails
        """
        pass

    @abstractmethod
    def find_by_status(
        self, account_id: str, status: OrderStatus, limit: int = 100
    ) -> List[Order]:
        """
        Find orders by status.

        Args:
            account_id: Account ID
            status: Order status
            limit: Maximum results

        Returns:
            List of matching orders

        Raises:
            RepositoryException: If query fails
        """
        pass

    @abstractmethod
    def find_by_symbol(
        self, account_id: str, symbol: str, limit: int = 100
    ) -> List[Order]:
        """
        Find orders by symbol.

        Args:
            account_id: Account ID
            symbol: Trading pair
            limit: Maximum results

        Returns:
            List of matching orders

        Raises:
            RepositoryException: If query fails
        """
        pass

    @abstractmethod
    def get_pending_orders(self, account_id: str) -> List[Order]:
        """
        Get all pending orders for account.

        Args:
            account_id: Account ID

        Returns:
            List of pending orders

        Raises:
            RepositoryException: If query fails
        """
        pass

    @abstractmethod
    def get_filled_orders(self, account_id: str) -> List[Order]:
        """
        Get all filled orders for account.

        Args:
            account_id: Account ID

        Returns:
            List of filled orders

        Raises:
            RepositoryException: If query fails
        """
        pass

    @abstractmethod
    def get_order_count(self, account_id: str) -> int:
        """
        Get total order count.

        Args:
            account_id: Account ID

        Returns:
            Number of orders

        Raises:
            RepositoryException: If query fails
        """
        pass

    @abstractmethod
    def delete_by_account(self, account_id: str) -> int:
        """
        Delete all orders for account.

        Args:
            account_id: Account ID

        Returns:
            Number of deleted orders

        Raises:
            RepositoryException: If delete fails
        """
        pass
