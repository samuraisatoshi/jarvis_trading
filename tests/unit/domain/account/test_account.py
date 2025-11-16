"""Tests for Account entity."""

import pytest

from src.domain.account.entities.account import Account
from src.domain.account.entities.balance import Balance
from src.domain.account.entities.transaction import TransactionType
from src.domain.account.value_objects.currency import Currency
from src.domain.account.value_objects.money import Money


class TestAccountCreation:
    """Test Account entity creation."""

    def test_create_account_with_defaults(self) -> None:
        """Test creating account with default values."""
        account = Account()
        assert account.name == "Paper Trading Account"
        assert account.is_active
        assert account.leverage == 1.0
        assert account.max_leverage == 3.0

    def test_create_account_with_custom_name(self) -> None:
        """Test creating account with custom name."""
        account = Account(name="My Trading Account")
        assert account.name == "My Trading Account"

    def test_account_has_unique_id(self) -> None:
        """Test that each account has unique ID."""
        account1 = Account()
        account2 = Account()
        assert account1.account_id != account2.account_id

    def test_account_invalid_leverage(self) -> None:
        """Test that invalid leverage raises error."""
        with pytest.raises(ValueError, match="between 1.0"):
            Account(leverage=0.5)

        with pytest.raises(ValueError, match="between 1.0"):
            Account(leverage=5.0)


class TestAccountDeposits:
    """Test account deposit operations."""

    def test_deposit_funds(self) -> None:
        """Test depositing funds."""
        account = Account()
        money = Money(1000, Currency.USDT)
        account.deposit(money)
        assert account.get_available_balance(Currency.USDT).amount == 1000

    def test_deposit_multiple_currencies(self) -> None:
        """Test depositing multiple currencies."""
        account = Account()
        account.deposit(Money(1000, Currency.USDT))
        account.deposit(Money(0.5, Currency.BTC))

        assert account.get_available_balance(Currency.USDT).amount == 1000
        assert account.get_available_balance(Currency.BTC).amount == 0.5

    def test_deposit_to_closed_account_raises_error(self) -> None:
        """Test depositing to closed account raises error."""
        account = Account()
        account.close()
        with pytest.raises(ValueError, match="closed"):
            account.deposit(Money(1000, Currency.USDT))

    def test_deposit_creates_transaction(self) -> None:
        """Test that deposit creates transaction."""
        account = Account()
        account.deposit(Money(1000, Currency.USDT))
        assert account.get_transaction_count() == 1

        tx = account.get_transaction_history()[0]
        assert tx.transaction_type == TransactionType.DEPOSIT
        assert tx.amount.amount == 1000


class TestAccountWithdrawals:
    """Test account withdrawal operations."""

    def test_withdraw_funds(self) -> None:
        """Test withdrawing funds."""
        account = Account()
        account.deposit(Money(1000, Currency.USDT))
        account.withdraw(Money(300, Currency.USDT))
        assert account.get_available_balance(Currency.USDT).amount == 700

    def test_withdraw_insufficient_funds(self) -> None:
        """Test withdrawing more than available."""
        account = Account()
        account.deposit(Money(100, Currency.USDT))
        with pytest.raises(ValueError):
            account.withdraw(Money(200, Currency.USDT))

    def test_withdraw_from_closed_account(self) -> None:
        """Test withdrawing from closed account raises error."""
        account = Account()
        account.deposit(Money(1000, Currency.USDT))
        account.close()
        with pytest.raises(ValueError, match="closed"):
            account.withdraw(Money(100, Currency.USDT))

    def test_withdraw_creates_transaction(self) -> None:
        """Test that withdrawal creates transaction."""
        account = Account()
        account.deposit(Money(1000, Currency.USDT))
        account.withdraw(Money(300, Currency.USDT))
        assert account.get_transaction_count() == 2

        tx = account.get_transaction_history()[-1]
        assert tx.transaction_type == TransactionType.WITHDRAWAL
        assert tx.amount.amount == 300


