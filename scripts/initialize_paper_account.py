"""
Initialize Paper Trading Account with SQLite persistence.

Creates a new paper trading account with $5,000 USD (USDT) initial balance
using SQLite database for persistent storage.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.domain.account.entities.account import Account
from src.domain.account.value_objects.currency import Currency
from src.domain.account.value_objects.money import Money
from src.infrastructure.database import DatabaseManager
from src.infrastructure.persistence.sqlite_account_repository import (
    SQLiteAccountRepository,
)
from loguru import logger


def initialize_paper_account(
    db_path: str,
    account_name: str = "Paper Trading Account - Client",
    initial_balance_usdt: float = 5000.0,
    leverage: float = 1.0,
    max_leverage: float = 3.0,
) -> Account:
    """
    Initialize a paper trading account with SQLite persistence.

    Args:
        db_path: Path to SQLite database file
        account_name: Name of the account
        initial_balance_usdt: Initial USDT balance
        leverage: Initial leverage multiplier (1.0 = no leverage)
        max_leverage: Maximum allowed leverage

    Returns:
        Created Account object

    Raises:
        ValueError: If parameters are invalid
    """
    # Validate parameters
    if initial_balance_usdt <= 0:
        raise ValueError("Initial balance must be positive")
    if leverage < 1.0 or leverage > max_leverage:
        raise ValueError(f"Leverage must be between 1.0 and {max_leverage}")

    # Initialize database
    logger.info(f"Initializing database: {db_path}")
    db = DatabaseManager(db_path)
    db.initialize()

    # Create account
    logger.info(f"Creating account: {account_name}")
    account = Account(
        name=account_name,
        leverage=leverage,
        max_leverage=max_leverage,
    )

    # Deposit initial balance
    initial_deposit = Money(initial_balance_usdt, Currency.USDT)
    account.deposit(initial_deposit, f"Initial deposit: ${initial_balance_usdt} USD")

    # Save to database
    logger.info(f"Saving account to database: {account.account_id}")
    repo = SQLiteAccountRepository(db)
    repo.save(account)

    return account, db


def display_account_status(account: Account, db: DatabaseManager) -> None:
    """
    Display account status and details.

    Args:
        account: Account entity
        db: Database manager instance
    """
    print("\n" + "=" * 70)
    print("PAPER TRADING ACCOUNT INITIALIZED")
    print("=" * 70)

    summary = account.get_summary()

    print(f"\nAccount ID:     {summary['account_id']}")
    print(f"Account Name:   {summary['name']}")
    print(f"Status:         {'ACTIVE' if summary['is_active'] else 'CLOSED'}")
    print(f"Leverage:       {summary['leverage']}x")
    print(f"Max Leverage:   {account.max_leverage}x")
    print(f"Created At:     {summary['created_at']}")
    print(f"Transactions:   {summary['transaction_count']}")

    print("\n" + "-" * 70)
    print("BALANCES")
    print("-" * 70)

    balance_summary = summary["balance"]
    for currency, amount in balance_summary.items():
        print(f"  {currency}: {amount}")

    print("\n" + "-" * 70)
    print("DATABASE")
    print("-" * 70)
    print(f"Database Path: {db.db_path}")
    print(f"Initialized:   {db._initialized}")

    print("\n" + "=" * 70)
    print("READY FOR PAPER TRADING")
    print("=" * 70 + "\n")


def main() -> None:
    """Main entry point for account initialization."""
    try:
        # Database configuration
        db_path = str(project_root / "data" / "jarvis_trading.db")

        logger.info("Starting paper trading account initialization...")

        # Initialize account with $5,000 USDT
        account, db = initialize_paper_account(
            db_path=db_path,
            account_name="Paper Trading Account - Client",
            initial_balance_usdt=5000.0,
            leverage=1.0,
            max_leverage=3.0,
        )

        # Display status
        display_account_status(account, db)

        # Print key information
        print("QUICK REFERENCE:")
        print(f"  Account ID: {account.account_id}")
        print(f"  Database:   {db_path}")
        print(f"  Balance:    $5,000.00 USDT")
        print("\nTo check account status later:")
        print(f"  python scripts/check_account_status.py")
        print()

        logger.info(f"Paper trading account created successfully: {account.account_id}")

    except Exception as e:
        logger.error(f"Failed to initialize paper trading account: {e}", exc_info=True)
        print(f"\nERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
