"""JSON-based implementation of AccountRepository."""

import json
from pathlib import Path
from typing import List, Optional

from src.domain.account.entities.account import Account
from src.domain.account.entities.balance import Balance
from src.domain.account.entities.transaction import Transaction, TransactionType
from src.domain.account.repositories.account_repository import AccountRepository
from src.domain.account.value_objects.currency import Currency
from src.domain.account.value_objects.money import Money


class JsonAccountRepository(AccountRepository):
    """
    JSON file-based implementation of AccountRepository.

    Persists accounts to JSON files in the data directory.
    """

    def __init__(self, data_dir: str = "data"):
        """Initialize repository.

        Args:
            data_dir: Directory for storing JSON files
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.accounts_file = self.data_dir / "accounts.json"
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        """Ensure accounts file exists."""
        if not self.accounts_file.exists():
            self.accounts_file.write_text(json.dumps({}))

    def _load_all_data(self) -> dict:
        """Load all accounts data from file.

        Returns:
            Dictionary of accounts keyed by account_id
        """
        try:
            content = self.accounts_file.read_text()
            return json.loads(content) if content else {}
        except json.JSONDecodeError:
            return {}

    def _save_all_data(self, data: dict) -> None:
        """Save all accounts data to file.

        Args:
            data: Dictionary of accounts to save
        """
        self.accounts_file.write_text(json.dumps(data, indent=2, default=str))

    def _account_to_dict(self, account: Account) -> dict:
        """Convert account to JSON-serializable dictionary.

        Args:
            account: Account to convert

        Returns:
            Dictionary representation
        """
        # Convert transactions
        transactions = []
        for tx in account.transactions:
            transactions.append({
                "transaction_id": tx.transaction_id,
                "type": tx.transaction_type.value,
                "amount": tx.amount.amount,
                "currency": tx.amount.currency.value,
                "timestamp": tx.timestamp.isoformat(),
                "description": tx.description,
                "reference_id": tx.reference_id,
                "metadata": tx.metadata,
            })

        # Convert available balance
        available = {}
        for currency, money in account.balance.available.items():
            available[currency.value] = money.amount

        # Convert reserved balance
        reserved = {}
        for currency, money in account.balance.reserved.items():
            reserved[currency.value] = money.amount

        # Convert initial balance
        initial_available = {}
        for currency, money in account.initial_balance.available.items():
            initial_available[currency.value] = money.amount

        return {
            "account_id": account.account_id,
            "name": account.name,
            "is_active": account.is_active,
            "leverage": account.leverage,
            "max_leverage": account.max_leverage,
            "created_at": account.created_at.isoformat(),
            "closed_at": account.closed_at.isoformat() if account.closed_at else None,
            "balance_available": available,
            "balance_reserved": reserved,
            "initial_balance_available": initial_available,
            "transactions": transactions,
        }

    def _dict_to_account(self, data: dict) -> Account:
        """Convert JSON dictionary to Account entity.

        Args:
            data: Dictionary representation

        Returns:
            Account entity

        Raises:
            ValueError: If data format is invalid
        """
        from datetime import datetime

        try:
            # Reconstruct balance
            available = {}
            for curr_str, amount in data.get("balance_available", {}).items():
                currency = Currency.from_string(curr_str)
                available[currency] = Money(amount, currency)

            reserved = {}
            for curr_str, amount in data.get("balance_reserved", {}).items():
                currency = Currency.from_string(curr_str)
                reserved[currency] = Money(amount, currency)

            balance = Balance(available=available, reserved=reserved)

            # Reconstruct initial balance
            initial_available = {}
            for curr_str, amount in data.get("initial_balance_available", {}).items():
                currency = Currency.from_string(curr_str)
                initial_available[currency] = Money(amount, currency)

            initial_balance = Balance(available=initial_available)

            # Reconstruct transactions
            transactions = []
            for tx_data in data.get("transactions", []):
                currency = Currency.from_string(tx_data["currency"])
                money = Money(tx_data["amount"], currency)
                tx = Transaction(
                    transaction_id=tx_data["transaction_id"],
                    transaction_type=TransactionType[tx_data["type"]],
                    amount=money,
                    timestamp=datetime.fromisoformat(tx_data["timestamp"]),
                    description=tx_data["description"],
                    reference_id=tx_data.get("reference_id"),
                    metadata=tx_data.get("metadata", {}),
                )
                transactions.append(tx)

            # Create account
            account = Account(
                account_id=data["account_id"],
                name=data["name"],
                balance=balance,
                initial_balance=initial_balance,
                transactions=transactions,
                is_active=data["is_active"],
                leverage=data["leverage"],
                max_leverage=data["max_leverage"],
                created_at=datetime.fromisoformat(data["created_at"]),
            )

            if data.get("closed_at"):
                account.closed_at = datetime.fromisoformat(data["closed_at"])

            return account

        except (KeyError, ValueError, TypeError) as e:
            raise ValueError(f"Invalid account data format: {e}") from e

    def save(self, account: Account) -> None:
        """Save account to JSON.

        Args:
            account: Account to save
        """
        data = self._load_all_data()
        data[account.account_id] = self._account_to_dict(account)
        self._save_all_data(data)

    def find_by_id(self, account_id: str) -> Optional[Account]:
        """Find account by ID.

        Args:
            account_id: Account ID to search for

        Returns:
            Account if found, None otherwise
        """
        data = self._load_all_data()
        account_data = data.get(account_id)
        return self._dict_to_account(account_data) if account_data else None

    def find_by_name(self, name: str) -> Optional[Account]:
        """Find account by name.

        Args:
            name: Account name to search for

        Returns:
            Account if found, None otherwise
        """
        data = self._load_all_data()
        for account_data in data.values():
            if account_data["name"] == name:
                return self._dict_to_account(account_data)
        return None

    def find_all(self) -> List[Account]:
        """Get all accounts.

        Returns:
            List of all accounts
        """
        data = self._load_all_data()
        return [self._dict_to_account(acc_data) for acc_data in data.values()]

    def find_all_active(self) -> List[Account]:
        """Get all active accounts.

        Returns:
            List of active accounts
        """
        data = self._load_all_data()
        return [
            self._dict_to_account(acc_data)
            for acc_data in data.values()
            if acc_data.get("is_active", True)
        ]

    def delete(self, account_id: str) -> bool:
        """Delete account by ID.

        Args:
            account_id: Account ID to delete

        Returns:
            True if deleted, False if not found
        """
        data = self._load_all_data()
        if account_id in data:
            del data[account_id]
            self._save_all_data(data)
            return True
        return False

    def exists(self, account_id: str) -> bool:
        """Check if account exists.

        Args:
            account_id: Account ID to check

        Returns:
            True if exists, False otherwise
        """
        data = self._load_all_data()
        return account_id in data
