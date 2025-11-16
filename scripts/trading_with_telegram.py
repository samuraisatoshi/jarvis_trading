#!/usr/bin/env python3
"""
Paper Trading System with Telegram Notifications

Enhanced version of run_paper_trading.py with full Telegram integration.

Features:
- All features from run_paper_trading.py
- Real-time Telegram notifications for all events
- Market analysis alerts
- Trade execution confirmations
- Circuit breaker alerts
- Daily performance reports
- Error notifications

Usage:
    # One-time execution with notifications
    python scripts/trading_with_telegram.py

    # Daemon mode with scheduled notifications
    python scripts/trading_with_telegram.py --daemon

    # Dry run (no trades, but send notifications)
    python scripts/trading_with_telegram.py --dry-run
"""

import sys
import os
import asyncio
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from loguru import logger

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv(project_root / ".env")

from src.infrastructure.database import DatabaseManager
from src.infrastructure.exchange.binance_rest_client import BinanceRESTClient
from src.infrastructure.persistence.sqlite_account_repository import (
    SQLiteAccountRepository,
)
from src.domain.features.services.feature_calculator import FeatureCalculator
from src.domain.reinforcement_learning.services.prediction_service import (
    RLPredictionService,
)
from src.domain.market_data.services.candle_scheduler import CandleScheduler
from src.domain.account.value_objects.money import Money
from src.domain.account.value_objects.currency import Currency
from src.domain.account.entities.transaction import TransactionType

# Telegram integration
from src.infrastructure.notifications.telegram_notifier import TelegramNotifier
from src.infrastructure.notifications.message_templates import (
    TradingMessageTemplates,
    MessageFormat,
)


