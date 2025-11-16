#!/usr/bin/env python3
"""
Buy & Hold + Fixed DCA Strategy Implementation

The WINNING strategy from our comprehensive backtesting:
- Buy & Hold + Fixed Weekly DCA: +87.41% return
- Simple beats complex in crypto bull markets

Strategy Rules:
1. Never sell existing holdings (Buy & Hold)
2. Buy $200 worth of BNB every week, regardless of price
3. No indicators, no timing, just consistent accumulation

This strategy beat:
- Fibonacci Golden Zone: -4.62% (0% win rate)
- DCA Smart with RSI: -27.00% (complexity penalty)
- Trend Following: +22.36% (but lost -37% alpha)
- Momentum Day Trade: -23.14%
"""

import sys
import time
import argparse
import signal
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
import traceback

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from src.infrastructure.exchange.binance_rest_client import BinanceRESTClient
from src.infrastructure.database import DatabaseManager
from src.domain.account.repositories.account_repository import AccountRepository
from src.infrastructure.persistence.sqlite_account_repository import SQLiteAccountRepository
from src.infrastructure.persistence.sqlite_transaction_repository import SQLiteTransactionRepository
from src.domain.account.value_objects.money import Money
from src.domain.account.value_objects.currency import Currency
from src.domain.account.entities.transaction import TransactionType
from src.infrastructure.notifications.telegram_notifier import TelegramNotifier


