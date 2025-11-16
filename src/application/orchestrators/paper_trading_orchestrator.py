"""
Generic paper trading orchestrator.

Coordinates paper trading workflow for ANY strategy (not just Fibonacci).
This is a more generic version that can be extended for different strategies
and trading approaches.

Usage:
    >>> from src.strategies import FibonacciGoldenZoneStrategy
    >>> orchestrator = PaperTradingOrchestrator(
    ...     account_id="uuid",
    ...     strategy=FibonacciGoldenZoneStrategy(),
    ...     symbol="BTC_USDT",
    ...     timeframe="4h",
    ...     db_path="data/db.sqlite"
    ... )
    >>> result = orchestrator.execute()
"""

from typing import Dict, Any, Optional
from loguru import logger
import pandas as pd
from datetime import datetime
import time

from src.application.orchestrators.base import BaseOrchestrator, OrchestrationError
from src.strategies.base import TradingStrategy
from src.infrastructure.database import DatabaseManager
from src.infrastructure.exchange.binance_rest_client import BinanceRESTClient
from src.infrastructure.persistence.sqlite_account_repository import (
    SQLiteAccountRepository,
)
from src.domain.account.value_objects.money import Money
from src.domain.account.value_objects.currency import Currency
from src.domain.account.entities.transaction import TransactionType


