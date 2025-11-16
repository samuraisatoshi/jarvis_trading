"""
Check Paper Trading Account Status.

Displays current account balances, transactions, and status.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.database import DatabaseManager
from src.infrastructure.persistence.sqlite_account_repository import (
    SQLiteAccountRepository,
)
from loguru import logger


def check_account_status(db_path: str, account_id: str = None) -> None:
    """
    Check and display account status.

    Args:
        db_path: Path to SQLite database file
        account_id: Specific account ID to check (optional)
    """
    try:
        # Initialize database
        db = DatabaseManager(db_path)
        db.initialize()

        repo = SQLiteAccountRepository(db)

        if account_id:
            # Get specific account
            account = repo.find_by_id(account_id)
            if not account:
                print(f"Account not found: {account_id}")
                return

            accounts = [account]
        else:
            # Get all active accounts
            accounts = repo.find_all_active()

        if not accounts:
            print("No active accounts found.")
            return

        print("\n" + "=" * 80)
        print("PAPER TRADING ACCOUNT STATUS")
        print("=" * 80)

        for account in accounts:
            summary = account.get_summary()

            print(f"\nAccount: {summary['name']}")
            print(f"  ID:              {summary['account_id']}")
            print(f"  Status:          {'ACTIVE' if summary['is_active'] else 'CLOSED'}")
            print(f"  Created:         {summary['created_at']}")
            print(f"  Leverage:        {summary['leverage']}x")
            print(f"  Transactions:    {summary['transaction_count']}")

            print(f"\n  Balances:")
            balance_data = summary["balance"]
            if balance_data:
                for currency, amount in balance_data.items():
                    print(f"    {currency:8s} {amount}")
            else:
                print("    (No balances)")

            # Display recent transactions
            transactions = account.get_transaction_history()
            if transactions:
                print(f"\n  Recent Transactions ({len(transactions)}):")
                # Show last 5 transactions
                for tx in transactions[-5:]:
                    print(
                        f"    {tx.timestamp.isoformat():19s} | "
                        f"{tx.transaction_type.value:8s} | "
                        f"{str(tx.amount):20s} | {tx.description}"
                    )
            else:
                print("\n  Recent Transactions: None")

            print("\n" + "-" * 80)

        print("\n" + "=" * 80 + "\n")

    except Exception as e:
        logger.error(f"Failed to check account status: {e}", exc_info=True)
        print(f"ERROR: {e}")
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Check paper trading account status")
    parser.add_argument(
        "--db",
        type=str,
        default=str(project_root / "data" / "jarvis_trading.db"),
        help="Path to database file",
    )
    parser.add_argument(
        "--account-id",
        type=str,
        default=None,
        help="Specific account ID to check",
    )

    args = parser.parse_args()

    check_account_status(args.db, args.account_id)


if __name__ == "__main__":
    main()
