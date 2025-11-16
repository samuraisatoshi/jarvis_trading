"""Tests for Balance entity."""

import pytest

from src.domain.account.entities.balance import Balance
from src.domain.account.value_objects.currency import Currency
from src.domain.account.value_objects.money import Money


class TestBalanceCreation:
    """Test Balance entity creation."""

    def test_create_empty_balance(self) -> None:
        """Test creating empty Balance."""
        balance = Balance()
        assert len(balance.available) == 0
        assert len(balance.reserved) == 0

    def test_create_balance_with_initial_funds(self) -> None:
        """Test creating Balance with initial funds."""
        money = Money(1000, Currency.USDT)
        balance = Balance(available={Currency.USDT: money})
        assert balance.get_available(Currency.USDT) == money

    def test_create_balance_with_reserved_funds(self) -> None:
        """Test creating Balance with reserved funds."""
        money = Money(100, Currency.USDT)
        balance = Balance(reserved={Currency.USDT: money})
        assert balance.get_reserved(Currency.USDT) == money


class TestBalanceOperations:
    """Test Balance operations."""

    def test_add_available_new_currency(self) -> None:
        """Test adding available balance for new currency."""
        balance = Balance()
        money = Money(1000, Currency.USDT)
        balance.add_available(money)
        assert balance.get_available(Currency.USDT) == money

    def test_add_available_existing_currency(self) -> None:
        """Test adding to existing available balance."""
        money1 = Money(1000, Currency.USDT)
        balance = Balance(available={Currency.USDT: money1})
        money2 = Money(500, Currency.USDT)
        balance.add_available(money2)
        assert balance.get_available(Currency.USDT).amount == 1500

    def test_deduct_available_success(self) -> None:
        """Test deducting from available balance."""
        money = Money(1000, Currency.USDT)
        balance = Balance(available={Currency.USDT: money})
        balance.deduct_available(Money(300, Currency.USDT))
        assert balance.get_available(Currency.USDT).amount == 700

    def test_deduct_available_insufficient_balance(self) -> None:
        """Test deducting more than available."""
        money = Money(100, Currency.USDT)
        balance = Balance(available={Currency.USDT: money})
        with pytest.raises(ValueError, match="Insufficient"):
            balance.deduct_available(Money(200, Currency.USDT))

    def test_deduct_available_nonexistent_currency(self) -> None:
        """Test deducting from nonexistent currency."""
        balance = Balance()
        with pytest.raises(ValueError):
            balance.deduct_available(Money(100, Currency.USDT))

    def test_get_total_balance(self) -> None:
        """Test getting total balance (available + reserved)."""
        available = Money(1000, Currency.USDT)
        reserved = Money(200, Currency.USDT)
        balance = Balance(
            available={Currency.USDT: available},
            reserved={Currency.USDT: reserved},
        )
        total = balance.get_total(Currency.USDT)
        assert total.amount == 1200

    def test_get_total_no_reserved(self) -> None:
        """Test getting total with no reserved balance."""
        available = Money(1000, Currency.USDT)
        balance = Balance(available={Currency.USDT: available})
        total = balance.get_total(Currency.USDT)
        assert total.amount == 1000

    def test_reserve_balance(self) -> None:
        """Test reserving balance."""
        available = Money(1000, Currency.USDT)
        balance = Balance(available={Currency.USDT: available})
        balance.reserve(Money(300, Currency.USDT))
        assert balance.get_available(Currency.USDT).amount == 700
        assert balance.get_reserved(Currency.USDT).amount == 300

    def test_reserve_insufficient_balance(self) -> None:
        """Test reserving more than available."""
        available = Money(100, Currency.USDT)
        balance = Balance(available={Currency.USDT: available})
        with pytest.raises(ValueError, match="Insufficient"):
            balance.reserve(Money(200, Currency.USDT))

    def test_unreserve_balance(self) -> None:
        """Test unreserving balance."""
        available = Money(700, Currency.USDT)
        reserved = Money(300, Currency.USDT)
        balance = Balance(
            available={Currency.USDT: available},
            reserved={Currency.USDT: reserved},
        )
        balance.unreserve(Money(100, Currency.USDT))
        assert balance.get_available(Currency.USDT).amount == 800
        assert balance.get_reserved(Currency.USDT).amount == 200

    def test_unreserve_insufficient_reserved(self) -> None:
        """Test unreserving more than reserved."""
        reserved = Money(100, Currency.USDT)
        balance = Balance(reserved={Currency.USDT: reserved})
        with pytest.raises(ValueError, match="Insufficient"):
            balance.unreserve(Money(200, Currency.USDT))

    def test_reserve_and_unreserve_workflow(self) -> None:
        """Test complete reserve and unreserve workflow."""
        # Start with $1000
        balance = Balance(available={Currency.USDT: Money(1000, Currency.USDT)})

        # Reserve $500
        balance.reserve(Money(500, Currency.USDT))
        assert balance.get_available(Currency.USDT).amount == 500
        assert balance.get_reserved(Currency.USDT).amount == 500

        # Unreserve $200
        balance.unreserve(Money(200, Currency.USDT))
        assert balance.get_available(Currency.USDT).amount == 700
        assert balance.get_reserved(Currency.USDT).amount == 300

        # Unreserve remaining
        balance.unreserve(Money(300, Currency.USDT))
        assert balance.get_available(Currency.USDT).amount == 1000
        assert balance.get_reserved(Currency.USDT).amount == 0


class TestBalanceSummary:
    """Test Balance summary methods."""

    def test_get_summary_single_currency(self) -> None:
        """Test getting balance summary."""
        balance = Balance(available={Currency.USDT: Money(1000, Currency.USDT)})
        summary = balance.get_summary()
        assert summary == {"USDT": 1000}

    def test_get_summary_multiple_currencies(self) -> None:
        """Test getting balance summary with multiple currencies."""
        balance = Balance(
            available={
                Currency.USDT: Money(1000, Currency.USDT),
                Currency.BTC: Money(0.5, Currency.BTC),
            }
        )
        summary = balance.get_summary()
        assert summary["USDT"] == 1000
        assert summary["BTC"] == 0.5

    def test_get_reserved_nonexistent(self) -> None:
        """Test getting reserved balance for nonexistent currency."""
        balance = Balance()
        reserved = balance.get_reserved(Currency.USDT)
        assert reserved.amount == 0