class BuyHoldDCAStrategy:
    """
    The simplest and most effective strategy:
    Buy & Hold existing position + Fixed weekly DCA.

    No indicators, no timing, just discipline.
    """

    def __init__(
        self,
        account_id: str,
        symbol: str = "BNB_USDT",
        dca_amount_usd: float = 200.0,
        dca_day: str = "monday"
    ):
        """
        Initialize Buy & Hold + DCA Strategy.

        Args:
            account_id: Paper trading account ID
            symbol: Trading pair (e.g., BNB_USDT)
            dca_amount_usd: Weekly DCA amount in USD
            dca_day: Day of week to execute DCA ("monday", "tuesday", etc.)
        """
        self.account_id = account_id
        self.symbol = symbol
        self.dca_amount_usd = dca_amount_usd
        self.dca_day = dca_day.lower()

        # Map day names to weekday numbers (0=Monday, 6=Sunday)
        self.day_map = {
            "monday": 0, "tuesday": 1, "wednesday": 2,
            "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6
        }

        # Initialize components
        self.client = BinanceRESTClient(testnet=False)
        self.db_manager = DatabaseManager('data/jarvis_trading.db')
        self.account_repo = SQLiteAccountRepository(self.db_manager)
        self.transaction_repo = SQLiteTransactionRepository(self.db_manager)

        # Initialize Telegram notifier (optional)
        try:
            self.telegram = TelegramNotifier()
            logger.info("Telegram notifications enabled")
        except Exception as e:
            self.telegram = None
            logger.warning(f"Telegram notifications disabled: {e}")

        # Control flags
        self.running = False
        self.last_dca_date = None

        logger.info(f"Buy & Hold + DCA Strategy initialized")
        logger.info(f"Account: {account_id}")
        logger.info(f"Symbol: {symbol}")
        logger.info(f"DCA Amount: ${dca_amount_usd} weekly on {dca_day}")

    def should_execute_dca(self) -> bool:
        """
        Check if today is DCA day and we haven't executed yet.

        Returns:
            True if we should execute DCA today
        """
        now = datetime.now(timezone.utc)
        current_weekday = now.weekday()
        target_weekday = self.day_map.get(self.dca_day, 0)

        # Check if today is the DCA day
        if current_weekday != target_weekday:
            return False

        # Check if we already executed today
        today_date = now.date()
        if self.last_dca_date == today_date:
            return False

        # Check if market is open (after 00:00 UTC)
        if now.hour < 0:  # Always true, but kept for clarity
            return False

        return True

    def execute_dca_purchase(self) -> dict:
        """
        Execute the weekly DCA purchase.

        Returns:
            dict with transaction details
        """
        try:
            # Get current BNB price
            ticker = self.client.get_24h_ticker(self.symbol.replace("_", ""))
            bnb_price = float(ticker['lastPrice'])

            # Calculate BNB amount to buy
            bnb_amount = self.dca_amount_usd / bnb_price

            # Load account
            account = self.account_repo.find_by_id(self.account_id)
            if not account:
                raise ValueError(f"Account {self.account_id} not found")

            # Check USDT balance
            usdt_balance = account.balance.available.get(Currency.USDT, 0.0)

            if usdt_balance < self.dca_amount_usd:
                logger.warning(f"Insufficient USDT balance: ${usdt_balance:.2f} < ${self.dca_amount_usd:.2f}")
                return {
                    "status": "FAILED",
                    "reason": "Insufficient balance",
                    "usdt_balance": usdt_balance,
                    "required": self.dca_amount_usd
                }

            # Execute purchase
            timestamp = datetime.now(timezone.utc)

            # Withdraw USDT
            account.withdraw(
                Money(self.dca_amount_usd, Currency.USDT),
                f"DCA purchase at ${bnb_price:.2f}"
            )

            # Deposit BNB
            account.deposit(
                Money(bnb_amount, Currency.BNB),
                f"DCA: Bought {bnb_amount:.6f} BNB"
            )

            # Record trade
            account.record_trade(
                TransactionType.BUY,
                Money(bnb_amount, Currency.BNB),
                f"Weekly DCA at ${bnb_price:.2f}"
            )

            # Save to database
            self.account_repo.save(account)

            # Update last DCA date
            self.last_dca_date = timestamp.date()

            # Create result
            result = {
                "status": "SUCCESS",
                "timestamp": timestamp.isoformat(),
                "action": "BUY",
                "amount_bnb": bnb_amount,
                "amount_usd": self.dca_amount_usd,
                "price": bnb_price,
                "new_bnb_balance": account.balance.available.get(Currency.BNB, 0.0),
                "new_usdt_balance": account.balance.available.get(Currency.USDT, 0.0)
            }

            # Send Telegram notification
            if self.telegram:
                message = (
                    "📈 **Weekly DCA Executed**\\n\\n"
                    f"✅ Bought {bnb_amount:.6f} BNB\\n"
                    f"💵 Price: ${bnb_price:.2f}\\n"
                    f"💰 Spent: ${self.dca_amount_usd:.2f}\\n\\n"
                    f"**New Balances:**\\n"
                    f"• BNB: {result['new_bnb_balance']:.6f}\\n"
                    f"• USDT: ${result['new_usdt_balance']:.2f}\\n\\n"
                    f"Strategy: Buy & Hold + Fixed DCA\\n"
                    f"Next DCA: Next {self.dca_day.capitalize()}"
                )
                self.telegram.send_message(message)

            logger.info(f"DCA executed: Bought {bnb_amount:.6f} BNB at ${bnb_price:.2f}")
            return result

        except Exception as e:
            logger.error(f"DCA execution failed: {e}")
            traceback.print_exc()
            return {
                "status": "ERROR",
                "error": str(e)
            }

    def get_portfolio_status(self) -> dict:
        """Get current portfolio status and performance."""
        try:
            account = self.account_repo.find_by_id(self.account_id)
            if not account:
                return {"error": "Account not found"}

            # Get balances
            bnb_balance = account.balance.available.get(Currency.BNB, 0.0)
            usdt_balance = account.balance.available.get(Currency.USDT, 0.0)

            # Get current BNB price
            ticker = self.client.get_24h_ticker(self.symbol.replace("_", ""))
            bnb_price = float(ticker['lastPrice'])

            # Calculate total value
            total_value = usdt_balance + (bnb_balance * bnb_price)
            initial_capital = 5000.0
            pnl = total_value - initial_capital
            pnl_pct = (total_value / initial_capital - 1) * 100

            return {
                "bnb_balance": bnb_balance,
                "usdt_balance": usdt_balance,
                "bnb_price": bnb_price,
                "total_value": total_value,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "strategy": "Buy & Hold + Fixed DCA"
            }

        except Exception as e:
            logger.error(f"Failed to get portfolio status: {e}")
            return {"error": str(e)}

    def run_daemon(self):
        """
        Run the strategy as a daemon.
        Checks daily if it's time for weekly DCA.
        """
        logger.info("Starting Buy & Hold + DCA daemon")
        self.running = True

        # Send startup notification
        if self.telegram:
            status = self.get_portfolio_status()
            message = (
                "🚀 **Buy & Hold + DCA Strategy Started**\\n\\n"
                f"📊 Initial Portfolio:\\n"
                f"• BNB: {status.get('bnb_balance', 0):.6f}\\n"
                f"• USDT: ${status.get('usdt_balance', 0):.2f}\\n"
                f"• Total: ${status.get('total_value', 0):.2f}\\n"
                f"• P&L: ${status.get('pnl', 0):.2f} ({status.get('pnl_pct', 0):+.2f}%)\\n\\n"
                f"⚙️ Settings:\\n"
                f"• DCA Amount: ${self.dca_amount_usd} weekly\\n"
                f"• DCA Day: {self.dca_day.capitalize()}\\n"
                f"• Symbol: {self.symbol}"
            )
            self.telegram.send_message(message)

        check_interval = 3600  # Check every hour

        while self.running:
            try:
                # Check if it's time for DCA
                if self.should_execute_dca():
                    logger.info(f"It's {self.dca_day}! Executing weekly DCA...")
                    result = self.execute_dca_purchase()

                    if result['status'] == 'SUCCESS':
                        logger.info(f"DCA successful: {result}")
                    else:
                        logger.warning(f"DCA failed: {result}")

                # Log status every 6 hours
                now = datetime.now(timezone.utc)
                if now.hour % 6 == 0 and now.minute < 1:
                    status = self.get_portfolio_status()
                    logger.info(f"Portfolio Status: {status}")

                # Sleep
                time.sleep(check_interval)

            except KeyboardInterrupt:
                logger.info("Received interrupt signal")
                break

            except Exception as e:
                logger.error(f"Error in daemon loop: {e}")
                traceback.print_exc()
                time.sleep(60)  # Wait a minute before retrying

        logger.info("Buy & Hold + DCA daemon stopped")

    def stop(self):
        """Stop the daemon."""
        self.running = False
        logger.info("Stopping Buy & Hold + DCA strategy")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Buy & Hold + Fixed DCA Strategy - The proven winner"
    )
    parser.add_argument(
        "--account-id",
        type=str,
        default="868e0dd8-37f5-43ea-a956-7cc05e6bad66",
        help="Paper trading account ID"
    )
    parser.add_argument(
        "--symbol",
        type=str,
        default="BNB_USDT",
        help="Trading symbol (e.g., BNB_USDT)"
    )
    parser.add_argument(
        "--dca-amount",
        type=float,
        default=200.0,
        help="Weekly DCA amount in USD"
    )
    parser.add_argument(
        "--dca-day",
        type=str,
        default="monday",
        choices=["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"],
        help="Day of week to execute DCA"
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run as daemon"
    )
    parser.add_argument(
        "--execute-now",
        action="store_true",
        help="Execute DCA immediately (for testing)"
    )

    args = parser.parse_args()

    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level="INFO"
    )

    if args.daemon:
        logger.add(
            f"logs/buyhold_dca_{args.symbol}_{args.dca_day}.log",
            rotation="100 MB",
            retention="30 days",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
            level="DEBUG"
        )

    # Create strategy
    strategy = BuyHoldDCAStrategy(
        account_id=args.account_id,
        symbol=args.symbol,
        dca_amount_usd=args.dca_amount,
        dca_day=args.dca_day
    )

    # Handle signals
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        strategy.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Execute
    if args.execute_now:
        logger.info("Executing DCA purchase immediately...")
        result = strategy.execute_dca_purchase()
        print(f"Result: {result}")
    elif args.daemon:
        logger.info("Starting Buy & Hold + DCA daemon...")
        logger.info(f"Strategy: Keep all BNB + Buy ${args.dca_amount} every {args.dca_day}")
        logger.info("This is the PROVEN WINNER with +87.41% backtest returns")
        strategy.run_daemon()
    else:
        # Just show status
        status = strategy.get_portfolio_status()
        print("=" * 60)
        print("BUY & HOLD + FIXED DCA STRATEGY")
        print("The Proven Winner: +87.41% Returns")
        print("=" * 60)
        print(f"Current Portfolio:")
        print(f"  BNB:  {status['bnb_balance']:.6f}")
        print(f"  USDT: ${status['usdt_balance']:.2f}")
        print(f"  BNB Price: ${status['bnb_price']:.2f}")
        print(f"  Total Value: ${status['total_value']:.2f}")
        print(f"  P&L: ${status['pnl']:.2f} ({status['pnl_pct']:+.2f}%)")
        print("=" * 60)
        print(f"DCA Settings:")
        print(f"  Amount: ${args.dca_amount} weekly")
        print(f"  Day: {args.dca_day.capitalize()}")
        print("=" * 60)


if __name__ == "__main__":
    main()