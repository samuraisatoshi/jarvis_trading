"""Account entity for paper trading."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from ..value_objects.currency import Currency
from ..value_objects.money import Money
from .balance import Balance
from .transaction import Transaction, TransactionType


@dataclass
class Account:
    """
    Entity representing a trading account.

    Maintains account state including balance, transaction history,
    and performance metrics.

    Attributes:
        account_id: Unique account identifier
        name: Account name
        balance: Current balance object
        initial_balance: Initial balance snapshot
        transactions: Transaction history
        created_at: Account creation timestamp
        closed_at: Account closure timestamp (if closed)
        is_active: Whether account is active
        leverage: Current leverage multiplier (1.0 = no leverage)
        max_leverage: Maximum allowed leverage
    """

    account_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = field(default="Paper Trading Account")
    balance: Balance = field(default_factory=Balance)
    initial_balance: Balance = field(default_factory=Balance)
    transactions: List[Transaction] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    closed_at: Optional[datetime] = field(default=None)
    is_active: bool = field(default=True)
    leverage: float = field(default=1.0)
    max_leverage: float = field(default=3.0)

    def __post_init__(self) -> None:
        """Validate account after initialization."""
        if not isinstance(self.balance, Balance):
            raise TypeError("balance must be Balance object")
        if not isinstance(self.initial_balance, Balance):
            raise TypeError("initial_balance must be Balance object")
        if self.leverage < 1.0 or self.leverage > self.max_leverage:
            raise ValueError(
                f"leverage must be between 1.0 and {self.max_leverage}"
            )

    def __hash__(self) -> int:
        """Make account hashable by ID."""
        return hash(self.account_id)

    def __eq__(self, other: object) -> bool:
        """Check equality by account ID."""
        if not isinstance(other, Account):
            return NotImplemented
        return self.account_id == other.account_id

    def deposit(self, money: Money, description: str = "Initial deposit") -> None:
        """Add funds to account.

        Args:
            money: Money to deposit
            description: Transaction description

        Raises:
            ValueError: If account is closed
        """
        if not self.is_active:
            raise ValueError("Cannot deposit to closed account")

        self.balance.add_available(money)
        transaction = Transaction(
            transaction_type=TransactionType.DEPOSIT,
            amount=money,
            description=description,
        )
        self.transactions.append(transaction)

    def withdraw(self, money: Money, description: str = "Withdrawal") -> None:
        """Withdraw funds from account.

        Args:
            money: Money to withdraw
            description: Transaction description

        Raises:
            ValueError: If account is closed or insufficient funds
        """
        if not self.is_active:
            raise ValueError("Cannot withdraw from closed account")

        self.balance.deduct_available(money)
        transaction = Transaction(
            transaction_type=TransactionType.WITHDRAWAL,
            amount=money,
            description=description,
        )
        self.transactions.append(transaction)

    def record_trade(
        self,
        transaction_type: TransactionType,
        amount: Money,
        description: str,
        reference_id: Optional[str] = None,
    ) -> None:
        """Record a trade (buy/sell) transaction.

        Args:
            transaction_type: BUY or SELL
            amount: Amount of currency traded
            description: Trade description
            reference_id: Reference to order or position

        Raises:
            ValueError: If transaction type is invalid
        """
        if transaction_type not in (TransactionType.BUY, TransactionType.SELL):
            raise ValueError("Must be BUY or SELL transaction")

        transaction = Transaction(
            transaction_type=transaction_type,
            amount=amount,
            description=description,
            reference_id=reference_id,
        )
        self.transactions.append(transaction)

    def record_fee(self, money: Money, description: str) -> None:
        """Record a trading fee.

        Args:
            money: Fee amount
            description: Fee description
        """
        self.balance.deduct_available(money)
        transaction = Transaction(
            transaction_type=TransactionType.FEE,
            amount=money,
            description=description,
        )
        self.transactions.append(transaction)

    def get_total_balance(self, currency: Currency) -> Money:
        """Get total balance for currency.

        Args:
            currency: Currency to get balance for

        Returns:
            Total Money amount

        Raises:
            KeyError: If currency not found
        """
        return self.balance.get_total(currency)

    def get_available_balance(self, currency: Currency) -> Money:
        """Get available balance for currency.

        Args:
            currency: Currency to get balance for

        Returns:
            Available Money amount

        Raises:
            KeyError: If currency not found
        """
        return self.balance.get_available(currency)

    def get_transaction_history(self) -> List[Transaction]:
        """Get all transactions.

        Returns:
            List of transactions sorted by timestamp
        """
        return sorted(self.transactions, key=lambda t: t.timestamp)

    def get_transaction_count(self) -> int:
        """Get count of transactions.

        Returns:
            Number of transactions
        """
        return len(self.transactions)

    def close(self) -> None:
        """Close account.

        Raises:
            ValueError: If account already closed
        """
        if not self.is_active:
            raise ValueError("Account already closed")
        self.is_active = False
        self.closed_at = datetime.utcnow()

    def reopen(self) -> None:
        """Reopen closed account.

        Raises:
            ValueError: If account not closed
        """
        if self.is_active:
            raise ValueError("Account already open")
        self.is_active = True
        self.closed_at = None

    def set_leverage(self, leverage: float) -> None:
        """Set account leverage.

        Args:
            leverage: Leverage multiplier (1.0 = no leverage)

        Raises:
            ValueError: If leverage out of range
        """
        if leverage < 1.0 or leverage > self.max_leverage:
            raise ValueError(
                f"leverage must be between 1.0 and {self.max_leverage}"
            )
        self.leverage = leverage

    def get_summary(self) -> dict:
        """Get account summary.

        Returns:
            Dictionary with account information
        """
        return {
            "account_id": self.account_id,
            "name": self.name,
            "is_active": self.is_active,
            "balance": self.balance.get_summary(),
            "leverage": self.leverage,
            "transaction_count": self.get_transaction_count(),
            "created_at": self.created_at.isoformat(),
        }
