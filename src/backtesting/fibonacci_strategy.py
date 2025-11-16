"""
Fibonacci Golden Zone backtest strategy implementation.

This module integrates the Fibonacci Golden Zone strategy with the backtest engine.
It wraps the strategy logic and provides the interface required by BacktestEngine.

SOLID Principles:
- Single Responsibility: Only handles Fibonacci strategy integration
- Dependency Inversion: Depends on TradingStrategy abstraction
- Open/Closed: Can be extended with variants
"""

import sys
from pathlib import Path
from typing import Dict
import pandas as pd

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'scripts'))

from src.backtesting.engine import TradingStrategy, BacktestEngine
from src.infrastructure.exchange.binance_rest_client import BinanceRESTClient


class FibonacciBacktestStrategy(TradingStrategy):
    """
    Fibonacci Golden Zone strategy wrapper for backtesting.

    This class adapts the FibonacciGoldenZoneStrategy to work with the
    BacktestEngine by implementing the TradingStrategy interface.

    The strategy identifies high-probability setups using:
    - Fibonacci retracement levels (Golden Zone: 50%-61.8%)
    - Trend identification (EMA crossovers)
    - Multiple confirmation signals
    - Risk management (stop loss and take profit levels)
    """

    def __init__(self):
        """Initialize Fibonacci strategy."""
        # Lazy import to avoid circular dependencies
        try:
            from fibonacci_golden_zone_strategy import FibonacciGoldenZoneStrategy
            self.strategy = FibonacciGoldenZoneStrategy()
        except ImportError as e:
            raise ImportError(
                f"Failed to import FibonacciGoldenZoneStrategy: {e}\n"
                "Ensure fibonacci_golden_zone_strategy.py is in scripts/ directory"
            )

    def generate_signal(self, df: pd.DataFrame) -> Dict:
        """
        Generate trading signal using Fibonacci strategy.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Dictionary with:
                - action: 'BUY', 'SELL', or 'HOLD'
                - stop_loss: Stop loss price
                - take_profit_1: First take profit
                - take_profit_2: Second take profit
                - confirmations: List of confirmation signals
        """
        return self.strategy.generate_signal(df)


class FibonacciBacktester:
    """
    Comprehensive Fibonacci strategy backtester.

    This class provides a high-level interface for backtesting the Fibonacci
    Golden Zone strategy. It handles data fetching, backtest execution,
    and results aggregation.

    Example:
        >>> backtester = FibonacciBacktester(initial_balance=5000)
        >>> df = backtester.fetch_historical_data('BNB_USDT', '4h', '2023-11-01')
        >>> trades, portfolio_df = backtester.run(df)
    """

    def __init__(self, initial_balance: float = 5000):
        """
        Initialize Fibonacci backtester.

        Args:
            initial_balance: Starting capital in USD
        """
        self.initial_balance = initial_balance
        strategy = FibonacciBacktestStrategy()
        self.engine = BacktestEngine(initial_balance, strategy)

        print(f"\nFibonacci Backtester initialized with ${initial_balance:,.2f}")

    def fetch_historical_data(
        self,
        symbol: str,
        timeframe: str,
        start_date: str
    ) -> pd.DataFrame:
        """
        Fetch historical candle data from Binance.

        Args:
            symbol: Trading pair (e.g., 'BNB_USDT')
            timeframe: Candle timeframe (e.g., '4h', '1d')
            start_date: Start date in 'YYYY-MM-DD' format

        Returns:
            DataFrame with OHLCV data indexed by timestamp

        Raises:
            ValueError: If no data received from exchange
        """
        print(f"\nFetching historical data:")
        print(f"  Symbol: {symbol}")
        print(f"  Timeframe: {timeframe}")
        print(f"  Start Date: {start_date}")

        client = BinanceRESTClient(testnet=False)
        binance_symbol = symbol.replace("_", "")

        # Convert start_date to timestamp
        start_dt = pd.to_datetime(start_date)
        start_ts = int(start_dt.timestamp() * 1000)

        # Fetch all available data since start
        all_klines = []
        batch_size = 1000
        current_start = start_ts

        while True:
            klines = client.get_klines(
                symbol=binance_symbol,
                interval=timeframe,
                limit=batch_size,
                start_time=current_start
            )

            if not klines or len(klines) == 0:
                break

            all_klines.extend(klines)

            # Update start time for next batch
            current_start = klines[-1]['close_time'] + 1

            # Break if we got less than batch_size (no more data)
            if len(klines) < batch_size:
                break

            if len(all_klines) % 5000 == 0:
                print(f"  Fetched {len(all_klines)} candles so far...")

        if not all_klines:
            raise ValueError(f"No data received from Binance for {symbol}")

        # Convert to DataFrame
        df = pd.DataFrame(all_klines)
        df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms")
        df = df[["timestamp", "open", "high", "low", "close", "volume"]]
        df.set_index("timestamp", inplace=True)

        print(f"\nTotal fetched: {len(df)} candles")
        print(f"Date range: {df.index[0]} to {df.index[-1]}")

        return df

    def run(
        self,
        df: pd.DataFrame,
        warmup_periods: int = 200
    ) -> tuple:
        """
        Run backtest on historical data.

        Args:
            df: DataFrame with OHLCV data
            warmup_periods: Number of candles for indicator warmup

        Returns:
            Tuple of (trades_list, portfolio_dataframe)
        """
        return self.engine.run(df, warmup_periods)

    def get_final_balance(self) -> float:
        """Get final portfolio balance."""
        return self.engine.get_final_balance()

    def get_trade_count(self) -> int:
        """Get total number of trades."""
        return self.engine.get_trade_count()
