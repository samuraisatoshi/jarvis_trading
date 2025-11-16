"""Balance entity for account domain."""

from dataclasses import dataclass, field
from typing import Dict

from ..value_objects.currency import Currency
from ..value_objects.money import Money


@dataclass
class Balance:
    """
    Entity representing multi-currency balance in account.

    Tracks available balance and reserved balance (in orders) per currency.

    Attributes:
        available: Available balance per currency (can trade/withdraw)
        reserved: Reserved balance per currency (in open orders)
    """

    available: Dict[Currency, Money] = field(default_factory=dict)
    reserved: Dict[Currency, Money] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate balance after initialization."""
        for currency, money in self.available.items():
            if not isinstance(currency, Currency):
                raise TypeError("Balance keys must be Currency enum")
            if not isinstance(money, Money):
                raise TypeError("Balance values must be Money objects")
            if money.currency != currency:
                raise ValueError(
                    f"Money currency {money.currency} must match key {currency}"
                )

        for currency, money in self.reserved.items():
            if not isinstance(currency, Currency):
                raise TypeError("Reserved keys must be Currency enum")
            if not isinstance(money, Money):
                raise TypeError("Reserved values must be Money objects")
            if money.currency != currency:
                raise ValueError(
                    f"Money currency {money.currency} must match key {currency}"
                )

    def get_total(self, currency: Currency) -> Money:
        """Get total balance (available + reserved) for currency.

        Args:
            currency: Currency to get balance for

        Returns:
            Total Money amount

        Raises:
            KeyError: If currency not found in available balance
        """
        available = self.available.get(currency)
        if available is None:
            raise KeyError(f"Currency {currency} not in available balance")

        reserved = self.reserved.get(currency, Money(0, currency))
        return available + reserved

    def get_available(self, currency: Currency) -> Money:
        """Get available balance for currency.

        Args:
            currency: Currency to get balance for

        Returns:
            Available Money amount

        Raises:
            KeyError: If currency not found
        """
        if currency not in self.available:
            raise KeyError(f"Currency {currency} not in available balance")
        return self.available[currency]

    def get_reserved(self, currency: Currency) -> Money:
        """Get reserved balance for currency.

        Args:
            currency: Currency to get reserved balance for

        Returns:
            Reserved Money amount (0 if none)
        """
        return self.reserved.get(currency, Money(0, currency))

    def add_available(self, money: Money) -> None:
        """Add to available balance.

        Args:
            money: Money to add

        Raises:
            ValueError: If currency already exists with different value
        """
        if money.currency in self.available:
            self.available[money.currency] = (
                self.available[money.currency] + money
            )
        else:
            self.available[money.currency] = money

    def deduct_available(self, money: Money) -> None:
        """Deduct from available balance.

        Args:
            money: Money to deduct

        Raises:
            ValueError: If insufficient available balance
        """
        if money.currency not in self.available:
            raise ValueError(f"No available balance for {money.currency}")

        current = self.available[money.currency]
        if current.amount < money.amount:
            raise ValueError(
                f"Insufficient balance: {current.amount} < {money.amount}"
            )

        self.available[money.currency] = current - money

    def reserve(self, money: Money) -> None:
        """Reserve balance from available.

        Args:
            money: Money to reserve

        Raises:
            ValueError: If insufficient available balance
        """
        self.deduct_available(money)

        if money.currency in self.reserved:
            self.reserved[money.currency] = (
                self.reserved[money.currency] + money
            )
        else:
            self.reserved[money.currency] = money

    def unreserve(self, money: Money) -> None:
        """Release reserved balance back to available.

        Args:
            money: Money to unreserve

        Raises:
            ValueError: If insufficient reserved balance
        """
        if money.currency not in self.reserved:
            raise ValueError(f"No reserved balance for {money.currency}")

        current_reserved = self.reserved[money.currency]
        if current_reserved.amount < money.amount:
            raise ValueError(
                f"Insufficient reserved: {current_reserved.amount} "
                f"< {money.amount}"
            )

        self.reserved[money.currency] = current_reserved - money
        self.add_available(money)

    def get_summary(self) -> Dict[str, float]:
        """Get balance summary as dictionary.

        Returns:
            Dictionary mapping currency symbols to available amounts
        """
        return {
            currency.value: self.available[currency].amount
            for currency in self.available
        }
