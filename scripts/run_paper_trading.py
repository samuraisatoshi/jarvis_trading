#!/usr/bin/env python3
"""
Paper Trading System for RL Models - Autonomous Trading

This script runs the paper trading system for trained RL models.
Executes trades automatically at candle close based on model predictions.

Features:
- Fetches real-time data from Binance REST API
- Calculates 13 core features
- Gets model predictions (no manual adjustments)
- Executes paper trades with SQLite persistence
- Schedules execution at daily candle close (00:00 UTC)

Usage:
    # One-time execution
    python scripts/run_paper_trading.py

    # Scheduled execution (daemon mode)
    python scripts/run_paper_trading.py --daemon

    # Dry run (no trades)
    python scripts/run_paper_trading.py --dry-run
"""

import sys
import asyncio
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import logging
from loguru import logger

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.database import DatabaseManager
from src.infrastructure.exchange.binance_rest_client import BinanceRESTClient
from src.infrastructure.persistence.sqlite_account_repository import (
    SQLiteAccountRepository,
)
from src.domain.features.services.feature_calculator import FeatureCalculator
from src.domain.reinforcement_learning.services.prediction_service import (
    RLPredictionService,
)
from src.domain.reinforcement_learning.services.model_loader import ModelLoader
from src.domain.market_data.services.candle_scheduler import CandleScheduler
from src.domain.account.value_objects.money import Money
from src.domain.account.value_objects.currency import Currency
from src.domain.account.entities.transaction import TransactionType


