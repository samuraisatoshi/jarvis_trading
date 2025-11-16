"""Transaction entity for account domain."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from ..value_objects.money import Money


class TransactionType(Enum):
    """Enumeration of transaction types."""

    DEPOSIT = "DEPOSIT"          # Initial deposit
    WITHDRAWAL = "WITHDRAWAL"    # Withdrawal
    BUY = "BUY"                  # Buy order executed
    SELL = "SELL"                # Sell order executed
    FEE = "FEE"                  # Trading fee
    DIVIDEND = "DIVIDEND"        # Dividend/reward
    LIQUIDATION = "LIQUIDATION"  # Position liquidated


@dataclass
class Transaction:
    """
    Entity representing a transaction in account history.

    Immutable transaction record with full audit trail.

    Attributes:
        transaction_id: Unique transaction identifier
        transaction_type: Type of transaction
        amount: Money amount of transaction
        timestamp: When transaction occurred
        description: Human-readable description
        reference_id: Optional reference to related entity (order, position)
        metadata: Additional transaction metadata
    """

    transaction_type: TransactionType
    amount: Money
    transaction_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    description: str = field(default="")
    reference_id: Optional[str] = field(default=None)
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate transaction after initialization."""
        if not isinstance(self.transaction_type, TransactionType):
            raise TypeError("transaction_type must be TransactionType enum")

        if not isinstance(self.amount, Money):
            raise TypeError("amount must be Money value object")

        if not isinstance(self.timestamp, datetime):
            raise TypeError("timestamp must be datetime")

        if self.amount.amount <= 0:
            raise ValueError("Transaction amount must be positive")

    def __hash__(self) -> int:
        """Make transaction hashable by ID."""
        return hash(self.transaction_id)

    def __eq__(self, other: object) -> bool:
        """Check equality by transaction ID."""
        if not isinstance(other, Transaction):
            return NotImplemented
        return self.transaction_id == other.transaction_id

    def get_summary(self) -> str:
        """Get transaction summary.

        Returns:
            Human-readable transaction summary
        """
        return (
            f"{self.transaction_type.value}: {self.amount} "
            f"- {self.description} ({self.timestamp.isoformat()})"
        )
