"""SQLite implementation of AccountRepository."""

import json
from typing import List, Optional

from loguru import logger

from src.domain.account.entities.account import Account
from src.domain.account.entities.balance import Balance
from src.domain.account.entities.transaction import Transaction, TransactionType
from src.domain.account.repositories.account_repository import AccountRepository
from src.domain.account.value_objects.currency import Currency
from src.domain.account.value_objects.money import Money
from src.infrastructure.database import DatabaseManager


class SQLiteAccountRepository(AccountRepository):
    """
    SQLite implementation of AccountRepository.

    Provides persistent account storage with transaction management,
    type-safe queries, and audit trail support.
    """

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize SQLiteAccountRepository.

        Args:
            db_manager: Database manager instance
        """
        self.db = db_manager
        logger.debug("SQLiteAccountRepository initialized")

    def save(self, account: Account) -> None:
        """
        Save account to database.

        Creates new account or updates existing. Handles associated
        balances and transactions atomically.

        Args:
            account: Account entity to save

        Raises:
            sqlite3.DatabaseError: If save fails
        """
        try:
            with self.db.transaction() as conn:
                cursor = conn.cursor()

                # Upsert account
                cursor.execute(
                    """
                    INSERT INTO accounts (id, name, leverage, is_active, closed_at, max_leverage, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                    ON CONFLICT(id) DO UPDATE SET
                        name = excluded.name,
                        leverage = excluded.leverage,
                        is_active = excluded.is_active,
                        closed_at = excluded.closed_at,
                        max_leverage = excluded.max_leverage,
                        updated_at = datetime('now')
                    """,
                    (
                        account.account_id,
                        account.name,
                        account.leverage,
                        account.is_active,
                        account.closed_at.isoformat() if account.closed_at else None,
                        account.max_leverage,
                    ),
                )

                # Save balances (available and reserved)
                for currency, available_money in account.balance.available.items():
                    reserved_money = account.balance.reserved.get(
                        currency, Money(0, currency)
                    )
                    cursor.execute(
                        """
                        INSERT INTO balances (account_id, currency, available_amount, reserved_amount)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(account_id, currency) DO UPDATE SET
                            available_amount = excluded.available_amount,
                            reserved_amount = excluded.reserved_amount,
                            updated_at = datetime('now')
                        """,
                        (
                            account.account_id,
                            currency.value,
                            available_money.amount,
                            reserved_money.amount,
                        ),
                    )

                # Save transactions
                for tx in account.transactions:
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO transactions
                        (id, account_id, transaction_type, currency, amount, description, reference_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            tx.transaction_id,
                            account.account_id,
                            tx.transaction_type.value,
                            tx.amount.currency.value,
                            tx.amount.amount,
                            tx.description,
                            tx.reference_id,
                        ),
                    )

                logger.debug(f"Account saved: {account.account_id}")

        except Exception as e:
            logger.error(f"Failed to save account: {e}")
            raise

    def find_by_id(self, account_id: str) -> Optional[Account]:
        """
        Find account by ID.

        Args:
            account_id: Account ID

        Returns:
            Account if found, None otherwise

        Raises:
            sqlite3.DatabaseError: If query fails
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                # Fetch account
                cursor.execute("SELECT * FROM accounts WHERE id = ?", (account_id,))
                account_row = cursor.fetchone()

                if not account_row:
                    return None

                # Fetch balances
                cursor.execute(
                    "SELECT currency, available_amount, reserved_amount FROM balances WHERE account_id = ?",
                    (account_id,),
                )
                balance_rows = cursor.fetchall()

                # Fetch transactions
                cursor.execute(
                    "SELECT id, transaction_type, currency, amount, description, reference_id, created_at FROM transactions WHERE account_id = ? ORDER BY created_at",
                    (account_id,),
                )
                transaction_rows = cursor.fetchall()

                # Reconstruct Account
                return self._row_to_account(
                    account_row, balance_rows, transaction_rows
                )

        except Exception as e:
            logger.error(f"Failed to find account: {e}")
            raise

    def find_by_name(self, name: str) -> Optional[Account]:
        """
        Find account by name.

        Args:
            name: Account name

        Returns:
            Account if found, None otherwise

        Raises:
            sqlite3.DatabaseError: If query fails
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT id FROM accounts WHERE name = ? LIMIT 1", (name,)
                )
                row = cursor.fetchone()

                if not row:
                    return None

                return self.find_by_id(row["id"])

        except Exception as e:
            logger.error(f"Failed to find account by name: {e}")
            raise

    def find_all(self) -> List[Account]:
        """
        Find all accounts.

        Returns:
            List of all accounts

        Raises:
            sqlite3.DatabaseError: If query fails
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute("SELECT id FROM accounts ORDER BY created_at DESC")
                account_ids = [row["id"] for row in cursor.fetchall()]

                accounts = []
                for account_id in account_ids:
                    account = self.find_by_id(account_id)
                    if account:
                        accounts.append(account)

                return accounts

        except Exception as e:
            logger.error(f"Failed to find all accounts: {e}")
            raise

    def find_all_active(self) -> List[Account]:
        """
        Find all active accounts.

        Returns:
            List of active accounts

        Raises:
            sqlite3.DatabaseError: If query fails
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT id FROM accounts WHERE is_active = 1 ORDER BY created_at DESC"
                )
                account_ids = [row["id"] for row in cursor.fetchall()]

                accounts = []
                for account_id in account_ids:
                    account = self.find_by_id(account_id)
                    if account:
                        accounts.append(account)

                return accounts

        except Exception as e:
            logger.error(f"Failed to find active accounts: {e}")
            raise

    def delete(self, account_id: str) -> bool:
        """
        Delete account by ID.

        Cascades to related balances and transactions.

        Args:
            account_id: Account ID to delete

        Returns:
            True if deleted, False if not found

        Raises:
            sqlite3.DatabaseError: If delete fails
        """
        try:
            affected = self.db.execute_update(
                "DELETE FROM accounts WHERE id = ?", (account_id,)
            )
            return affected > 0

        except Exception as e:
            logger.error(f"Failed to delete account: {e}")
            raise

    def exists(self, account_id: str) -> bool:
        """
        Check if account exists.

        Args:
            account_id: Account ID to check

        Returns:
            True if exists, False otherwise

        Raises:
            sqlite3.DatabaseError: If query fails
        """
        try:
            rows = self.db.execute_query(
                "SELECT 1 FROM accounts WHERE id = ? LIMIT 1", (account_id,)
            )
            return len(rows) > 0

        except Exception as e:
            logger.error(f"Failed to check account existence: {e}")
            raise

    def _row_to_account(
        self, account_row, balance_rows, transaction_rows
    ) -> Account:
        """
        Convert database rows to Account entity.

        Args:
            account_row: Account database row
            balance_rows: Balance database rows
            transaction_rows: Transaction database rows

        Returns:
            Reconstructed Account entity
        """
        from datetime import datetime

        # Reconstruct balance
        balance = Balance()
        for balance_row in balance_rows:
            currency = Currency.from_string(balance_row["currency"])

            # Add available balance
            available_money = Money(
                amount=balance_row["available_amount"],
                currency=currency,
            )
            balance.available[currency] = available_money

            # Add reserved balance if non-zero
            reserved_amount = balance_row["reserved_amount"]
            if reserved_amount > 0:
                reserved_money = Money(
                    amount=reserved_amount,
                    currency=currency,
                )
                balance.reserved[currency] = reserved_money

        # Reconstruct transactions
        transactions = []
        for tx_row in transaction_rows:
            currency = Currency.from_string(tx_row["currency"])
            money = Money(
                amount=tx_row["amount"],
                currency=currency,
            )
            tx = Transaction(
                transaction_type=TransactionType(tx_row["transaction_type"]),
                amount=money,
                description=tx_row["description"],
                reference_id=tx_row["reference_id"],
            )
            tx.transaction_id = tx_row["id"]
            tx.timestamp = datetime.fromisoformat(tx_row["created_at"])
            transactions.append(tx)

        # Reconstruct account
        account = Account(
            account_id=account_row["id"],
            name=account_row["name"],
            balance=balance,
            initial_balance=Balance(),  # Could be stored separately if needed
            transactions=transactions,
            created_at=datetime.fromisoformat(account_row["created_at"]),
            closed_at=(
                datetime.fromisoformat(account_row["closed_at"])
                if account_row["closed_at"]
                else None
            ),
            is_active=bool(account_row["is_active"]),
            leverage=account_row["leverage"],
            max_leverage=account_row["max_leverage"],
        )

        return account