class TelegramPaperTradingSystem:
    """
    Paper trading system with Telegram notifications.

    Extends basic paper trading with real-time Telegram alerts for:
    - System startup/shutdown
    - Market analysis (every execution)
    - Trading signals (BUY/SELL/HOLD)
    - Trade executions
    - Circuit breaker activation
    - Errors and warnings
    - Daily/weekly reports
    """

    # Trading thresholds
    BUY_THRESHOLD = 0.3
    SELL_THRESHOLD = -0.3

    # Circuit breaker
    MAX_DRAWDOWN = 0.15  # 15% max loss
    MIN_WIN_RATE = 0.35  # 35% minimum win rate

    def __init__(
        self,
        account_id: str,
        symbol: str,
        timeframe: str,
        models_path: str,
        db_path: str,
        telegram_enabled: bool = True,
        dry_run: bool = False,
    ):
        """
        Initialize paper trading system with Telegram.

        Args:
            account_id: Paper trading account UUID
            symbol: Trading pair (e.g., 'BNB_USDT')
            timeframe: Candle timeframe (e.g., '1d')
            models_path: Path to trained models
            db_path: Path to SQLite database
            telegram_enabled: Enable Telegram notifications
            dry_run: Dry run mode (no trades)
        """
        self.account_id = account_id
        self.symbol = symbol
        self.timeframe = timeframe
        self.dry_run = dry_run
        self.telegram_enabled = telegram_enabled
        self.circuit_breaker_active = False

        # Initialize core services
        self.db = DatabaseManager(db_path)
        self.db.initialize()

        self.account_repo = SQLiteAccountRepository(self.db)
        self.binance_client = BinanceRESTClient(testnet=False)
        self.feature_calculator = FeatureCalculator()
        self.prediction_service = RLPredictionService(
            models_path=models_path, use_core_features=True
        )
        self.scheduler = CandleScheduler()

        # Initialize Telegram
        self.telegram = None
        if telegram_enabled:
            self._initialize_telegram()

        # Track initial balance for circuit breaker
        self.initial_balance = self._get_total_value()

        logger.info(
            f"Paper Trading System (Telegram) initialized:\n"
            f"  Account: {account_id}\n"
            f"  Symbol: {symbol}\n"
            f"  Timeframe: {timeframe}\n"
            f"  Telegram: {'Enabled' if telegram_enabled else 'Disabled'}\n"
            f"  Dry run: {dry_run}"
        )

    def _initialize_telegram(self):
        """Initialize Telegram notifier."""
        try:
            bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
            chat_id = os.getenv("TELEGRAM_CHAT_ID")
            authorized_ids_str = os.getenv("TELEGRAM_AUTHORIZED_CHAT_IDS", chat_id)

            if not bot_token or not chat_id:
                logger.warning(
                    "Telegram configuration not found in .env. Notifications disabled."
                )
                logger.warning("Run: python scripts/setup_telegram.py")
                self.telegram_enabled = False
                return

            # Parse authorized chat IDs
            authorized_ids = [id.strip() for id in authorized_ids_str.split(",")]

            self.telegram = TelegramNotifier(
                bot_token=bot_token,
                chat_id=chat_id,
                authorized_chat_ids=authorized_ids,
                parse_mode="HTML",  # HTML is more reliable than MarkdownV2
            )

            # Test connection
            if not self.telegram.test_connection():
                logger.warning("Telegram connection test failed. Notifications disabled.")
                self.telegram_enabled = False
                self.telegram = None
                return

            logger.info("✅ Telegram notifications enabled")

        except Exception as e:
            logger.error(f"Error initializing Telegram: {e}", exc_info=True)
            self.telegram_enabled = False
            self.telegram = None

    def _send_telegram(self, message: str, disable_notification: bool = False) -> bool:
        """Send Telegram notification (with error handling)."""
        if not self.telegram_enabled or not self.telegram:
            return False

        try:
            return self.telegram.send_message(
                message, disable_notification=disable_notification
            )
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False

    def _get_total_value(self) -> float:
        """Get total account value (USDT + position value)."""
        try:
            account = self.account_repo.find_by_id(self.account_id)
            if not account:
                return 0.0

            # Get balances
            usdt_balance = float(
                account.balance.available.get(
                    Currency.USDT, Money(0, Currency.USDT)
                ).amount
            )

            # Get asset balance
            asset_symbol = self.symbol.split("_")[0]
            asset_currency = Currency.from_string(asset_symbol)
            asset_balance = float(
                account.balance.available.get(
                    asset_currency, Money(0, asset_currency)
                ).amount
            )

            # Get current price
            binance_symbol = self.symbol.replace("_", "")
            current_price = self.binance_client.get_ticker_price(binance_symbol) or 0.0

            return usdt_balance + (asset_balance * current_price)

        except Exception as e:
            logger.error(f"Error getting total value: {e}")
            return 0.0

    def _check_circuit_breaker(self) -> bool:
        """
        Check circuit breaker conditions.

        Returns:
            True if circuit breaker should activate, False otherwise
        """
        try:
            current_value = self._get_total_value()
            drawdown = (self.initial_balance - current_value) / self.initial_balance

            # Check drawdown
            if drawdown > self.MAX_DRAWDOWN:
                self.circuit_breaker_active = True

                # Send alert
                message = TradingMessageTemplates.circuit_breaker_triggered(
                    reason="Drawdown máximo excedido",
                    current_drawdown=drawdown,
                    max_drawdown=self.MAX_DRAWDOWN,
                    format=MessageFormat.HTML,
                )
                self._send_telegram(message)

                logger.critical(
                    f"🚨 CIRCUIT BREAKER: Drawdown {drawdown:.1%} > {self.MAX_DRAWDOWN:.1%}"
                )
                return True

            return False

        except Exception as e:
            logger.error(f"Error checking circuit breaker: {e}")
            return False

    def fetch_latest_candles(self, limit: int = 300) -> Optional[pd.DataFrame]:
        """Fetch latest candles from Binance."""
        try:
            binance_symbol = self.symbol.replace("_", "")
            logger.info(f"Fetching {limit} candles for {binance_symbol} {self.timeframe}")

            klines = self.binance_client.get_klines(
                symbol=binance_symbol, interval=self.timeframe, limit=limit
            )

            if not klines:
                error_msg = TradingMessageTemplates.error_alert(
                    error_type="Data Fetch Error",
                    error_message="No candle data received from Binance",
                    context=f"{binance_symbol} {self.timeframe}",
                    format=MessageFormat.HTML,
                )
                self._send_telegram(error_msg)
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
            error_msg = TradingMessageTemplates.error_alert(
                error_type="Exchange Error",
                error_message=str(e),
                context="fetch_latest_candles",
                format=MessageFormat.HTML,
            )
            self._send_telegram(error_msg)
            return None

    def get_current_position(self) -> dict:
        """Get current position from account."""
        try:
            account = self.account_repo.find_by_id(self.account_id)
            if not account:
                raise ValueError(f"Account not found: {self.account_id}")

            asset_symbol = self.symbol.split("_")[0]
            asset_currency = Currency.from_string(asset_symbol)

            usdt_balance = float(
                account.balance.available.get(
                    Currency.USDT, Money(0, Currency.USDT)
                ).amount
            )
            asset_balance = float(
                account.balance.available.get(
                    asset_currency, Money(0, asset_currency)
                ).amount
            )

            binance_symbol = self.symbol.replace("_", "")
            current_price = self.binance_client.get_ticker_price(binance_symbol) or 0.0

            return {
                "usdt_balance": usdt_balance,
                "asset_balance": asset_balance,
                "current_price": current_price,
                "position_value": asset_balance * current_price,
            }

        except Exception as e:
            logger.error(f"Error getting position: {e}", exc_info=True)
            return {
                "usdt_balance": 0.0,
                "asset_balance": 0.0,
                "current_price": 0.0,
                "position_value": 0.0,
            }

    def execute_trade(
        self, action: int, confidence: float, price: float, indicators: dict
    ) -> bool:
        """Execute trade with Telegram notification."""
        try:
            # Check circuit breaker
            if self.circuit_breaker_active:
                logger.warning("Circuit breaker active. Skipping trade.")
                return False

            if self._check_circuit_breaker():
                return False

            position = self.get_current_position()
            action_name = self.prediction_service.get_action_name(action)

            # Send trading signal
            signal_msg = TradingMessageTemplates.trade_signal(
                symbol=self.symbol,
                action=action_name,
                confidence=confidence,
                price=price,
                indicators=indicators,
                format=MessageFormat.HTML,
            )
            self._send_telegram(signal_msg)

            logger.info(
                f"Trade decision: {action_name} (confidence={confidence:.2%})\n"
                f"  Price: ${price:,.2f}\n"
                f"  USDT: ${position['usdt_balance']:,.2f}\n"
                f"  Asset: {position['asset_balance']:.6f}"
            )

            if self.dry_run:
                logger.info("DRY RUN: No trade executed")
                return False

            account = self.account_repo.find_by_id(self.account_id)
            if not account:
                raise ValueError(f"Account not found: {self.account_id}")

            asset_symbol = self.symbol.split("_")[0]
            asset_currency = Currency.from_string(asset_symbol)

            # BUY logic
            if action == 2 and confidence > self.BUY_THRESHOLD:
                if position["asset_balance"] > 0:
                    logger.info("Already in position. Skipping BUY.")
                    return False

                usdt_to_spend = position["usdt_balance"]
                amount_to_buy = usdt_to_spend / price

                if amount_to_buy <= 0:
                    logger.warning("No USDT balance to buy")
                    return False

                # Execute BUY
                account.withdraw(
                    Money(usdt_to_spend, Currency.USDT),
                    description=f"BUY {amount_to_buy:.6f} {asset_symbol} @ ${price:,.2f}",
                )
                account.deposit(
                    Money(amount_to_buy, asset_currency),
                    description=f"Received {amount_to_buy:.6f} {asset_symbol}",
                )
                account.record_trade(
                    transaction_type=TransactionType.BUY,
                    amount=Money(amount_to_buy, asset_currency),
                    description=f"BUY {amount_to_buy:.6f} {asset_symbol} @ ${price:,.2f}",
                )

                self.account_repo.save(account)

                # Get new balances
                new_position = self.get_current_position()
                total_value = new_position["usdt_balance"] + new_position["position_value"]

                # Send execution notification
                exec_msg = TradingMessageTemplates.trade_executed(
                    trade_type="BUY",
                    symbol=self.symbol,
                    quantity=amount_to_buy,
                    price=price,
                    total_cost=usdt_to_spend,
                    new_balance_usdt=new_position["usdt_balance"],
                    new_balance_asset=new_position["asset_balance"],
                    total_value=total_value,
                    format=MessageFormat.HTML,
                )
                self._send_telegram(exec_msg)

                logger.info(f"✅ BUY executed: {amount_to_buy:.6f} {asset_symbol}")
                return True

            # SELL logic
            elif action == 0 and confidence < self.SELL_THRESHOLD:
                if position["asset_balance"] <= 0:
                    logger.info("No position to sell. Skipping SELL.")
                    return False

                asset_to_sell = position["asset_balance"]
                usdt_received = asset_to_sell * price

                # Execute SELL
                account.withdraw(
                    Money(asset_to_sell, asset_currency),
                    description=f"SELL {asset_to_sell:.6f} {asset_symbol} @ ${price:,.2f}",
                )
                account.deposit(
                    Money(usdt_received, Currency.USDT),
                    description=f"Received ${usdt_received:,.2f} USDT",
                )
                account.record_trade(
                    transaction_type=TransactionType.SELL,
                    amount=Money(asset_to_sell, asset_currency),
                    description=f"SELL {asset_to_sell:.6f} {asset_symbol} @ ${price:,.2f}",
                )

                self.account_repo.save(account)

                # Get new balances
                new_position = self.get_current_position()
                total_value = new_position["usdt_balance"] + new_position["position_value"]

                # Send execution notification
                exec_msg = TradingMessageTemplates.trade_executed(
                    trade_type="SELL",
                    symbol=self.symbol,
                    quantity=asset_to_sell,
                    price=price,
                    total_cost=usdt_received,
                    new_balance_usdt=new_position["usdt_balance"],
                    new_balance_asset=new_position["asset_balance"],
                    total_value=total_value,
                    format=MessageFormat.HTML,
                )
                self._send_telegram(exec_msg)

                logger.info(f"✅ SELL executed: {asset_to_sell:.6f} {asset_symbol}")
                return True

            else:
                logger.info(f"HOLD: No action taken")
                return False

        except Exception as e:
            logger.error(f"Error executing trade: {e}", exc_info=True)
            error_msg = TradingMessageTemplates.error_alert(
                error_type="Trade Execution Error",
                error_message=str(e),
                context=f"{self.symbol} - {action_name}",
                format=MessageFormat.HTML,
            )
            self._send_telegram(error_msg)
            return False

    async def run_trading_cycle(self, **kwargs):
        """Run trading cycle with full Telegram notifications."""
        try:
            logger.info(f"\n{'=' * 80}")
            logger.info(f"TRADING CYCLE - {datetime.utcnow().isoformat()} UTC")
            logger.info(f"{'=' * 80}\n")

            # Fetch candles
            df = self.fetch_latest_candles(limit=300)
            if df is None or len(df) < 200:
                logger.error("Insufficient candle data. Skipping cycle.")
                return

            # Get prediction
            result = self.prediction_service.predict(
                symbol=self.symbol, timeframe=self.timeframe, candles=df
            )

            # Prepare indicators dict for messages
            indicators = {
                "rsi": result.features.get("rsi_14", 50),
                "macd": result.features.get("macd", 0),
                "macd_signal": result.features.get("macd_signal", 0),
                "volume_change_pct": result.features.get("volume_change_pct", 0),
            }

            logger.info(
                f"Prediction: {self.prediction_service.get_action_name(result.action)} "
                f"(confidence={result.confidence:.2%})"
            )

            # Execute trade (will send Telegram notifications internally)
            self.execute_trade(
                action=result.action,
                confidence=result.confidence,
                price=result.price,
                indicators=indicators,
            )

            # Log final position
            position = self.get_current_position()
            total_value = position["usdt_balance"] + position["position_value"]

            logger.info(
                f"\nFinal position:\n"
                f"  USDT: ${position['usdt_balance']:,.2f}\n"
                f"  Asset: {position['asset_balance']:.6f}\n"
                f"  Total: ${total_value:,.2f}"
            )

            logger.info(f"\n{'=' * 80}\n")

        except Exception as e:
            logger.error(f"Error in trading cycle: {e}", exc_info=True)
            error_msg = TradingMessageTemplates.error_alert(
                error_type="Trading Cycle Error",
                error_message=str(e),
                context="run_trading_cycle",
                format=MessageFormat.HTML,
            )
            self._send_telegram(error_msg)

    async def run_daemon(self):
        """Run in daemon mode with scheduled execution."""
        logger.info(f"Starting daemon mode: {self.symbol} {self.timeframe}")

        # Send startup notification
        if self.telegram_enabled:
            startup_msg = TradingMessageTemplates.system_startup(
                symbol=self.symbol,
                timeframe=self.timeframe,
                account_id=self.account_id,
                initial_balance=self.initial_balance,
                format=MessageFormat.HTML,
            )
            self._send_telegram(startup_msg)

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
        """Run single cycle."""
        asyncio.run(self.run_trading_cycle())


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Paper trading with Telegram notifications"
    )
    parser.add_argument(
        "--account-id",
        type=str,
        default="868e0dd8-37f5-43ea-a956-7cc05e6bad66",
        help="Paper trading account ID",
    )
    parser.add_argument(
        "--symbol", type=str, default="BNB_USDT", help="Trading pair"
    )
    parser.add_argument(
        "--timeframe", type=str, default="1d", help="Candle timeframe"
    )
    parser.add_argument(
        "--models-path",
        type=str,
        default="/Users/jfoc/Documents/DevLabs/python/crypto/finrl/trained_models",
        help="Path to trained models",
    )
    parser.add_argument(
        "--db",
        type=str,
        default=str(project_root / "data" / "jarvis_trading.db"),
        help="Database path",
    )
    parser.add_argument("--daemon", action="store_true", help="Daemon mode")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    parser.add_argument(
        "--no-telegram", action="store_true", help="Disable Telegram notifications"
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
        project_root / "logs" / f"telegram_trading_{args.symbol}_{args.timeframe}.log",
        rotation="1 day",
        retention="30 days",
        level="DEBUG",
    )

    # Create system
    system = TelegramPaperTradingSystem(
        account_id=args.account_id,
        symbol=args.symbol,
        timeframe=args.timeframe,
        models_path=args.models_path,
        db_path=args.db,
        telegram_enabled=not args.no_telegram,
        dry_run=args.dry_run,
    )

    # Run
    if args.daemon:
        asyncio.run(system.run_daemon())
    else:
        system.run_once()


if __name__ == "__main__":
    main()