class PaperTradingOrchestrator(BaseOrchestrator):
    """
    Generic paper trading orchestrator for any strategy.

    This orchestrator is strategy-agnostic and works with ANY trading
    strategy that implements the TradingStrategy interface (Strategy Pattern).

    Benefits:
    - Open/Closed Principle: Add new strategies without modifying orchestrator
    - Liskov Substitution: Any TradingStrategy is substitutable
    - Single Responsibility: Only coordinates workflow, no strategy logic

    Workflow:
    1. Fetch market data from exchange
    2. Generate signal using provided strategy
    3. Execute trade via paper trading account
    4. Persist results to database

    Example:
        >>> from src.strategies import FibonacciGoldenZoneStrategy
        >>> strategy = FibonacciGoldenZoneStrategy()
        >>> orchestrator = PaperTradingOrchestrator(
        ...     account_id="uuid",
        ...     strategy=strategy,
        ...     symbol="BTC_USDT",
        ...     timeframe="4h",
        ...     db_path="data/db.sqlite"
        ... )
        >>> result = orchestrator.execute()
    """

    def __init__(
        self,
        account_id: str,
        strategy: TradingStrategy,
        symbol: str,
        timeframe: str,
        db_path: str,
        dry_run: bool = False,
        candles_limit: int = 300
    ):
        """
        Initialize paper trading orchestrator.

        Args:
            account_id: Paper trading account UUID
            strategy: Any TradingStrategy implementation
            symbol: Trading pair (e.g., 'BTC_USDT')
            timeframe: Candle timeframe (e.g., '1d', '4h')
            db_path: Path to SQLite database
            dry_run: If True, don't execute actual trades
            candles_limit: Number of candles to fetch
        """
        self.account_id = account_id
        self.strategy = strategy
        self.symbol = symbol
        self.timeframe = timeframe
        self.dry_run = dry_run
        self.candles_limit = candles_limit

        # Initialize services
        self.db = DatabaseManager(db_path)
        self.db.initialize()

        self.account_repo = SQLiteAccountRepository(self.db)
        self.binance_client = BinanceRESTClient(testnet=False)

        logger.info(
            f"Paper Trading Orchestrator initialized:\n"
            f"  Account: {account_id}\n"
            f"  Strategy: {strategy.__class__.__name__}\n"
            f"  Symbol: {symbol}\n"
            f"  Timeframe: {timeframe}\n"
            f"  Dry run: {dry_run}"
        )

    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute paper trading workflow.

        Returns:
            Dict with workflow results:
                {
                    'status': 'success' | 'failure',
                    'signal': <strategy signal>,
                    'trade_executed': bool,
                    'position': <current position>,
                    'error': <error if failed>
                }
        """
        start_time = time.time()
        workflow_name = f"{self.strategy.__class__.__name__} Paper Trading"

        self._log_execution_start(workflow_name, {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'strategy': self.strategy.__class__.__name__
        })

        try:
            # Fetch data
            df = self._fetch_market_data()
            if df is None or len(df) < 50:  # Minimum required candles
                raise OrchestrationError(
                    "Insufficient market data",
                    {'candles_received': len(df) if df is not None else 0}
                )

            # Generate signal
            signal = self.strategy.generate_signal(df)

            # Get position
            position = self._get_position()

            # Execute trade
            trade_executed = self._execute_trade(signal, position)

            # Success
            result = {
                'status': 'success',
                'signal': signal,
                'trade_executed': trade_executed,
                'position': position,
                'timestamp': datetime.utcnow().isoformat()
            }

            duration = time.time() - start_time
            self._log_execution_end(workflow_name, result, duration)

            return result

        except Exception as e:
            error_result = self._handle_error(
                error=e,
                context={
                    'symbol': self.symbol,
                    'strategy': self.strategy.__class__.__name__
                }
            )

            duration = time.time() - start_time
            self._log_execution_end(workflow_name, error_result, duration)

            return error_result

    def _fetch_market_data(self) -> Optional[pd.DataFrame]:
        """Fetch market data from Binance."""
        try:
            binance_symbol = self.symbol.replace("_", "")

            logger.info(
                f"Fetching {self.candles_limit} candles for "
                f"{binance_symbol} {self.timeframe}"
            )

            klines = self.binance_client.get_klines(
                symbol=binance_symbol,
                interval=self.timeframe,
                limit=self.candles_limit
            )

            if not klines:
                return None

            df = pd.DataFrame(klines)
            df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms")
            df = df[["timestamp", "open", "high", "low", "close", "volume"]]
            df.set_index("timestamp", inplace=True)

            logger.info(f"Fetched {len(df)} candles. Latest: {df.index[-1]}")
            return df

        except Exception as e:
            logger.error(f"Error fetching market data: {e}", exc_info=True)
            raise OrchestrationError("Failed to fetch market data", {'error': str(e)})

    def _get_position(self) -> Dict[str, float]:
        """Get current position from account."""
        try:
            account = self.account_repo.find_by_id(self.account_id)
            if not account:
                raise OrchestrationError(
                    "Account not found",
                    {'account_id': self.account_id}
                )

            asset_symbol = self.symbol.split("_")[0]
            asset_currency = Currency.from_string(asset_symbol)

            usdt_balance = account.balance.available.get(
                Currency.USDT, Money(0, Currency.USDT)
            ).amount
            asset_balance = account.balance.available.get(
                asset_currency, Money(0, asset_currency)
            ).amount

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
            raise OrchestrationError("Failed to get position", {'error': str(e)})

    def _execute_trade(self, signal: Dict, position: Dict) -> bool:
        """
        Execute trade based on signal.

        Args:
            signal: Signal from strategy
            position: Current position

        Returns:
            True if trade executed
        """
        action = signal.get('action', 'HOLD')

        if action == 'HOLD':
            logger.info("Signal: HOLD - No trade executed")
            return False

        if self.dry_run:
            logger.info(f"DRY RUN: Would execute {action}")
            return False

        try:
            account = self.account_repo.find_by_id(self.account_id)
            if not account:
                return False

            asset_symbol = self.symbol.split("_")[0]
            asset_currency = Currency.from_string(asset_symbol)
            price = signal.get('entry', signal.get('current_price', 0))

            if action == 'BUY' and position["asset_balance"] == 0:
                return self._buy(account, position, asset_symbol, asset_currency, price)

            elif action == 'SELL' and position["asset_balance"] > 0:
                return self._sell(account, position, asset_symbol, asset_currency, price)

            return False

        except Exception as e:
            logger.error(f"Error executing trade: {e}", exc_info=True)
            return False

    def _buy(self, account, position, asset_symbol, asset_currency, price) -> bool:
        """Execute BUY trade."""
        usdt = position["usdt_balance"]
        amount = usdt / price

        if amount <= 0:
            return False

        account.withdraw(Money(usdt, Currency.USDT), description=f"BUY {amount:.6f} {asset_symbol}")
        account.deposit(Money(amount, asset_currency), description=f"Received {amount:.6f} {asset_symbol}")
        account.record_trade(
            transaction_type=TransactionType.BUY,
            amount=Money(amount, asset_currency),
            description=f"BUY {amount:.6f} {asset_symbol} @ ${price:,.2f}"
        )

        self.account_repo.save(account)
        logger.info(f"✅ BUY: {amount:.6f} {asset_symbol} @ ${price:,.2f}")
        return True

    def _sell(self, account, position, asset_symbol, asset_currency, price) -> bool:
        """Execute SELL trade."""
        amount = position["asset_balance"]
        usdt = amount * price

        account.withdraw(Money(amount, asset_currency), description=f"SELL {amount:.6f} {asset_symbol}")
        account.deposit(Money(usdt, Currency.USDT), description=f"Received ${usdt:,.2f} USDT")
        account.record_trade(
            transaction_type=TransactionType.SELL,
            amount=Money(amount, asset_currency),
            description=f"SELL {amount:.6f} {asset_symbol} @ ${price:,.2f}"
        )

        self.account_repo.save(account)
        logger.info(f"✅ SELL: {amount:.6f} {asset_symbol} @ ${price:,.2f}")
        return True
