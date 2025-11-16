"""SQLite implementation of TransactionRepository."""

import csv
import json
from datetime import datetime
from typing import List, Optional, Tuple

from loguru import logger

from src.domain.account.entities.transaction import Transaction, TransactionType
from src.domain.account.repositories.transaction_repository import TransactionRepository
from src.domain.account.value_objects.currency import Currency
from src.domain.account.value_objects.money import Money
from src.infrastructure.database import DatabaseManager


class SQLiteTransactionRepository(TransactionRepository):
    """
    SQLite implementation of TransactionRepository.

    Provides efficient queries for transaction audit trail and analytics.
    """

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize SQLiteTransactionRepository.

        Args:
            db_manager: Database manager instance
        """
        self.db = db_manager
        logger.debug("SQLiteTransactionRepository initialized")

    def save(self, transaction: Transaction, account_id: str) -> None:
        """
        Save transaction.

        Args:
            transaction: Transaction to save
            account_id: Associated account ID

        Raises:
            sqlite3.DatabaseError: If save fails
        """
        try:
            self.db.execute_update(
                """
                INSERT OR REPLACE INTO transactions
                (id, account_id, transaction_type, currency, amount, description, reference_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    transaction.id,
                    account_id,
                    transaction.transaction_type.value,
                    transaction.amount.currency.code,
                    transaction.amount.available.amount,
                    transaction.description,
                    transaction.reference_id,
                ),
            )
            logger.debug(f"Transaction saved: {transaction.id}")

        except Exception as e:
            logger.error(f"Failed to save transaction: {e}")
            raise

    def find_by_id(self, transaction_id: str) -> Optional[Transaction]:
        """
        Find transaction by ID.

        Args:
            transaction_id: Transaction ID

        Returns:
            Transaction if found, None otherwise

        Raises:
            sqlite3.DatabaseError: If query fails
        """
        try:
            rows = self.db.execute_query(
                "SELECT * FROM transactions WHERE id = ?",
                (transaction_id,),
            )

            if not rows:
                return None

            return self._row_to_transaction(rows[0])

        except Exception as e:
            logger.error(f"Failed to find transaction: {e}")
            raise

    def find_by_account(self, account_id: str, limit: int = 100) -> List[Transaction]:
        """
        Find recent transactions for account.

        Args:
            account_id: Account ID
            limit: Maximum results

        Returns:
            List of transactions sorted by timestamp DESC

        Raises:
            sqlite3.DatabaseError: If query fails
        """
        try:
            rows = self.db.execute_query(
                """
                SELECT * FROM transactions
                WHERE account_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (account_id, limit),
            )

            return [self._row_to_transaction(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to find transactions for account: {e}")
            raise

    def find_by_type(
        self, account_id: str, tx_type: TransactionType, limit: int = 100
    ) -> List[Transaction]:
        """
        Find transactions by type.

        Args:
            account_id: Account ID
            tx_type: Transaction type
            limit: Maximum results

        Returns:
            List of matching transactions

        Raises:
            sqlite3.DatabaseError: If query fails
        """
        try:
            rows = self.db.execute_query(
                """
                SELECT * FROM transactions
                WHERE account_id = ? AND transaction_type = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (account_id, tx_type.value, limit),
            )

            return [self._row_to_transaction(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to find transactions by type: {e}")
            raise

    def find_by_period(
        self, account_id: str, start: datetime, end: datetime
    ) -> List[Transaction]:
        """
        Find transactions in date range.

        Args:
            account_id: Account ID
            start: Start datetime
            end: End datetime

        Returns:
            List of transactions in period

        Raises:
            sqlite3.DatabaseError: If query fails
        """
        try:
            rows = self.db.execute_query(
                """
                SELECT * FROM transactions
                WHERE account_id = ? AND created_at BETWEEN ? AND ?
                ORDER BY created_at DESC
                """,
                (account_id, start.isoformat(), end.isoformat()),
            )

            return [self._row_to_transaction(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to find transactions by period: {e}")
            raise

    def find_by_currency(
        self, account_id: str, currency: Currency, limit: int = 100
    ) -> List[Transaction]:
        """
        Find transactions by currency.

        Args:
            account_id: Account ID
            currency: Currency
            limit: Maximum results

        Returns:
            List of transactions

        Raises:
            sqlite3.DatabaseError: If query fails
        """
        try:
            rows = self.db.execute_query(
                """
                SELECT * FROM transactions
                WHERE account_id = ? AND currency = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (account_id, currency.code, limit),
            )

            return [self._row_to_transaction(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to find transactions by currency: {e}")
            raise

    def get_sum_by_type(
        self,
        account_id: str,
        tx_type: TransactionType,
        currency: Currency,
    ) -> float:
        """
        Get sum of amounts by transaction type.

        Args:
            account_id: Account ID
            tx_type: Transaction type
            currency: Currency

        Returns:
            Total amount

        Raises:
            sqlite3.DatabaseError: If query fails
        """
        try:
            rows = self.db.execute_query(
                """
                SELECT COALESCE(SUM(amount), 0) as total
                FROM transactions
                WHERE account_id = ? AND transaction_type = ? AND currency = ?
                """,
                (account_id, tx_type.value, currency.code),
            )

            return float(rows[0]["total"]) if rows else 0.0

        except Exception as e:
            logger.error(f"Failed to get sum by type: {e}")
            raise

    def get_sum_by_currency(
        self, account_id: str, currency: Currency
    ) -> Tuple[float, float]:
        """
        Get total deposits and withdrawals for currency.

        Args:
            account_id: Account ID
            currency: Currency

        Returns:
            Tuple of (total_deposits, total_withdrawals)

        Raises:
            sqlite3.DatabaseError: If query fails
        """
        try:
            # Get deposits
            deposits = self.get_sum_by_type(
                account_id, TransactionType.DEPOSIT, currency
            )

            # Get withdrawals
            withdrawals = self.get_sum_by_type(
                account_id, TransactionType.WITHDRAWAL, currency
            )

            return (deposits, withdrawals)

        except Exception as e:
            logger.error(f"Failed to get sum by currency: {e}")
            raise

    def get_transaction_count(self, account_id: str) -> int:
        """
        Get total transaction count.

        Args:
            account_id: Account ID

        Returns:
            Number of transactions

        Raises:
            sqlite3.DatabaseError: If query fails
        """
        try:
            rows = self.db.execute_query(
                "SELECT COUNT(*) as count FROM transactions WHERE account_id = ?",
                (account_id,),
            )

            return int(rows[0]["count"]) if rows else 0

        except Exception as e:
            logger.error(f"Failed to get transaction count: {e}")
            raise

    def delete_by_account(self, account_id: str) -> int:
        """
        Delete all transactions for account.

        Args:
            account_id: Account ID

        Returns:
            Number of deleted transactions

        Raises:
            sqlite3.DatabaseError: If delete fails
        """
        try:
            affected = self.db.execute_update(
                "DELETE FROM transactions WHERE account_id = ?",
                (account_id,),
            )
            logger.debug(f"Deleted {affected} transactions for account {account_id}")
            return affected

        except Exception as e:
            logger.error(f"Failed to delete transactions: {e}")
            raise

    def export_to_csv(self, account_id: str, filepath: str) -> None:
        """
        Export transactions to CSV.

        Args:
            account_id: Account ID
            filepath: Output file path

        Raises:
            OSError: If export fails
        """
        try:
            transactions = self.find_by_account(account_id, limit=10000)

            with open(filepath, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "ID",
                        "Type",
                        "Currency",
                        "Amount",
                        "Description",
                        "Reference ID",
                        "Created At",
                    ]
                )

                for tx in transactions:
                    writer.writerow(
                        [
                            tx.id,
                            tx.transaction_type.value,
                            tx.amount.currency.code,
                            tx.amount.available.amount,
                            tx.description,
                            tx.reference_id or "",
                            tx.timestamp.isoformat(),
                        ]
                    )

            logger.info(f"Exported {len(transactions)} transactions to {filepath}")

        except Exception as e:
            logger.error(f"Failed to export transactions to CSV: {e}")
            raise OSError(f"Export failed: {e}")

    def export_to_json(self, account_id: str, filepath: str) -> None:
        """
        Export transactions to JSON.

        Args:
            account_id: Account ID
            filepath: Output file path

        Raises:
            OSError: If export fails
        """
        try:
            transactions = self.find_by_account(account_id, limit=10000)

            data = {
                "account_id": account_id,
                "count": len(transactions),
                "exported_at": datetime.utcnow().isoformat(),
                "transactions": [
                    {
                        "id": tx.id,
                        "type": tx.transaction_type.value,
                        "currency": tx.amount.currency.code,
                        "amount": tx.amount.available.amount,
                        "description": tx.description,
                        "reference_id": tx.reference_id,
                        "timestamp": tx.timestamp.isoformat(),
                    }
                    for tx in transactions
                ],
            }

            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)

            logger.info(f"Exported {len(transactions)} transactions to {filepath}")

        except Exception as e:
            logger.error(f"Failed to export transactions to JSON: {e}")
            raise OSError(f"Export failed: {e}")

    def _row_to_transaction(self, row) -> Transaction:
        """
        Convert database row to Transaction entity.

        Args:
            row: Database row

        Returns:
            Transaction entity
        """
        currency = Currency(row["currency"])
        money = Money(
            currency=currency,
            available_amount=row["amount"],
        )

        tx = Transaction(
            transaction_type=TransactionType(row["transaction_type"]),
            amount=money,
            description=row["description"],
            reference_id=row["reference_id"],
        )

        tx.id = row["id"]
        tx.timestamp = datetime.fromisoformat(row["created_at"])

        return tx
