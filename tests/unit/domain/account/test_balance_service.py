"""Tests for BalanceService."""

import pytest

from src.domain.account.entities.account import Account
from src.domain.account.entities.balance import Balance
from src.domain.account.services.balance_service import BalanceService
from src.domain.account.value_objects.currency import Currency
from src.domain.account.value_objects.money import Money


class TestBalanceServiceQueries:
    """Test BalanceService query methods."""

    def test_get_total_balance(self) -> None:
        """Test getting total balance."""
        account = Account()
        account.deposit(Money(1000, Currency.USDT))

        total = BalanceService.get_total_balance_in_currency(
            account, Currency.USDT
        )
        assert total.amount == 1000

    def test_get_available_balance(self) -> None:
        """Test getting available balance."""
        account = Account()
        account.deposit(Money(1000, Currency.USDT))

        available = BalanceService.get_available_balance_in_currency(
            account, Currency.USDT
        )
        assert available.amount == 1000

    def test_get_reserved_balance(self) -> None:
        """Test getting reserved balance."""
        account = Account()
        account.deposit(Money(1000, Currency.USDT))
        account.balance.reserve(Money(200, Currency.USDT))

        reserved = BalanceService.get_reserved_balance_in_currency(
            account, Currency.USDT
        )
        assert reserved.amount == 200

    def test_get_all_available_balances(self) -> None:
        """Test getting all available balances."""
        account = Account()
        account.deposit(Money(1000, Currency.USDT))
        account.deposit(Money(0.5, Currency.BTC))

        balances = BalanceService.get_all_available_balances(account)
        assert balances["USDT"] == 1000
        assert balances["BTC"] == 0.5


class TestBalanceServiceTradeValidation:
    """Test BalanceService trade validation."""

    def test_can_trade_sufficient_balance(self) -> None:
        """Test can_trade with sufficient balance."""
        account = Account()
        account.deposit(Money(1000, Currency.USDT))

        can_trade = BalanceService.can_trade(account, Money(500, Currency.USDT))
        assert can_trade

    def test_can_trade_insufficient_balance(self) -> None:
        """Test can_trade with insufficient balance."""
        account = Account()
        account.deposit(Money(100, Currency.USDT))

        can_trade = BalanceService.can_trade(account, Money(500, Currency.USDT))
        assert not can_trade

    def test_can_trade_exact_balance(self) -> None:
        """Test can_trade with exact balance."""
        account = Account()
        account.deposit(Money(500, Currency.USDT))

        can_trade = BalanceService.can_trade(account, Money(500, Currency.USDT))
        assert can_trade


class TestBalanceServiceBuyingPower:
    """Test BalanceService buying power calculation."""

    def test_calculate_buying_power_no_leverage(self) -> None:
        """Test buying power without leverage."""
        account = Account(leverage=1.0)
        account.deposit(Money(1000, Currency.USDT))

        power = BalanceService.calculate_buying_power(account, Currency.USDT)
        assert power.amount == 1000

    def test_calculate_buying_power_with_leverage(self) -> None:
        """Test buying power with leverage."""
        account = Account(leverage=2.0)
        account.deposit(Money(1000, Currency.USDT))

        power = BalanceService.calculate_buying_power(account, Currency.USDT)
        assert power.amount == 2000

    def test_calculate_buying_power_3x_leverage(self) -> None:
        """Test buying power with 3x leverage."""
        account = Account(leverage=3.0)
        account.deposit(Money(500, Currency.USDT))

        power = BalanceService.calculate_buying_power(account, Currency.USDT)
        assert power.amount == 1500


