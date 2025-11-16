#!/usr/bin/env python3
"""
Fibonacci Golden Zone Paper Trading System

Runs autonomous paper trading using the Fibonacci Golden Zone strategy
instead of ML models. Executes at candle close based on technical analysis.

Features:
- Fetches real-time data from Binance REST API
- Applies Fibonacci Golden Zone analysis
- Executes paper trades with SQLite persistence
- Schedules execution at daily candle close (00:00 UTC)

Usage:
    # One-time execution
    python scripts/run_fibonacci_strategy.py

    # Scheduled execution (daemon mode)
    python scripts/run_fibonacci_strategy.py --daemon

    # Dry run (no trades)
    python scripts/run_fibonacci_strategy.py --dry-run

Example:
    $ python scripts/run_fibonacci_strategy.py --dry-run
    TRADING CYCLE - 2025-11-15T00:00:05 UTC
    ================================================================================
    Fetching 300 candles for BNBUSDT 1d
    Fetched 300 candles. Latest: 2025-11-14 23:59:59
    UPTREND detected: EMA20=625.45 > EMA50=612.30 > EMA200=595.10
    Found 15 swing highs and 14 swing lows (lookback=20)
    Price $618.50 is IN Golden Zone
    RSI Bullish Divergence detected
    Volume Spike detected
    Hammer candle detected

    Signal: BUY
    Reason: Golden Zone em UPTREND com 3 confirmações bullish
    Entry: $618.50
    Stop Loss: $605.20
    Take Profit 1: $640.80
    Take Profit 2: $668.90

    Trade executed: 16.15 BNB @ $618.50 (spent $10,000.00 USDT)
"""

import sys
import asyncio
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Optional
from loguru import logger

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.database import DatabaseManager
from src.infrastructure.exchange.binance_rest_client import BinanceRESTClient
from src.infrastructure.persistence.sqlite_account_repository import (
    SQLiteAccountRepository,
)
from src.domain.market_data.services.candle_scheduler import CandleScheduler
from src.domain.account.value_objects.money import Money
from src.domain.account.value_objects.currency import Currency
from src.domain.account.entities.transaction import TransactionType

# Import Fibonacci strategy
sys.path.insert(0, str(project_root / 'scripts'))
from fibonacci_golden_zone_strategy import FibonacciGoldenZoneStrategy


