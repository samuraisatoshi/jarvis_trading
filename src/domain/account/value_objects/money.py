"""Money value object for account domain."""

from dataclasses import dataclass
from typing import Union

from .currency import Currency


@dataclass(frozen=True)
class Money:
    """
    Value Object representing a monetary amount in a specific currency.

    Immutable value object that ensures type-safe handling of money amounts.

    Attributes:
        amount: Numeric amount (can be positive or negative)
        currency: Currency of the amount
    """

    amount: Union[int, float]
    currency: Currency

    def __post_init__(self) -> None:
        """Validate money after initialization."""
        if isinstance(self.amount, (int, float)):
            if self.amount < 0:
                raise ValueError("Money amount cannot be negative")
        else:
            raise TypeError("Money amount must be numeric")

        if not isinstance(self.currency, Currency):
            raise TypeError("Currency must be a Currency enum value")

    def __add__(self, other: "Money") -> "Money":
        """Add two Money objects.

        Args:
            other: Money object to add

        Returns:
            New Money object with sum

        Raises:
            ValueError: If currencies don't match
        """
        if self.currency != other.currency:
            raise ValueError(
                f"Cannot add {self.currency} and {other.currency}"
            )
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        """Subtract Money object from another.

        Args:
            other: Money object to subtract

        Returns:
            New Money object with difference

        Raises:
            ValueError: If result is negative or currencies don't match
        """
        if self.currency != other.currency:
            raise ValueError(
                f"Cannot subtract {other.currency} from {self.currency}"
            )
        result = self.amount - other.amount
        if result < 0:
            raise ValueError("Subtraction would result in negative balance")
        return Money(result, self.currency)

    def __mul__(self, scalar: float) -> "Money":
        """Multiply Money by scalar.

        Args:
            scalar: Numeric scalar

        Returns:
            New Money object with multiplied amount

        Raises:
            ValueError: If scalar is negative or result is negative
        """
        if scalar < 0:
            raise ValueError("Scalar cannot be negative")
        result = self.amount * scalar
        if result < 0:
            raise ValueError("Multiplication would result in negative balance")
        return Money(result, self.currency)

    def __truediv__(self, scalar: float) -> "Money":
        """Divide Money by scalar.

        Args:
            scalar: Numeric scalar

        Returns:
            New Money object with divided amount

        Raises:
            ValueError: If scalar is negative or zero, or result is negative
        """
        if scalar <= 0:
            raise ValueError("Divisor must be positive")
        result = self.amount / scalar
        if result < 0:
            raise ValueError("Division would result in negative balance")
        return Money(result, self.currency)

    def __eq__(self, other: object) -> bool:
        """Check equality with another Money object.

        Args:
            other: Object to compare

        Returns:
            True if amounts and currencies match
        """
        if not isinstance(other, Money):
            return NotImplemented
        return self.amount == other.amount and self.currency == other.currency

    def __lt__(self, other: "Money") -> bool:
        """Compare Money objects.

        Args:
            other: Money object to compare

        Returns:
            True if self < other

        Raises:
            ValueError: If currencies don't match
        """
        if self.currency != other.currency:
            raise ValueError(
                f"Cannot compare {self.currency} with {other.currency}"
            )
        return self.amount < other.amount

    def __le__(self, other: "Money") -> bool:
        """Compare Money objects.

        Args:
            other: Money object to compare

        Returns:
            True if self <= other

        Raises:
            ValueError: If currencies don't match
        """
        if self.currency != other.currency:
            raise ValueError(
                f"Cannot compare {self.currency} with {other.currency}"
            )
        return self.amount <= other.amount

    def __gt__(self, other: "Money") -> bool:
        """Compare Money objects.

        Args:
            other: Money object to compare

        Returns:
            True if self > other

        Raises:
            ValueError: If currencies don't match
        """
        if self.currency != other.currency:
            raise ValueError(
                f"Cannot compare {self.currency} with {other.currency}"
            )
        return self.amount > other.amount

    def __ge__(self, other: "Money") -> bool:
        """Compare Money objects.

        Args:
            other: Money object to compare

        Returns:
            True if self >= other

        Raises:
            ValueError: If currencies don't match
        """
        if self.currency != other.currency:
            raise ValueError(
                f"Cannot compare {self.currency} with {other.currency}"
            )
        return self.amount >= other.amount

    def __repr__(self) -> str:
        """Return string representation.

        Returns:
            String representation in format "amount CURRENCY"
        """
        decimal_places = Currency.get_decimal_places(self.currency)
        formatted_amount = f"{self.amount:.{decimal_places}f}"
        return f"{formatted_amount} {self.currency.value}"

    def is_zero(self) -> bool:
        """Check if money amount is zero.

        Returns:
            True if amount is zero
        """
        return self.amount == 0

    def is_positive(self) -> bool:
        """Check if money amount is positive.

        Returns:
            True if amount > 0
        """
        return self.amount > 0
