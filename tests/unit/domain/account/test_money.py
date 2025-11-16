"""Tests for Money value object."""

import pytest

from src.domain.account.value_objects.currency import Currency
from src.domain.account.value_objects.money import Money


class TestMoneyCreation:
    """Test Money creation and validation."""

    def test_create_valid_money(self) -> None:
        """Test creating valid Money object."""
        money = Money(100.50, Currency.USDT)
        assert money.amount == 100.50
        assert money.currency == Currency.USDT

    def test_money_with_integer_amount(self) -> None:
        """Test Money with integer amount."""
        money = Money(100, Currency.BTC)
        assert money.amount == 100
        assert isinstance(money.amount, int)

    def test_money_with_zero_amount(self) -> None:
        """Test Money with zero amount."""
        money = Money(0, Currency.USDT)
        assert money.amount == 0
        assert money.is_zero()

    def test_money_negative_amount_raises_error(self) -> None:
        """Test that negative amount raises error."""
        with pytest.raises(ValueError, match="cannot be negative"):
            Money(-100, Currency.USDT)

    def test_money_invalid_type_raises_error(self) -> None:
        """Test that non-numeric amount raises error."""
        with pytest.raises(TypeError, match="must be numeric"):
            Money("100", Currency.USDT)  # type: ignore

    def test_money_invalid_currency_raises_error(self) -> None:
        """Test that invalid currency raises error."""
        with pytest.raises(TypeError, match="must be a Currency"):
            Money(100, "USDT")  # type: ignore


class TestMoneyOperations:
    """Test Money arithmetic operations."""

    def test_add_money_same_currency(self) -> None:
        """Test adding Money with same currency."""
        m1 = Money(100, Currency.USDT)
        m2 = Money(50, Currency.USDT)
        result = m1 + m2
        assert result.amount == 150
        assert result.currency == Currency.USDT

    def test_add_money_different_currency_raises_error(self) -> None:
        """Test adding Money with different currencies raises error."""
        m1 = Money(100, Currency.USDT)
        m2 = Money(1, Currency.BTC)
        with pytest.raises(ValueError, match="Cannot add"):
            m1 + m2

    def test_subtract_money_same_currency(self) -> None:
        """Test subtracting Money with same currency."""
        m1 = Money(100, Currency.USDT)
        m2 = Money(30, Currency.USDT)
        result = m1 - m2
        assert result.amount == 70
        assert result.currency == Currency.USDT

    def test_subtract_money_insufficient_balance(self) -> None:
        """Test subtracting more than available."""
        m1 = Money(30, Currency.USDT)
        m2 = Money(100, Currency.USDT)
        with pytest.raises(ValueError, match="negative"):
            m1 - m2

    def test_multiply_money_by_scalar(self) -> None:
        """Test multiplying Money by scalar."""
        money = Money(100, Currency.USDT)
        result = money * 2.5
        assert result.amount == 250
        assert result.currency == Currency.USDT

    def test_multiply_money_by_negative_scalar(self) -> None:
        """Test multiplying Money by negative scalar raises error."""
        money = Money(100, Currency.USDT)
        with pytest.raises(ValueError, match="cannot be negative"):
            money * -1

    def test_divide_money_by_scalar(self) -> None:
        """Test dividing Money by scalar."""
        money = Money(100, Currency.USDT)
        result = money / 4
        assert result.amount == 25
        assert result.currency == Currency.USDT

    def test_divide_money_by_zero_raises_error(self) -> None:
        """Test dividing Money by zero raises error."""
        money = Money(100, Currency.USDT)
        with pytest.raises(ValueError, match="must be positive"):
            money / 0

    def test_divide_money_by_negative_raises_error(self) -> None:
        """Test dividing Money by negative raises error."""
        money = Money(100, Currency.USDT)
        with pytest.raises(ValueError, match="must be positive"):
            money / -2


class TestMoneyComparison:
    """Test Money comparison operations."""

    def test_money_equality(self) -> None:
        """Test Money equality."""
        m1 = Money(100, Currency.USDT)
        m2 = Money(100, Currency.USDT)
        assert m1 == m2

    def test_money_inequality(self) -> None:
        """Test Money inequality."""
        m1 = Money(100, Currency.USDT)
        m2 = Money(50, Currency.USDT)
        assert m1 != m2

    def test_money_less_than(self) -> None:
        """Test Money less than comparison."""
        m1 = Money(50, Currency.USDT)
        m2 = Money(100, Currency.USDT)
        assert m1 < m2

    def test_money_less_than_equal(self) -> None:
        """Test Money less than or equal comparison."""
        m1 = Money(100, Currency.USDT)
        m2 = Money(100, Currency.USDT)
        assert m1 <= m2

    def test_money_greater_than(self) -> None:
        """Test Money greater than comparison."""
        m1 = Money(100, Currency.USDT)
        m2 = Money(50, Currency.USDT)
        assert m1 > m2

    def test_money_greater_than_equal(self) -> None:
        """Test Money greater than or equal comparison."""
        m1 = Money(100, Currency.USDT)
        m2 = Money(100, Currency.USDT)
        assert m1 >= m2

    def test_compare_different_currencies_raises_error(self) -> None:
        """Test comparing Money with different currencies raises error."""
        m1 = Money(100, Currency.USDT)
        m2 = Money(1, Currency.BTC)
        with pytest.raises(ValueError, match="Cannot compare"):
            m1 < m2


class TestMoneyProperties:
    """Test Money properties and methods."""

    def test_is_zero(self) -> None:
        """Test is_zero() method."""
        m_zero = Money(0, Currency.USDT)
        m_nonzero = Money(1, Currency.USDT)
        assert m_zero.is_zero()
        assert not m_nonzero.is_zero()

    def test_is_positive(self) -> None:
        """Test is_positive() method."""
        m_zero = Money(0, Currency.USDT)
        m_positive = Money(1, Currency.USDT)
        assert not m_zero.is_positive()
        assert m_positive.is_positive()

    def test_repr(self) -> None:
        """Test string representation."""
        money = Money(100.50, Currency.USDT)
        assert "100.50" in repr(money)
        assert "USDT" in repr(money)

    def test_money_is_immutable(self) -> None:
        """Test that Money is immutable."""
        money = Money(100, Currency.USDT)
        with pytest.raises(AttributeError):
            money.amount = 200  # type: ignore
