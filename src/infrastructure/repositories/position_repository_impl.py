"""
Position repository implementation using SQLite.

Implements PositionRepository protocol for daemon package.
"""

from typing import Optional, List
import sqlite3
from loguru import logger

from src.daemon.interfaces import PositionRepository
from src.daemon.models import Position


class PositionRepositoryImpl(PositionRepository):
    """
    SQLite implementation of PositionRepository.

    Queries balances table to determine current positions
    (non-zero balances in non-USDT currencies).
    """

    def __init__(self, db_path: str, account_id: str):
        """
        Initialize position repository.

        Args:
            db_path: Path to SQLite database file
            account_id: Account ID for filtering positions
        """
        self.db_path = db_path
        self.account_id = account_id

    def get_position(self, symbol: str) -> Optional[Position]:
        """
        Get current position for symbol.

        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')

        Returns:
            Position if exists with quantity > 0, None otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Extract base currency from symbol
            base_currency = symbol.replace('USDT', '')

            cursor.execute("""
                SELECT available_amount
                FROM balances
                WHERE account_id = ? AND currency = ?
            """, (self.account_id, base_currency))

            row = cursor.fetchone()

            if row and row[0] > 0:
                return Position(
                    symbol=symbol,
                    currency=base_currency,
                    quantity=row[0]
                )

            return None

        except Exception as e:
            logger.error(f"Error getting position for {symbol}: {e}")
            return None

        finally:
            conn.close()

    def get_all_positions(self) -> List[Position]:
        """
        Get all open positions.

        Returns:
            List of positions with quantity > 0 (excludes USDT)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT currency, available_amount
                FROM balances
                WHERE account_id = ?
                  AND currency != 'USDT'
                  AND available_amount > 0
            """, (self.account_id,))

            positions = []
            for currency, quantity in cursor.fetchall():
                positions.append(Position(
                    symbol=f"{currency}USDT",
                    currency=currency,
                    quantity=quantity
                ))

            return positions

        except Exception as e:
            logger.error(f"Error getting all positions: {e}")
            return []

        finally:
            conn.close()
