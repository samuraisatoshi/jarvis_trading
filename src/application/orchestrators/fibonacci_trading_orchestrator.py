"""
Fibonacci trading workflow orchestrator.

Coordinates the complete Fibonacci Golden Zone trading workflow:
1. Fetch market data from Binance
2. Generate trading signal using Fibonacci strategy
3. Execute trades via paper trading account
4. Persist results to database

This orchestrator contains NO business logic - it only coordinates
services and handles the workflow.

Business logic is in:
- src/strategies/fibonacci_golden_zone.py (strategy logic)
- src/domain/account/ (account management)
- src/domain/market_data/ (data fetching)
"""

from typing import Dict, Any, Optional
from loguru import logger
import pandas as pd
from datetime import datetime
import time

from src.application.orchestrators.base import BaseOrchestrator, OrchestrationError
from src.strategies import FibonacciGoldenZoneStrategy
from src.infrastructure.database import DatabaseManager
from src.infrastructure.exchange.binance_rest_client import BinanceRESTClient
from src.infrastructure.persistence.sqlite_account_repository import (
    SQLiteAccountRepository,
)
from src.domain.account.value_objects.money import Money
from src.domain.account.value_objects.currency import Currency
from src.domain.account.entities.transaction import TransactionType


class FibonacciTradingOrchestrator(BaseOrchestrator):
    """
    Orchestrates Fibonacci Golden Zone trading workflow.

    Responsibilities:
    - Coordinate data fetching from Binance
    - Coordinate strategy signal generation
    - Coordinate trade execution via account repository
    - Handle errors and retries
    - Log workflow execution

    Does NOT contain:
    - Fibonacci calculation logic (in strategy)
    - Account business rules (in domain)
    - Database queries (in repository)

    Usage:
        >>> orchestrator = FibonacciTradingOrchestrator(
        ...     account_id="account-uuid",
        ...     symbol="BNB_USDT",
        ...     timeframe="1d",
        ...     db_path="data/db.sqlite",
        ...     dry_run=False
        ... )
        >>> result = orchestrator.execute()
        >>> print(result['status'])  # 'success' or 'failure'
    """

    def __init__(
        self,
        account_id: str,
        symbol: str,
        timeframe: str,
        db_path: str,
        dry_run: bool = False,
        candles_limit: int = 300
    ):
        """
        Initialize Fibonacci trading orchestrator.

        Args:
            account_id: Paper trading account UUID
            symbol: Trading pair (e.g., 'BNB_USDT')
            timeframe: Candle timeframe (e.g., '1d', '4h')
            db_path: Path to SQLite database
            dry_run: If True, don't execute actual trades
            candles_limit: Number of candles to fetch (need 200+ for EMAs)
        """
        self.account_id = account_id
        self.symbol = symbol
        self.timeframe = timeframe
        self.dry_run = dry_run
        self.candles_limit = candles_limit

        # Initialize services and repositories
        self.db = DatabaseManager(db_path)
        self.db.initialize()

        self.account_repo = SQLiteAccountRepository(self.db)
        self.binance_client = BinanceRESTClient(testnet=False)
        self.strategy = FibonacciGoldenZoneStrategy()

        logger.info(
            f"Fibonacci Trading Orchestrator initialized:\n"
            f"  Account: {account_id}\n"
            f"  Symbol: {symbol}\n"
            f"  Timeframe: {timeframe}\n"
            f"  Candles: {candles_limit}\n"
            f"  Dry run: {dry_run}"
        )

    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute complete Fibonacci trading workflow.

        Workflow steps:
        1. Fetch latest candles from Binance
        2. Generate Fibonacci strategy signal
        3. Get current account position
        4. Execute trade if signal is BUY/SELL
        5. Return workflow results

        Returns:
            Dict with workflow results:
                {
                    'status': 'success' | 'failure',
                    'signal': <strategy signal dict>,
                    'trade_executed': bool,
                    'position': <current position dict>,
                    'error': <error message if failed>
                }
        """
        start_time = time.time()
        workflow_name = "Fibonacci Trading Workflow"

        self._log_execution_start(workflow_name, {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'dry_run': self.dry_run
        })

        try:
            # Step 1: Fetch market data
            logger.info("Step 1/4: Fetching market data...")
            df = self._fetch_candles()
            if df is None or len(df) < 200:
                raise OrchestrationError(
                    "Insufficient market data",
                    {'candles_received': len(df) if df is not None else 0}
                )

            # Step 2: Generate signal
            logger.info("Step 2/4: Generating trading signal...")
            signal = self._generate_signal(df)

            # Step 3: Get current position
            logger.info("Step 3/4: Fetching current position...")
            position = self._get_position()

            # Step 4: Execute trade
            logger.info("Step 4/4: Executing trade...")
            trade_executed = self._execute_trade(signal, position)

            # Success result
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
                    'timeframe': self.timeframe,
                    'account_id': self.account_id
                }
            )

            duration = time.time() - start_time
            self._log_execution_end(workflow_name, error_result, duration)

            return error_result

    def _fetch_candles(self) -> Optional[pd.DataFrame]:
        """
        Fetch latest candles from Binance.

        Returns:
            DataFrame with OHLCV data or None if error
        """
        try:
            # Convert symbol format (BNB_USDT -> BNBUSDT)
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
            raise OrchestrationError("Failed to fetch market data", {'error': str(e)})

    def _generate_signal(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate trading signal using Fibonacci strategy.

        Args:
            df: Market data DataFrame

        Returns:
            Signal dictionary from strategy
        """
        try:
            signal = self.strategy.generate_signal(df)

            logger.info(
                f"\nFibonacci Strategy Signal:\n"
                f"  Action: {signal['action']}\n"
                f"  Reason: {signal['reason']}\n"
                f"  Trend: {signal['trend']}\n"
                f"  Current Price: ${signal['current_price']:,.2f}"
            )

            # Log additional details if available
            if 'fib_levels' in signal:
                logger.info(
                    f"\nFibonacci Levels:\n"
                    f"  High: ${signal['fib_levels']['high']:,.2f}\n"
                    f"  Low: ${signal['fib_levels']['low']:,.2f}\n"
                    f"  Golden Zone: ${signal['fib_levels']['0.618']:,.2f} - "
                    f"${signal['fib_levels']['0.500']:,.2f}"
                )

            if 'confirmations' in signal and signal['confirmations']:
                logger.info(f"  Confirmations: {', '.join(signal['confirmations'])}")

            return signal

        except Exception as e:
            logger.error(f"Error generating signal: {e}", exc_info=True)
            raise OrchestrationError(
                "Failed to generate signal",
                {'error': str(e)}
            )

    def _get_position(self) -> Dict[str, float]:
        """
        Get current position from account repository.

        Returns:
            Dict with balance info (usdt_balance, asset_balance, current_price)
        """
        try:
            account = self.account_repo.find_by_id(self.account_id)
            if not account:
                raise OrchestrationError(
                    "Account not found",
                    {'account_id': self.account_id}
                )

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

            position = {
                "usdt_balance": float(usdt_balance),
                "asset_balance": float(asset_balance),
                "current_price": current_price or 0.0,
                "position_value": float(asset_balance) * (current_price or 0.0),
            }

            logger.info(
                f"\nCurrent Position:\n"
                f"  USDT: ${position['usdt_balance']:,.2f}\n"
                f"  {asset_symbol}: {position['asset_balance']:.6f}\n"
                f"  Position value: ${position['position_value']:,.2f}\n"
                f"  Total value: ${position['usdt_balance'] + position['position_value']:,.2f}"
            )

            return position

        except Exception as e:
            logger.error(f"Error getting position: {e}", exc_info=True)
            raise OrchestrationError(
                "Failed to get position",
                {'error': str(e)}
            )

    def _execute_trade(self, signal: Dict, position: Dict) -> bool:
        """
        Execute trade based on signal and position.

        Args:
            signal: Trading signal from strategy
            position: Current position dict

        Returns:
            True if trade executed, False otherwise
        """
        try:
            action = signal['action']

            # HOLD - no action
            if action == 'HOLD':
                logger.info("Signal: HOLD - No trade executed")
                return False

            # Dry run mode
            if self.dry_run:
                logger.info(f"DRY RUN: Would execute {action} signal")
                if action in ['BUY', 'SELL']:
                    logger.info(
                        f"  Entry: ${signal['entry']:,.2f}\n"
                        f"  Stop Loss: ${signal['stop_loss']:,.2f}\n"
                        f"  Take Profit 1: ${signal['take_profit_1']:,.2f}\n"
                        f"  Take Profit 2: ${signal['take_profit_2']:,.2f}\n"
                        f"  Confirmations: {', '.join(signal.get('confirmations', []))}"
                    )
                return False

            # Get account
            account = self.account_repo.find_by_id(self.account_id)
            if not account:
                raise OrchestrationError(
                    "Account not found",
                    {'account_id': self.account_id}
                )

            asset_symbol = self.symbol.split("_")[0]
            asset_currency = Currency.from_string(asset_symbol)
            price = signal['entry']

            # Execute BUY
            if action == 'BUY':
                if position["asset_balance"] > 0:
                    logger.info("Already in position. Skipping BUY.")
                    return False

                return self._execute_buy(
                    account, position, asset_symbol, asset_currency, price, signal
                )

            # Execute SELL
            elif action == 'SELL':
                if position["asset_balance"] <= 0:
                    logger.info("No position to sell. Skipping SELL.")
                    return False

                return self._execute_sell(
                    account, position, asset_symbol, asset_currency, price, signal
                )

            return False

        except Exception as e:
            logger.error(f"Error executing trade: {e}", exc_info=True)
            # Don't raise - trade execution failure shouldn't crash workflow
            return False

    def _execute_buy(
        self,
        account,
        position: Dict,
        asset_symbol: str,
        asset_currency,
        price: float,
        signal: Dict
    ) -> bool:
        """Execute BUY trade."""
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
                f"Confirmations: {', '.join(signal.get('confirmations', []))}"
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
            f"  Take Profit 2: ${signal['take_profit_2']:,.2f}"
        )
        return True

    def _execute_sell(
        self,
        account,
        position: Dict,
        asset_symbol: str,
        asset_currency,
        price: float,
        signal: Dict
    ) -> bool:
        """Execute SELL trade."""
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
                f"Confirmations: {', '.join(signal.get('confirmations', []))}"
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
            f"  Take Profit 2: ${signal['take_profit_2']:,.2f}"
        )
        return True