class FibonacciPaperTradingSystem:
    """
    Paper trading system using Fibonacci Golden Zone strategy.

    Differences from ML-based system:
    - Uses Fibonacci technical analysis instead of RL models
    - No feature calculation needed
    - Clearer, deterministic trading rules
    - Built-in risk management (stop loss, take profit)

    Responsibilities:
    - Fetch latest candle data at close
    - Run Fibonacci strategy analysis
    - Execute trade if Golden Zone + confirmations met
    - Persist all data to SQLite
    """

    def __init__(
        self,
        account_id: str,
        symbol: str,
        timeframe: str,
        db_path: str,
        dry_run: bool = False,
    ):
        """
        Initialize Fibonacci paper trading system.

        Args:
            account_id: Paper trading account UUID
            symbol: Trading pair (e.g., 'BNB_USDT')
            timeframe: Candle timeframe (e.g., '1d')
            db_path: Path to SQLite database
            dry_run: If True, don't execute trades
        """
        self.account_id = account_id
        self.symbol = symbol
        self.timeframe = timeframe
        self.dry_run = dry_run

        # Initialize services
        self.db = DatabaseManager(db_path)
        self.db.initialize()

        self.account_repo = SQLiteAccountRepository(self.db)
        self.binance_client = BinanceRESTClient(testnet=False)
        self.strategy = FibonacciGoldenZoneStrategy()
        self.scheduler = CandleScheduler()

        logger.info(
            f"Fibonacci Paper Trading System initialized:\n"
            f"  Account: {account_id}\n"
            f"  Symbol: {symbol}\n"
            f"  Timeframe: {timeframe}\n"
            f"  Strategy: Fibonacci Golden Zone\n"
            f"  Dry run: {dry_run}"
        )

    def fetch_latest_candles(self, limit: int = 300) -> Optional[pd.DataFrame]:
        """
        Fetch latest candles from Binance.

        Args:
            limit: Number of candles to fetch (need 200+ for EMAs)

        Returns:
            DataFrame with OHLCV data or None if error
        """
        try:
            # Convert symbol format (BNB_USDT -> BNBUSDT)
            binance_symbol = self.symbol.replace("_", "")

            logger.info(f"Fetching {limit} candles for {binance_symbol} {self.timeframe}")

            klines = self.binance_client.get_klines(
                symbol=binance_symbol, interval=self.timeframe, limit=limit
            )

            if not klines:
                logger.error("No candle data received from Binance")
                return None

            # Convert to DataFrame
            df = pd.DataFrame(klines)
            df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms")
            df = df[["timestamp", "open", "high", "low", "close", "volume"]]
            df.set_index("timestamp", inplace=True)

            logger.info(f"Fetched {len(df)} candles. Latest: {df.index[-1]}")

            return df

        except Exception as e:
            logger.error(f"Error fetching candles: {e}", exc_info=True)
            return None

    def get_current_position(self) -> dict:
        """
        Get current position from account.

        Returns:
            Dict with balance info (usdt_balance, asset_balance, current_price)
        """
        try:
            account = self.account_repo.find_by_id(self.account_id)
            if not account:
                raise ValueError(f"Account not found: {self.account_id}")

            # Get asset symbol from trading pair (BNB from BNB_USDT)
            asset_symbol = self.symbol.split("_")[0]
            asset_currency = Currency.from_string(asset_symbol)

            # Get balances
            usdt_balance = account.balance.available.get(
                Currency.USDT, Money(0, Currency.USDT)
            ).amount
            asset_balance = account.balance.available.get(
                asset_currency, Money(0, asset_currency)
            ).amount

            # Get current price
            binance_symbol = self.symbol.replace("_", "")
            current_price = self.binance_client.get_ticker_price(binance_symbol)

            return {
                "usdt_balance": float(usdt_balance),
                "asset_balance": float(asset_balance),
                "current_price": current_price or 0.0,
                "position_value": float(asset_balance) * (current_price or 0.0),
            }

        except Exception as e:
            logger.error(f"Error getting position: {e}", exc_info=True)
            return {
                "usdt_balance": 0.0,
                "asset_balance": 0.0,
                "current_price": 0.0,
                "position_value": 0.0,
            }

    def execute_trade(self, signal: dict) -> bool:
        """
        Execute trade based on Fibonacci strategy signal.

        Args:
            signal: Signal dict from FibonacciGoldenZoneStrategy.generate_signal()

        Returns:
            True if trade executed, False otherwise
        """
        try:
            action = signal['action']
            position = self.get_current_position()

            logger.info(
                f"\n{'='*60}\n"
                f"Trade Signal: {action}\n"
                f"Reason: {signal['reason']}\n"
                f"Trend: {signal['trend']}\n"
                f"Current Price: ${signal['current_price']:,.2f}\n"
                f"{'='*60}\n"
                f"Current Position:\n"
                f"  USDT balance: ${position['usdt_balance']:,.2f}\n"
                f"  Asset balance: {position['asset_balance']:.6f}\n"
                f"  Position value: ${position['position_value']:,.2f}\n"
                f"{'='*60}"
            )

            # HOLD - no action
            if action == 'HOLD':
                logger.info("HOLD: No trade executed")
                return False

            if self.dry_run:
                logger.info("DRY RUN: No trade executed")
                if action in ['BUY', 'SELL']:
                    logger.info(
                        f"Would execute {action}:\n"
                        f"  Entry: ${signal['entry']:,.2f}\n"
                        f"  Stop Loss: ${signal['stop_loss']:,.2f}\n"
                        f"  Take Profit 1: ${signal['take_profit_1']:,.2f}\n"
                        f"  Take Profit 2: ${signal['take_profit_2']:,.2f}\n"
                        f"  Confirmations: {', '.join(signal['confirmations'])}"
                    )
                return False

            account = self.account_repo.find_by_id(self.account_id)
            if not account:
                raise ValueError(f"Account not found: {self.account_id}")

            asset_symbol = self.symbol.split("_")[0]
            asset_currency = Currency.from_string(asset_symbol)
            price = signal['entry']

            # BUY signal
            if action == 'BUY':
                if position["asset_balance"] > 0:
                    logger.info("Already in position. Skipping BUY.")
                    return False

                # Buy with available USDT
                usdt_to_spend = position["usdt_balance"]
                amount_to_buy = usdt_to_spend / price

                if amount_to_buy <= 0:
                    logger.warning("No USDT balance to buy")
                    return False

                # Execute BUY
                account.withdraw(
                    Money(usdt_to_spend, Currency.USDT),
                    description=f"BUY {amount_to_buy:.6f} {asset_symbol} @ ${price:,.2f}"
                )
                account.deposit(
                    Money(amount_to_buy, asset_currency),
                    description=f"Received {amount_to_buy:.6f} {asset_symbol} from BUY"
                )
                account.record_trade(
                    transaction_type=TransactionType.BUY,
                    amount=Money(amount_to_buy, asset_currency),
                    description=(
                        f"BUY {amount_to_buy:.6f} {asset_symbol} @ ${price:,.2f}\n"
                        f"Stop Loss: ${signal['stop_loss']:,.2f}\n"
                        f"Take Profit 1: ${signal['take_profit_1']:,.2f}\n"
                        f"Take Profit 2: ${signal['take_profit_2']:,.2f}\n"
                        f"Confirmations: {', '.join(signal['confirmations'])}"
                    )
                )

                self.account_repo.save(account)

                logger.info(
                    f"✅ BUY executed:\n"
                    f"  Amount: {amount_to_buy:.6f} {asset_symbol}\n"
                    f"  Price: ${price:,.2f}\n"
                    f"  Cost: ${usdt_to_spend:,.2f} USDT\n"
                    f"  Stop Loss: ${signal['stop_loss']:,.2f}\n"
                    f"  Take Profit 1: ${signal['take_profit_1']:,.2f}\n"
                    f"  Take Profit 2: ${signal['take_profit_2']:,.2f}\n"
                    f"  Confirmations: {', '.join(signal['confirmations'])}"
                )
                return True

            # SELL signal
            elif action == 'SELL':
                if position["asset_balance"] <= 0:
                    logger.info("No position to sell. Skipping SELL.")
                    return False

                # Sell entire position
                asset_to_sell = position["asset_balance"]
                usdt_received = asset_to_sell * price

                # Execute SELL
                account.withdraw(
                    Money(asset_to_sell, asset_currency),
                    description=f"SELL {asset_to_sell:.6f} {asset_symbol} @ ${price:,.2f}"
                )
                account.deposit(
                    Money(usdt_received, Currency.USDT),
                    description=f"Received ${usdt_received:,.2f} USDT from SELL"
                )
                account.record_trade(
                    transaction_type=TransactionType.SELL,
                    amount=Money(asset_to_sell, asset_currency),
                    description=(
                        f"SELL {asset_to_sell:.6f} {asset_symbol} @ ${price:,.2f}\n"
                        f"Stop Loss: ${signal['stop_loss']:,.2f}\n"
                        f"Take Profit 1: ${signal['take_profit_1']:,.2f}\n"
                        f"Take Profit 2: ${signal['take_profit_2']:,.2f}\n"
                        f"Confirmations: {', '.join(signal['confirmations'])}"
                    )
                )

                self.account_repo.save(account)

                logger.info(
                    f"✅ SELL executed:\n"
                    f"  Amount: {asset_to_sell:.6f} {asset_symbol}\n"
                    f"  Price: ${price:,.2f}\n"
                    f"  Received: ${usdt_received:,.2f} USDT\n"
                    f"  Stop Loss: ${signal['stop_loss']:,.2f}\n"
                    f"  Take Profit 1: ${signal['take_profit_1']:,.2f}\n"
                    f"  Take Profit 2: ${signal['take_profit_2']:,.2f}\n"
                    f"  Confirmations: {', '.join(signal['confirmations'])}"
                )
                return True

            return False

        except Exception as e:
            logger.error(f"Error executing trade: {e}", exc_info=True)
            return False

    async def run_trading_cycle(self, **kwargs):
        """
        Run a single trading cycle (fetch, analyze, trade).

        Called by scheduler at candle close.
        """
        try:
            logger.info(f"\n{'=' * 80}")
            logger.info(f"FIBONACCI TRADING CYCLE - {datetime.utcnow().isoformat()} UTC")
            logger.info(f"{'=' * 80}\n")

            # 1. Fetch latest candles
            df = self.fetch_latest_candles(limit=300)
            if df is None or len(df) < 200:
                logger.error("Insufficient candle data. Skipping cycle.")
                return

            # 2. Get Fibonacci strategy signal
            signal = self.strategy.generate_signal(df)

            logger.info(
                f"\nFibonacci Strategy Signal:\n"
                f"  Action: {signal['action']}\n"
                f"  Reason: {signal['reason']}\n"
                f"  Trend: {signal['trend']}\n"
                f"  Current Price: ${signal['current_price']:,.2f}"
            )

            # Show additional details if in Golden Zone
            if 'fib_levels' in signal:
                logger.info(
                    f"\nFibonacci Levels:\n"
                    f"  High: ${signal['fib_levels']['high']:,.2f}\n"
                    f"  Low: ${signal['fib_levels']['low']:,.2f}\n"
                    f"  Golden Zone: ${signal['fib_levels']['0.618']:,.2f} - ${signal['fib_levels']['0.500']:,.2f}"
                )

            if 'confirmations' in signal and signal['confirmations']:
                logger.info(f"  Confirmations: {', '.join(signal['confirmations'])}")

            # 3. Execute trade if BUY or SELL signal
            trade_executed = self.execute_trade(signal)

            # 4. Log final position
            position = self.get_current_position()
            total_value = position["usdt_balance"] + position["position_value"]

            logger.info(
                f"\nFinal Position:\n"
                f"  USDT: ${position['usdt_balance']:,.2f}\n"
                f"  Asset: {position['asset_balance']:.6f}\n"
                f"  Position value: ${position['position_value']:,.2f}\n"
                f"  Total value: ${total_value:,.2f}"
            )

            logger.info(f"\n{'=' * 80}\n")

        except Exception as e:
            logger.error(f"Error in trading cycle: {e}", exc_info=True)

    async def run_daemon(self):
        """
        Run paper trading in daemon mode (scheduled execution).

        Schedules execution at daily candle close (00:00 UTC).
        """
        logger.info(f"Starting daemon mode for {self.symbol} {self.timeframe}")
        logger.info(f"Trades will execute at candle close using Fibonacci Golden Zone strategy")

        # Schedule job
        self.scheduler.start_job(
            timeframe=self.timeframe,
            callback=self.run_trading_cycle,
            callback_args=(),
            callback_kwargs={},
        )

        # Keep running
        try:
            while True:
                await asyncio.sleep(60)
        except KeyboardInterrupt:
            logger.info("Stopping daemon...")
            self.scheduler.stop_all_jobs()

    def run_once(self):
        """Run a single trading cycle (for testing or manual execution)."""
        asyncio.run(self.run_trading_cycle())


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Fibonacci Golden Zone paper trading system"
    )
    parser.add_argument(
        "--account-id",
        type=str,
        default="868e0dd8-37f5-43ea-a956-7cc05e6bad66",
        help="Paper trading account ID",
    )
    parser.add_argument(
        "--symbol", type=str, default="BNB_USDT", help="Trading pair (e.g., BNB_USDT)"
    )
    parser.add_argument(
        "--timeframe", type=str, default="1d", help="Candle timeframe (e.g., 1d)"
    )
    parser.add_argument(
        "--db",
        type=str,
        default=str(project_root / "data" / "jarvis_trading.db"),
        help="Path to SQLite database",
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run in daemon mode (scheduled execution)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Dry run (no trades executed)"
    )

    args = parser.parse_args()

    # Configure logging
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO",
    )
    logger.add(
        project_root / "logs" / f"fibonacci_strategy_{args.symbol}_{args.timeframe}.log",
        rotation="1 day",
        retention="30 days",
        level="DEBUG",
    )

    # Create system
    system = FibonacciPaperTradingSystem(
        account_id=args.account_id,
        symbol=args.symbol,
        timeframe=args.timeframe,
        db_path=args.db,
        dry_run=args.dry_run,
    )

    # Run
    if args.daemon:
        asyncio.run(system.run_daemon())
    else:
        system.run_once()


if __name__ == "__main__":
    main()
