"""SQLite implementation of OrderRepository."""

from typing import List, Optional

from loguru import logger

from src.domain.paper_trading.repositories.order_repository import (
    Order,
    OrderRepository,
    OrderSide,
    OrderStatus,
    OrderType,
)
from src.infrastructure.database import DatabaseManager


class SQLiteOrderRepository(OrderRepository):
    """
    SQLite implementation of OrderRepository.

    Provides efficient order storage and querying for paper trading.
    """

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize SQLiteOrderRepository.

        Args:
            db_manager: Database manager instance
        """
        self.db = db_manager
        logger.debug("SQLiteOrderRepository initialized")

    def save(self, order: Order) -> None:
        """
        Save order.

        Args:
            order: Order to save

        Raises:
            sqlite3.DatabaseError: If save fails
        """
        try:
            self.db.execute_update(
                """
                INSERT OR REPLACE INTO orders
                (id, account_id, symbol, side, order_type, status, quantity,
                 price, executed_price, fee_amount, fee_currency, executed_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    order.order_id,
                    order.account_id,
                    order.symbol,
                    order.side.value,
                    order.order_type.value,
                    order.status.value,
                    order.quantity,
                    order.price,
                    order.executed_price,
                    order.fee_amount,
                    order.fee_currency,
                    order.executed_at.isoformat() if order.executed_at else None,
                    None,  # metadata can be extended later
                ),
            )
            logger.debug(f"Order saved: {order.order_id}")

        except Exception as e:
            logger.error(f"Failed to save order: {e}")
            raise

    def find_by_id(self, order_id: str) -> Optional[Order]:
        """
        Find order by ID.

        Args:
            order_id: Order ID

        Returns:
            Order if found, None otherwise

        Raises:
            sqlite3.DatabaseError: If query fails
        """
        try:
            rows = self.db.execute_query(
                "SELECT * FROM orders WHERE id = ?",
                (order_id,),
            )

            if not rows:
                return None

            return self._row_to_order(rows[0])

        except Exception as e:
            logger.error(f"Failed to find order: {e}")
            raise

    def find_by_account(self, account_id: str, limit: int = 100) -> List[Order]:
        """
        Find orders for account.

        Args:
            account_id: Account ID
            limit: Maximum results

        Returns:
            List of orders

        Raises:
            sqlite3.DatabaseError: If query fails
        """
        try:
            rows = self.db.execute_query(
                """
                SELECT * FROM orders
                WHERE account_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (account_id, limit),
            )

            return [self._row_to_order(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to find orders for account: {e}")
            raise

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
            sqlite3.DatabaseError: If query fails
        """
        try:
            rows = self.db.execute_query(
                """
                SELECT * FROM orders
                WHERE account_id = ? AND status = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (account_id, status.value, limit),
            )

            return [self._row_to_order(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to find orders by status: {e}")
            raise

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
            sqlite3.DatabaseError: If query fails
        """
        try:
            rows = self.db.execute_query(
                """
                SELECT * FROM orders
                WHERE account_id = ? AND symbol = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (account_id, symbol, limit),
            )

            return [self._row_to_order(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to find orders by symbol: {e}")
            raise

    def get_pending_orders(self, account_id: str) -> List[Order]:
        """
        Get all pending orders for account.

        Args:
            account_id: Account ID

        Returns:
            List of pending orders

        Raises:
            sqlite3.DatabaseError: If query fails
        """
        try:
            rows = self.db.execute_query(
                """
                SELECT * FROM orders
                WHERE account_id = ? AND status IN ('PENDING', 'PARTIALLY_FILLED')
                ORDER BY created_at DESC
                """,
                (account_id,),
            )

            return [self._row_to_order(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get pending orders: {e}")
            raise

    def get_filled_orders(self, account_id: str) -> List[Order]:
        """
        Get all filled orders for account.

        Args:
            account_id: Account ID

        Returns:
            List of filled orders

        Raises:
            sqlite3.DatabaseError: If query fails
        """
        try:
            rows = self.db.execute_query(
                """
                SELECT * FROM orders
                WHERE account_id = ? AND status = 'FILLED'
                ORDER BY executed_at DESC
                """,
                (account_id,),
            )

            return [self._row_to_order(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get filled orders: {e}")
            raise

    def get_order_count(self, account_id: str) -> int:
        """
        Get total order count.

        Args:
            account_id: Account ID

        Returns:
            Number of orders

        Raises:
            sqlite3.DatabaseError: If query fails
        """
        try:
            rows = self.db.execute_query(
                "SELECT COUNT(*) as count FROM orders WHERE account_id = ?",
                (account_id,),
            )

            return int(rows[0]["count"]) if rows else 0

        except Exception as e:
            logger.error(f"Failed to get order count: {e}")
            raise

    def delete_by_account(self, account_id: str) -> int:
        """
        Delete all orders for account.

        Args:
            account_id: Account ID

        Returns:
            Number of deleted orders

        Raises:
            sqlite3.DatabaseError: If delete fails
        """
        try:
            affected = self.db.execute_update(
                "DELETE FROM orders WHERE account_id = ?",
                (account_id,),
            )
            logger.debug(f"Deleted {affected} orders for account {account_id}")
            return affected

        except Exception as e:
            logger.error(f"Failed to delete orders: {e}")
            raise

    def _row_to_order(self, row) -> Order:
        """
        Convert database row to Order entity.

        Args:
            row: Database row

        Returns:
            Order entity
        """
        from datetime import datetime

        order = Order(
            order_id=row["id"],
            account_id=row["account_id"],
            symbol=row["symbol"],
            side=OrderSide(row["side"]),
            order_type=OrderType(row["order_type"]),
            quantity=row["quantity"],
            price=row["price"],
        )

        order.status = OrderStatus(row["status"])
        order.filled_quantity = row.get("quantity", 0)  # Default to quantity
        order.executed_price = row["executed_price"]
        order.fee_amount = row["fee_amount"]
        order.fee_currency = row["fee_currency"]
        order.created_at = datetime.fromisoformat(row["created_at"])

        if row["executed_at"]:
            order.executed_at = datetime.fromisoformat(row["executed_at"])

        return order
