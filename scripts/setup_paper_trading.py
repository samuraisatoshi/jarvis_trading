"""
Setup and initialize paper trading account.

Creates a new virtual account with initial balance for paper trading.
This script demonstrates the Account Balance Management system.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.domain.account.entities.account import Account
from src.domain.account.value_objects.currency import Currency
from src.domain.account.value_objects.money import Money
from src.domain.account.services.balance_service import BalanceService
from src.infrastructure.persistence.json_account_repository import (
    JsonAccountRepository,
)


def setup_paper_trading_account(
    name: str = "Paper Trading Account",
    initial_usdt: float = 10000.0,
    initial_btc: float = 0.0,
    initial_eth: float = 0.0,
) -> Account:
    """
    Create and initialize a paper trading account.

    Args:
        name: Account name
        initial_usdt: Initial USDT balance
        initial_btc: Initial BTC balance
        initial_eth: Initial ETH balance

    Returns:
        Created Account object
    """
    # Create account
    account = Account(name=name, leverage=1.0, max_leverage=3.0)

    # Deposit initial funds
    if initial_usdt > 0:
        account.deposit(
            Money(initial_usdt, Currency.USDT), "Initial USDT deposit"
        )

    if initial_btc > 0:
        account.deposit(Money(initial_btc, Currency.BTC), "Initial BTC deposit")

    if initial_eth > 0:
        account.deposit(Money(initial_eth, Currency.ETH), "Initial ETH deposit")

    return account


def save_and_display_account(
    account: Account, repository: JsonAccountRepository
) -> None:
    """
    Save account to repository and display summary.

    Args:
        account: Account to save
        repository: Repository for persistence
    """
    # Save account
    repository.save(account)

    # Display summary
    print("\n" + "=" * 60)
    print("PAPER TRADING ACCOUNT CREATED")
    print("=" * 60)

    summary = account.get_summary()
    print(f"Account ID: {summary['account_id']}")
    print(f"Account Name: {summary['name']}")
    print(f"Status: {'ACTIVE' if summary['is_active'] else 'CLOSED'}")
    print(f"Leverage: {summary['leverage']}x")
    print(f"Transaction Count: {summary['transaction_count']}")

    print("\nBalance:")
    for currency, amount in summary["balance"].items():
        print(f"  {currency}: {amount}")

    # Display buying power
    print("\nBuying Power:")
    for currency_str in summary["balance"].keys():
        currency = Currency.from_string(currency_str)
        power = BalanceService.calculate_buying_power(account, currency)
        print(f"  {currency_str}: {power.amount:.8f}")

    print("\n" + "=" * 60 + "\n")


def main() -> None:
    """Main entry point."""
    import yaml

    # Load configuration
    config_file = project_root / "config" / "paper_trading.yaml"

    if not config_file.exists():
        print(f"ERROR: Configuration file not found: {config_file}")
        sys.exit(1)

    with open(config_file) as f:
        config = yaml.safe_load(f)

    paper_trading_config = config.get("paper_trading", {})
    initial_balance = paper_trading_config.get("initial_balance", {})

    # Create repository
    data_dir = paper_trading_config.get("storage", {}).get("data_dir", "data")
    repository = JsonAccountRepository(data_dir)

    # Setup account
    print("\nSetting up paper trading account...")
    account = setup_paper_trading_account(
        name="Paper Trading Account",
        initial_usdt=initial_balance.get("USDT", 10000.0),
        initial_btc=initial_balance.get("BTC", 0.0),
        initial_eth=initial_balance.get("ETH", 0.0),
    )

    # Save and display
    save_and_display_account(account, repository)

    print("Paper trading account successfully created!")
    print(f"Saved to: {data_dir}/accounts.json")


if __name__ == "__main__":
    main()
