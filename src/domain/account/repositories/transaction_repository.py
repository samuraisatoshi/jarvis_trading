"""Transaction repository for querying and persisting transactions."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional, Tuple

from ..entities.transaction import Transaction, TransactionType
from ..value_objects.currency import Currency


class TransactionRepository(ABC):
    """
    Repository abstraction for Transaction persistence and queries.

    Provides advanced queries for audit trail, analytics, and reconciliation.
    """

    @abstractmethod
    def save(self, transaction: Transaction, account_id: str) -> None:
        """
        Save transaction.

        Args:
            transaction: Transaction to save
            account_id: Associated account ID

        Raises:
            RepositoryException: If save fails
        """
        pass

    @abstractmethod
    def find_by_id(self, transaction_id: str) -> Optional[Transaction]:
        """
        Find transaction by ID.

        Args:
            transaction_id: Transaction ID

        Returns:
            Transaction if found, None otherwise

        Raises:
            RepositoryException: If query fails
        """
        pass

    @abstractmethod
    def find_by_account(self, account_id: str, limit: int = 100) -> List[Transaction]:
        """
        Find recent transactions for account.

        Args:
            account_id: Account ID
            limit: Maximum results

        Returns:
            List of transactions sorted by timestamp DESC

        Raises:
            RepositoryException: If query fails
        """
        pass

    @abstractmethod
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
            RepositoryException: If query fails
        """
        pass

    @abstractmethod
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
            RepositoryException: If query fails
        """
        pass

    @abstractmethod
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
            RepositoryException: If query fails
        """
        pass

    @abstractmethod
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
            RepositoryException: If query fails
        """
        pass

    @abstractmethod
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
            RepositoryException: If query fails
        """
        pass

    @abstractmethod
    def get_transaction_count(self, account_id: str) -> int:
        """
        Get total transaction count.

        Args:
            account_id: Account ID

        Returns:
            Number of transactions

        Raises:
            RepositoryException: If query fails
        """
        pass

    @abstractmethod
    def delete_by_account(self, account_id: str) -> int:
        """
        Delete all transactions for account.

        Args:
            account_id: Account ID

        Returns:
            Number of deleted transactions

        Raises:
            RepositoryException: If delete fails
        """
        pass

    @abstractmethod
    def export_to_csv(self, account_id: str, filepath: str) -> None:
        """
        Export transactions to CSV.

        Args:
            account_id: Account ID
            filepath: Output file path

        Raises:
            OSError: If export fails
        """
        pass

    @abstractmethod
    def export_to_json(self, account_id: str, filepath: str) -> None:
        """
        Export transactions to JSON.

        Args:
            account_id: Account ID
            filepath: Output file path

        Raises:
            OSError: If export fails
        """
        pass
