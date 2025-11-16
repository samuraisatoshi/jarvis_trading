"""
Order repository implementation using SQLite.

Implements OrderRepository protocol for daemon package.
"""

from datetime import datetime, timezone
import sqlite3
from loguru import logger

from src.daemon.interfaces import OrderRepository


class OrderRepositoryImpl(OrderRepository):
    """
    SQLite implementation of OrderRepository.

    Handles creation and persistence of orders with automatic
    transaction record generation.
    """

    def __init__(self, db_path: str, account_id: str):
        """
        Initialize order repository.

        Args:
            db_path: Path to SQLite database file
            account_id: Account ID for filtering orders
        """
        self.db_path = db_path
        self.account_id = account_id

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

        Also creates corresponding transaction record for audit trail.

        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            side: 'BUY' or 'SELL'
            quantity: Order quantity
            price: Execution price
            order_type: Order type (default: 'MARKET')

        Returns:
            Generated order ID

        Raises:
            Exception: If order creation fails
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Generate order ID
            timestamp = datetime.now(timezone.utc).timestamp()
            order_id = f"{side}_{symbol}_{timestamp}"

            # Create order record
            cursor.execute("""
                INSERT INTO orders (
                    id,
                    account_id,
                    symbol,
                    side,
                    order_type,
                    quantity,
                    price,
                    status,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_id,
                self.account_id,
                symbol,
                side,
                order_type,
                quantity,
                price,
                'FILLED',  # Paper trading - always filled
                datetime.now(timezone.utc).isoformat()
            ))

            # Create transaction record
            base_currency = symbol.replace('USDT', '')
            cursor.execute("""
                INSERT INTO transactions (
                    id,
                    account_id,
                    transaction_type,
                    amount,
                    currency,
                    description,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                f"TX_{order_id}",
                self.account_id,
                side,
                quantity,
                base_currency,
                f"{side} {symbol} @ ${price:.2f}",
                datetime.now(timezone.utc).isoformat()
            ))

            conn.commit()

            logger.debug(
                f"Order created: {order_id} - {side} {quantity:.6f} "
                f"{symbol} @ ${price:.2f}"
            )

            return order_id

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to create order: {e}")
            raise

        finally:
            conn.close()