class TestAccountTrading:
    """Test account trading operations."""

    def test_record_buy_trade(self) -> None:
        """Test recording buy trade."""
        account = Account()
        account.deposit(Money(1000, Currency.USDT))
        account.record_trade(
            TransactionType.BUY,
            Money(1000, Currency.USDT),
            "Buy USDT",
            reference_id="order_1",
        )
        assert account.get_transaction_count() == 2

    def test_record_sell_trade(self) -> None:
        """Test recording sell trade."""
        account = Account()
        account.deposit(Money(1, Currency.BTC))
        account.record_trade(
            TransactionType.SELL,
            Money(1, Currency.BTC),
            "Sell BTC",
            reference_id="order_1",
        )
        assert account.get_transaction_count() == 2

    def test_record_invalid_trade_type(self) -> None:
        """Test recording invalid trade type."""
        account = Account()
        with pytest.raises(ValueError, match="BUY or SELL"):
            account.record_trade(
                TransactionType.DEPOSIT,
                Money(100, Currency.USDT),
                "Invalid",
            )


class TestAccountFees:
    """Test account fee recording."""

    def test_record_fee(self) -> None:
        """Test recording trading fee."""
        account = Account()
        account.deposit(Money(1000, Currency.USDT))
        account.record_fee(Money(1, Currency.USDT), "Trading fee")

        assert account.get_available_balance(Currency.USDT).amount == 999
        assert account.get_transaction_count() == 2

    def test_fee_insufficient_balance(self) -> None:
        """Test recording fee with insufficient balance."""
        account = Account()
        account.deposit(Money(0.5, Currency.USDT))
        with pytest.raises(ValueError):
            account.record_fee(Money(1, Currency.USDT), "Fee")


class TestAccountStatus:
    """Test account status operations."""

    def test_close_account(self) -> None:
        """Test closing account."""
        account = Account()
        assert account.is_active
        account.close()
        assert not account.is_active
        assert account.closed_at is not None

    def test_close_already_closed_account(self) -> None:
        """Test closing already closed account."""
        account = Account()
        account.close()
        with pytest.raises(ValueError, match="already closed"):
            account.close()

    def test_reopen_account(self) -> None:
        """Test reopening closed account."""
        account = Account()
        account.close()
        assert not account.is_active
        account.reopen()
        assert account.is_active
        assert account.closed_at is None

    def test_reopen_active_account(self) -> None:
        """Test reopening active account."""
        account = Account()
        with pytest.raises(ValueError, match="already open"):
            account.reopen()


class TestAccountLeverage:
    """Test account leverage settings."""

    def test_set_leverage(self) -> None:
        """Test setting leverage."""
        account = Account()
        account.set_leverage(2.0)
        assert account.leverage == 2.0

    def test_set_leverage_invalid(self) -> None:
        """Test setting invalid leverage."""
        account = Account()
        with pytest.raises(ValueError):
            account.set_leverage(0.5)

        with pytest.raises(ValueError):
            account.set_leverage(5.0)


class TestAccountHistory:
    """Test account transaction history."""

    def test_get_transaction_history(self) -> None:
        """Test getting transaction history."""
        account = Account()
        account.deposit(Money(1000, Currency.USDT))
        account.withdraw(Money(100, Currency.USDT))

        history = account.get_transaction_history()
        assert len(history) == 2
        assert history[0].transaction_type == TransactionType.DEPOSIT
        assert history[1].transaction_type == TransactionType.WITHDRAWAL

    def test_transaction_history_sorted_by_timestamp(self) -> None:
        """Test that history is sorted by timestamp."""
        import time

        account = Account()
        account.deposit(Money(100, Currency.USDT))
        time.sleep(0.01)
        account.withdraw(Money(50, Currency.USDT))

        history = account.get_transaction_history()
        assert history[0].timestamp <= history[1].timestamp


class TestAccountSummary:
    """Test account summary."""

    def test_get_summary(self) -> None:
        """Test getting account summary."""
        account = Account(name="Test Account")
        account.deposit(Money(1000, Currency.USDT))

        summary = account.get_summary()
        assert summary["name"] == "Test Account"
        assert summary["is_active"]
        assert summary["leverage"] == 1.0
        assert summary["transaction_count"] == 1
