"""Balance service for account domain."""

from typing import Dict, Optional

from ..entities.account import Account
from ..value_objects.currency import Currency
from ..value_objects.money import Money


class BalanceService:
    """
    Service for managing account balances.

    Provides operations for balance queries and modifications.
    Implements domain logic for balance calculations.
    """

    @staticmethod
    def get_total_balance_in_currency(
        account: Account, currency: Currency
    ) -> Money:
        """Get total balance (available + reserved) for currency.

        Args:
            account: Account to query
            currency: Currency to get balance for

        Returns:
            Total Money amount

        Raises:
            KeyError: If currency not in balance
        """
        return account.balance.get_total(currency)

    @staticmethod
    def get_available_balance_in_currency(
        account: Account, currency: Currency
    ) -> Money:
        """Get available balance for currency.

        Args:
            account: Account to query
            currency: Currency to get balance for

        Returns:
            Available Money amount

        Raises:
            KeyError: If currency not in balance
        """
        return account.balance.get_available(currency)

    @staticmethod
    def get_reserved_balance_in_currency(
        account: Account, currency: Currency
    ) -> Money:
        """Get reserved balance for currency.

        Args:
            account: Account to query
            currency: Currency to get balance for

        Returns:
            Reserved Money amount (0 if none)
        """
        return account.balance.get_reserved(currency)

    @staticmethod
    def get_all_available_balances(account: Account) -> Dict[str, float]:
        """Get all available balances.

        Args:
            account: Account to query

        Returns:
            Dictionary mapping currency symbols to amounts
        """
        return account.balance.get_summary()

    @staticmethod
    def can_trade(account: Account, required: Money) -> bool:
        """Check if account can execute trade with required amount.

        Args:
            account: Account to check
            required: Required Money amount

        Returns:
            True if available balance >= required, False otherwise

        Raises:
            KeyError: If currency not in balance
        """
        available = account.balance.get_available(required.currency)
        return available >= required

    @staticmethod
    def calculate_buying_power(
        account: Account, currency: Currency
    ) -> Money:
        """Calculate buying power (available * leverage).

        Args:
            account: Account to calculate for
            currency: Currency to calculate for

        Returns:
            Buying power Money amount

        Raises:
            KeyError: If currency not in balance
        """
        available = account.balance.get_available(currency)
        buying_power_amount = available.amount * account.leverage
        return Money(buying_power_amount, currency)

    @staticmethod
    def calculate_utilization_percentage(
        account: Account, currency: Currency
    ) -> float:
        """Calculate balance utilization percentage (reserved/total).

        Args:
            account: Account to calculate for
            currency: Currency to calculate for

        Returns:
            Utilization percentage (0-100)

        Raises:
            KeyError: If currency not in balance
        """
        total = account.balance.get_total(currency)
        reserved = account.balance.get_reserved(currency)

        if total.amount == 0:
            return 0.0

        return (reserved.amount / total.amount) * 100

    @staticmethod
    def get_portfolio_value(
        account: Account, prices: Dict[Currency, float]
    ) -> float:
        """Calculate total portfolio value in reference currency.

        Args:
            account: Account to calculate for
            prices: Dictionary mapping currencies to prices in reference currency

        Returns:
            Total portfolio value

        Raises:
            KeyError: If currency price not found
        """
        total_value = 0.0

        for currency, money in account.balance.available.items():
            if currency not in prices:
                raise KeyError(f"Price not found for {currency}")
            total_value += money.amount * prices[currency]

        return total_value

    @staticmethod
    def get_currency_breakdown(
        account: Account, prices: Dict[Currency, float]
    ) -> Dict[str, Dict[str, float]]:
        """Get breakdown of portfolio by currency.

        Args:
            account: Account to analyze
            prices: Dictionary mapping currencies to prices

        Returns:
            Dictionary with per-currency information

        Raises:
            KeyError: If currency price not found
        """
        breakdown = {}
        total_value = BalanceService.get_portfolio_value(account, prices)

        for currency, money in account.balance.available.items():
            if currency not in prices:
                raise KeyError(f"Price not found for {currency}")

            value = money.amount * prices[currency]
            percentage = (value / total_value * 100) if total_value > 0 else 0

            breakdown[currency.value] = {
                "amount": money.amount,
                "value": value,
                "percentage": percentage,
            }

        return breakdown

    @staticmethod
    def reserve_for_order(account: Account, money: Money) -> None:
        """Reserve balance for open order.

        Args:
            account: Account to update
            money: Money to reserve

        Raises:
            ValueError: If insufficient available balance
        """
        account.balance.reserve(money)

    @staticmethod
    def release_from_order(account: Account, money: Money) -> None:
        """Release reserved balance from closed order.

        Args:
            account: Account to update
            money: Money to release

        Raises:
            ValueError: If insufficient reserved balance
        """
        account.balance.unreserve(money)

    @staticmethod
    def deduct_trading_fee(
        account: Account, amount_money: Money, fee_percentage: float
    ) -> Money:
        """Deduct trading fee from balance.

        Args:
            account: Account to update
            amount_money: Money amount traded
            fee_percentage: Fee percentage (e.g., 0.001 for 0.1%)

        Returns:
            Fee Money amount deducted

        Raises:
            ValueError: If insufficient balance
        """
        fee_amount = amount_money.amount * fee_percentage
        fee = Money(fee_amount, amount_money.currency)

        account.record_fee(
            fee, f"Trading fee ({fee_percentage*100}%) on {amount_money}"
        )

        return fee
