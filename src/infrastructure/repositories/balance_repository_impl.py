"""
Balance repository implementation using SQLite.

Implements BalanceRepository protocol for daemon package.
"""

from typing import Dict
from loguru import logger
import sqlite3

from src.daemon.interfaces import BalanceRepository


class BalanceRepositoryImpl(BalanceRepository):
    """
    SQLite implementation of BalanceRepository.

    Handles CRUD operations for account balances with proper
    transaction management and error handling.
    """

    def __init__(self, db_path: str, account_id: str):
        """
        Initialize balance repository.

        Args:
            db_path: Path to SQLite database file
            account_id: Account ID for filtering balances
        """
        self.db_path = db_path
        self.account_id = account_id

    def get_balance(self, currency: str) -> float:
        """
        Get available balance for specific currency.

        Args:
            currency: Currency code (e.g., 'USDT', 'BTC')

        Returns:
            Available balance amount (0.0 if not found)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT available_amount
                FROM balances
                WHERE account_id = ? AND currency = ?
            """, (self.account_id, currency))

            row = cursor.fetchone()
            return row[0] if row else 0.0

        except Exception as e:
            logger.error(f"Error getting balance for {currency}: {e}")
            return 0.0

        finally:
            conn.close()

    def get_all_balances(self) -> Dict[str, float]:
        """
        Get all account balances.

        Returns:
            Dict mapping currency code to available balance
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT currency, available_amount
                FROM balances
                WHERE account_id = ?
            """, (self.account_id,))

            balances = {
                currency: amount
                for currency, amount in cursor.fetchall()
            }

            return balances

        except Exception as e:
            logger.error(f"Error getting all balances: {e}")
            return {}

        finally:
            conn.close()

    def update_balance(
        self,
        currency: str,
        amount: float,
        operation: str
    ) -> bool:
        """
        Update balance (add or subtract).

        Uses SQLite's UPSERT to handle create-or-update atomically.

        Args:
            currency: Currency code
            amount: Amount to add/subtract (positive value)
            operation: 'add' or 'subtract'

        Returns:
            True if successful, False otherwise
        """
        if operation not in ['add', 'subtract']:
            logger.error(f"Invalid operation: {operation}")
            return False

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            if operation == 'add':
                # Add to balance (create if not exists)
                cursor.execute("""
                    INSERT INTO balances (
                        account_id,
                        currency,
                        available_amount,
                        reserved_amount
                    )
                    VALUES (?, ?, ?, 0)
                    ON CONFLICT(account_id, currency)
                    DO UPDATE SET available_amount = available_amount + ?
                """, (self.account_id, currency, amount, amount))

            elif operation == 'subtract':
                # Subtract from balance
                cursor.execute("""
                    UPDATE balances
                    SET available_amount = available_amount - ?
                    WHERE account_id = ? AND currency = ?
                """, (amount, self.account_id, currency))

                # Verify balance didn't go negative
                cursor.execute("""
                    SELECT available_amount
                    FROM balances
                    WHERE account_id = ? AND currency = ?
                """, (self.account_id, currency))

                row = cursor.fetchone()
                if row and row[0] < 0:
                    logger.error(
                        f"Balance would go negative for {currency}: {row[0]}"
                    )
                    conn.rollback()
                    return False

            conn.commit()
            logger.debug(
                f"Balance updated: {operation} {amount} {currency}"
            )
            return True

        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to update balance: {e}")
            return False

        finally:
            conn.close()