class TestBalanceServiceUtilization:
    """Test BalanceService utilization calculation."""

    def test_calculate_utilization_no_reserved(self) -> None:
        """Test utilization with no reserved balance."""
        account = Account()
        account.deposit(Money(1000, Currency.USDT))

        util = BalanceService.calculate_utilization_percentage(
            account, Currency.USDT
        )
        assert util == 0.0

    def test_calculate_utilization_partial_reserved(self) -> None:
        """Test utilization with partial reservation."""
        account = Account()
        account.deposit(Money(1000, Currency.USDT))
        account.balance.reserve(Money(200, Currency.USDT))

        util = BalanceService.calculate_utilization_percentage(
            account, Currency.USDT
        )
        assert util == 20.0

    def test_calculate_utilization_fully_reserved(self) -> None:
        """Test utilization with fully reserved balance."""
        account = Account()
        account.deposit(Money(1000, Currency.USDT))
        account.balance.reserve(Money(1000, Currency.USDT))

        util = BalanceService.calculate_utilization_percentage(
            account, Currency.USDT
        )
        assert util == 100.0


class TestBalanceServicePortfolioValue:
    """Test BalanceService portfolio value calculations."""

    def test_get_portfolio_value_single_currency(self) -> None:
        """Test portfolio value with single currency."""
        account = Account()
        account.deposit(Money(1000, Currency.USDT))

        prices = {Currency.USDT: 1.0}
        value = BalanceService.get_portfolio_value(account, prices)
        assert value == 1000

    def test_get_portfolio_value_multiple_currencies(self) -> None:
        """Test portfolio value with multiple currencies."""
        account = Account()
        account.deposit(Money(1000, Currency.USDT))
        account.deposit(Money(1, Currency.BTC))

        prices = {Currency.USDT: 1.0, Currency.BTC: 50000.0}
        value = BalanceService.get_portfolio_value(account, prices)
        assert value == 51000

    def test_get_portfolio_value_missing_price(self) -> None:
        """Test portfolio value with missing price."""
        account = Account()
        account.deposit(Money(1, Currency.BTC))

        prices = {}
        with pytest.raises(KeyError):
            BalanceService.get_portfolio_value(account, prices)

    def test_get_currency_breakdown(self) -> None:
        """Test currency breakdown calculation."""
        account = Account()
        account.deposit(Money(1000, Currency.USDT))
        account.deposit(Money(1, Currency.BTC))

        prices = {Currency.USDT: 1.0, Currency.BTC: 50000.0}
        breakdown = BalanceService.get_currency_breakdown(account, prices)

        assert "USDT" in breakdown
        assert "BTC" in breakdown
        assert breakdown["USDT"]["amount"] == 1000
        assert breakdown["USDT"]["value"] == 1000
        assert breakdown["BTC"]["amount"] == 1
        assert breakdown["BTC"]["value"] == 50000


class TestBalanceServiceReservation:
    """Test BalanceService reservation operations."""

    def test_reserve_for_order(self) -> None:
        """Test reserving balance for order."""
        account = Account()
        account.deposit(Money(1000, Currency.USDT))

        BalanceService.reserve_for_order(account, Money(300, Currency.USDT))
        assert account.balance.get_available(Currency.USDT).amount == 700
        assert account.balance.get_reserved(Currency.USDT).amount == 300

    def test_release_from_order(self) -> None:
        """Test releasing reserved balance."""
        account = Account()
        account.deposit(Money(1000, Currency.USDT))
        BalanceService.reserve_for_order(account, Money(300, Currency.USDT))

        BalanceService.release_from_order(account, Money(300, Currency.USDT))
        assert account.balance.get_available(Currency.USDT).amount == 1000
        assert account.balance.get_reserved(Currency.USDT).amount == 0


class TestBalanceServiceFeeDeduction:
    """Test BalanceService fee operations."""

    def test_deduct_trading_fee(self) -> None:
        """Test deducting trading fee."""
        account = Account()
        account.deposit(Money(1000, Currency.USDT))

        fee = BalanceService.deduct_trading_fee(
            account, Money(1000, Currency.USDT), 0.001
        )
        assert fee.amount == 1.0
        assert account.get_available_balance(Currency.USDT).amount == 999

    def test_deduct_trading_fee_different_percentage(self) -> None:
        """Test fee deduction with different percentage."""
        account = Account()
        account.deposit(Money(1000, Currency.USDT))

        fee = BalanceService.deduct_trading_fee(
            account, Money(500, Currency.USDT), 0.002
        )
        assert fee.amount == 1.0
        assert account.get_available_balance(Currency.USDT).amount == 999
