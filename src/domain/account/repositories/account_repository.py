"""Account repository interface for account domain."""

from abc import ABC, abstractmethod
from typing import List, Optional

from ..entities.account import Account


class AccountRepository(ABC):
    """
    Repository abstraction for Account persistence.

    Defines interface for saving and retrieving accounts from storage.
    """

    @abstractmethod
    def save(self, account: Account) -> None:
        """Save account to repository.

        Args:
            account: Account entity to save

        Raises:
            RepositoryException: If save fails
        """
        pass

    @abstractmethod
    def find_by_id(self, account_id: str) -> Optional[Account]:
        """Find account by ID.

        Args:
            account_id: Account ID to search for

        Returns:
            Account if found, None otherwise

        Raises:
            RepositoryException: If find fails
        """
        pass

    @abstractmethod
    def find_by_name(self, name: str) -> Optional[Account]:
        """Find account by name.

        Args:
            name: Account name to search for

        Returns:
            Account if found, None otherwise

        Raises:
            RepositoryException: If find fails
        """
        pass

    @abstractmethod
    def find_all(self) -> List[Account]:
        """Get all accounts.

        Returns:
            List of all accounts

        Raises:
            RepositoryException: If find fails
        """
        pass

    @abstractmethod
    def find_all_active(self) -> List[Account]:
        """Get all active accounts.

        Returns:
            List of active accounts

        Raises:
            RepositoryException: If find fails
        """
        pass

    @abstractmethod
    def delete(self, account_id: str) -> bool:
        """Delete account by ID.

        Args:
            account_id: Account ID to delete

        Returns:
            True if deleted, False if not found

        Raises:
            RepositoryException: If delete fails
        """
        pass

    @abstractmethod
    def exists(self, account_id: str) -> bool:
        """Check if account exists.

        Args:
            account_id: Account ID to check

        Returns:
            True if exists, False otherwise

        Raises:
            RepositoryException: If check fails
        """
        pass