class PaperTradingSystem:
    """
    Autonomous paper trading system using trained RL models.

    Responsibilities:
    - Fetch latest candle data at close
    - Calculate features
    - Get model prediction
    - Execute trade if threshold met
    - Persist all data to SQLite
    """

    # Trading thresholds (from training)
    BUY_THRESHOLD = 0.3
    SELL_THRESHOLD = -0.3

    def __init__(
        self,
        account_id: str,
        symbol: str,
        timeframe: str,
        models_path: str,
        db_path: str,
        dry_run: bool = False,
    ):
        """
        Initialize paper trading system.

        Args:
            account_id: Paper trading account UUID
            symbol: Trading pair (e.g., 'BNB_USDT')
            timeframe: Candle timeframe (e.g., '1d')
            models_path: Path to trained models directory
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
        self.feature_calculator = FeatureCalculator()
        self.prediction_service = RLPredictionService(
            models_path=models_path, use_core_features=True
        )
        self.scheduler = CandleScheduler()

        logger.info(
            f"Paper Trading System initialized:\n"
            f"  Account: {account_id}\n"
            f"  Symbol: {symbol}\n"
            f"  Timeframe: {timeframe}\n"
            f"  Models: {models_path}\n"
            f"  Dry run: {dry_run}"
        )

    def fetch_latest_candles(self, limit: int = 300) -> Optional[pd.DataFrame]:
        """
        Fetch latest candles from Binance.

        Args:
            limit: Number of candles to fetch (need 200+ for features)

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

            # Get balances directly from account.balance.available
            usdt_balance = account.balance.available.get(Currency.USDT, Money(0, Currency.USDT)).amount
            asset_balance = account.balance.available.get(asset_currency, Money(0, asset_currency)).amount

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

    def execute_trade(self, action: int, confidence: float, price: float) -> bool:
        """
        Execute trade based on model prediction.

        Args:
            action: Model action (0=SELL, 1=HOLD, 2=BUY)
            confidence: Prediction confidence (0-1)
            price: Current price

        Returns:
            True if trade executed, False otherwise
        """
        try:
            position = self.get_current_position()
            action_name = self.prediction_service.get_action_name(action)

            logger.info(
                f"Trade decision: {action_name} (confidence={confidence:.2%})\n"
                f"  Price: ${price:,.2f}\n"
                f"  USDT balance: ${position['usdt_balance']:,.2f}\n"
                f"  Asset balance: {position['asset_balance']:.6f}\n"
                f"  Position value: ${position['position_value']:,.2f}"
            )

            if self.dry_run:
                logger.info("DRY RUN: No trade executed")
                return False

            account = self.account_repo.find_by_id(self.account_id)
            if not account:
                raise ValueError(f"Account not found: {self.account_id}")

            # Get asset currency
            asset_symbol = self.symbol.split("_")[0]
            asset_currency = Currency.from_string(asset_symbol)

            # BUY: confidence > threshold AND no position
            if action == 2 and confidence > self.BUY_THRESHOLD:
                if position["asset_balance"] > 0:
                    logger.info("Already in position. Skipping BUY.")
                    return False

                # Buy with available USDT
                usdt_to_spend = position["usdt_balance"]
                amount_to_buy = usdt_to_spend / price

                if amount_to_buy <= 0:
                    logger.warning("No USDT balance to buy")
                    return False

                # Execute BUY:
                # 1. Withdraw USDT (deduct from balance)
                account.withdraw(
                    Money(usdt_to_spend, Currency.USDT),
                    description=f"BUY {amount_to_buy:.6f} {asset_symbol} @ ${price:,.2f}"
                )

                # 2. Deposit asset (add to balance)
                account.deposit(
                    Money(amount_to_buy, asset_currency),
                    description=f"Received {amount_to_buy:.6f} {asset_symbol} from BUY"
                )

                # 3. Record trade transaction
                account.record_trade(
                    transaction_type=TransactionType.BUY,
                    amount=Money(amount_to_buy, asset_currency),
                    description=f"BUY {amount_to_buy:.6f} {asset_symbol} @ ${price:,.2f} (cost: ${usdt_to_spend:,.2f} USDT)"
                )

                # Save account
                self.account_repo.save(account)

                logger.info(
                    f"✅ BUY executed: {amount_to_buy:.6f} {asset_symbol} @ ${price:,.2f} "
                    f"(spent ${usdt_to_spend:,.2f} USDT)"
                )
                return True

            # SELL: confidence < threshold AND has position
            elif action == 0 and confidence < self.SELL_THRESHOLD:
                if position["asset_balance"] <= 0:
                    logger.info("No position to sell. Skipping SELL.")
                    return False

                # Sell entire position
                asset_to_sell = position["asset_balance"]
                usdt_received = asset_to_sell * price

                # Execute SELL:
                # 1. Withdraw asset (deduct from balance)
                account.withdraw(
                    Money(asset_to_sell, asset_currency),
                    description=f"SELL {asset_to_sell:.6f} {asset_symbol} @ ${price:,.2f}"
                )

                # 2. Deposit USDT (add to balance)
                account.deposit(
                    Money(usdt_received, Currency.USDT),
                    description=f"Received ${usdt_received:,.2f} USDT from SELL"
                )

                # 3. Record trade transaction
                account.record_trade(
                    transaction_type=TransactionType.SELL,
                    amount=Money(asset_to_sell, asset_currency),
                    description=f"SELL {asset_to_sell:.6f} {asset_symbol} @ ${price:,.2f} (received: ${usdt_received:,.2f} USDT)"
                )

                # Save account
                self.account_repo.save(account)

                logger.info(
                    f"✅ SELL executed: {asset_to_sell:.6f} {asset_symbol} @ ${price:,.2f} "
                    f"-> ${usdt_received:,.2f} USDT"
                )
                return True

            else:
                logger.info(f"HOLD: No action taken (confidence={confidence:.2%})")
                return False

        except Exception as e:
            logger.error(f"Error executing trade: {e}", exc_info=True)
            return False

    async def run_trading_cycle(self, **kwargs):
        """
        Run a single trading cycle (fetch, predict, trade).

        Called by scheduler at candle close.
        """
        try:
            logger.info(f"\n{'=' * 80}")
            logger.info(f"TRADING CYCLE - {datetime.utcnow().isoformat()} UTC")
            logger.info(f"{'=' * 80}\n")

            # 1. Fetch latest candles
            df = self.fetch_latest_candles(limit=300)
            if df is None or len(df) < 200:
                logger.error("Insufficient candle data. Skipping cycle.")
                return

            # 2. Get model prediction
            result = self.prediction_service.predict(
                symbol=self.symbol, timeframe=self.timeframe, candles=df
            )

            logger.info(
                f"Model prediction:\n"
                f"  Action: {result.action} ({self.prediction_service.get_action_name(result.action)})\n"
                f"  Confidence: {result.confidence:.2%}\n"
                f"  Price: ${result.price:,.2f}\n"
                f"  Timestamp: {result.timestamp}"
            )

            # 3. Execute trade if threshold met
            trade_executed = self.execute_trade(
                action=result.action, confidence=result.confidence, price=result.price
            )

            # 4. Log final position
            position = self.get_current_position()
            total_value = position["usdt_balance"] + position["position_value"]

            logger.info(
                f"\nFinal position:\n"
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
        logger.info(f"Trades will execute at candle close")

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
                await asyncio.sleep(60)  # Sleep 1 minute, scheduler handles timing
        except KeyboardInterrupt:
            logger.info("Stopping daemon...")
            self.scheduler.stop_all_jobs()

    def run_once(self):
        """Run a single trading cycle (for testing or manual execution)."""
        asyncio.run(self.run_trading_cycle())


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Paper trading system for RL models")
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
        "--models-path",
        type=str,
        default="/Users/jfoc/Documents/DevLabs/python/crypto/finrl/trained_models",
        help="Path to trained models directory",
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
        project_root / "logs" / f"paper_trading_{args.symbol}_{args.timeframe}.log",
        rotation="1 day",
        retention="30 days",
        level="DEBUG",
    )

    # Create system
    system = PaperTradingSystem(
        account_id=args.account_id,
        symbol=args.symbol,
        timeframe=args.timeframe,
        models_path=args.models_path,
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
