"""
Base classes and interfaces for trading strategies.

This module defines the Strategy Pattern interface that all trading strategies
must implement. It provides a consistent contract for signal generation,
enabling strategies to be used interchangeably across backtesting, live trading,
and paper trading.

SOLID Principles:
- Single Responsibility: Only defines strategy interface
- Open/Closed: Open for extension (new strategies), closed for modification
- Liskov Substitution: All strategies are substitutable via this interface
- Interface Segregation: Minimal interface (only essential methods)
- Dependency Inversion: Depend on this abstraction, not concrete strategies
"""

from abc import ABC, abstractmethod
from typing import Dict
import pandas as pd


class TradingStrategy(ABC):
    """
    Abstract base class for all trading strategies.

    This interface defines the contract that all trading strategies must fulfill.
    Strategies implementing this interface can be used with the backtesting engine,
    live trading systems, and paper trading without modification.

    The Strategy Pattern allows algorithms to be selected and swapped at runtime,
    making the system flexible and extensible.

    Methods:
        generate_signal: Core method that analyzes market data and returns a trading signal

    Example:
        >>> class MyStrategy(TradingStrategy):
        ...     def generate_signal(self, df: pd.DataFrame) -> Dict:
        ...         # Implementation here
        ...         return {'action': 'BUY', 'entry': 100.0, ...}
        ...
        >>> strategy = MyStrategy()
        >>> signal = strategy.generate_signal(market_data)
    """

    @abstractmethod
    def generate_signal(self, df: pd.DataFrame) -> Dict:
        """
        Generate a trading signal based on market data analysis.

        This is the core method that all strategies must implement. It receives
        historical market data and returns a decision (BUY/SELL/HOLD) along with
        relevant trading parameters.

        Args:
            df: DataFrame with OHLCV (Open, High, Low, Close, Volume) data.
                Must be indexed by timestamp and contain at minimum:
                - 'open': Opening price
                - 'high': Highest price
                - 'low': Lowest price
                - 'close': Closing price
                - 'volume': Trading volume

        Returns:
            Dictionary containing trading signal with the following structure:
            {
                'action': str,           # 'BUY', 'SELL', or 'HOLD'
                'reason': str,           # Human-readable explanation
                'trend': str,            # Market trend context (optional)
                'current_price': float,  # Current market price

                # Required for BUY/SELL signals:
                'entry': float,          # Entry price
                'stop_loss': float,      # Stop loss price
                'take_profit_1': float,  # First take profit target
                'take_profit_2': float,  # Second take profit target (optional)

                # Optional metadata:
                'confirmations': list,   # List of confirmation signals
                'confidence': float,     # Confidence score 0-1 (optional)
                'metadata': dict,        # Strategy-specific data (optional)
            }

        Raises:
            ValueError: If DataFrame is missing required columns or has insufficient data
            Exception: Strategy-specific errors during analysis

        Note:
            - Strategies should handle their own error cases gracefully
            - Return HOLD signal on errors rather than raising exceptions
            - Include detailed 'reason' field for debugging
        """
        pass

    def validate_dataframe(self, df: pd.DataFrame, required_columns: list = None) -> None:
        """
        Validate that DataFrame has required structure and columns.

        This helper method can be used by strategies to validate input data
        before processing. It's optional but recommended for robust implementations.

        Args:
            df: DataFrame to validate
            required_columns: List of required column names (default: OHLCV)

        Raises:
            ValueError: If DataFrame is invalid or missing required columns
        """
        if required_columns is None:
            required_columns = ['open', 'high', 'low', 'close', 'volume']

        # Check DataFrame is not empty
        if df is None or len(df) == 0:
            raise ValueError("DataFrame is empty")

        # Check required columns exist
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            raise ValueError(
                f"DataFrame missing required columns: {missing_cols}. "
                f"Available columns: {list(df.columns)}"
            )

        # Check for sufficient data (minimum 1 candle)
        if len(df) < 1:
            raise ValueError("DataFrame must contain at least 1 row of data")


class BaseIndicatorStrategy(TradingStrategy):
    """
    Extended base class for indicator-based strategies.

    This class provides common functionality for strategies that rely on
    technical indicators (RSI, EMA, MACD, etc.). It includes helper methods
    for calculating indicators and detecting patterns.

    Strategies using technical indicators should inherit from this class
    instead of TradingStrategy directly.
    """

    @staticmethod
    def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """
        Calculate RSI (Relative Strength Index) indicator.

        Args:
            prices: Series of closing prices
            period: RSI period (default 14)

        Returns:
            Series of RSI values (0-100)
        """
        delta = prices.diff()
        gains = delta.where(delta > 0, 0)
        losses = -delta.where(delta < 0, 0)

        avg_gains = gains.rolling(window=period, min_periods=period).mean()
        avg_losses = losses.rolling(window=period, min_periods=period).mean()

        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))

        return rsi

    @staticmethod
    def calculate_ema(prices: pd.Series, span: int) -> pd.Series:
        """
        Calculate EMA (Exponential Moving Average).

        Args:
            prices: Series of prices
            span: EMA span (period)

        Returns:
            Series of EMA values
        """
        return prices.ewm(span=span, adjust=False).mean()

    @staticmethod
    def calculate_sma(prices: pd.Series, period: int) -> pd.Series:
        """
        Calculate SMA (Simple Moving Average).

        Args:
            prices: Series of prices
            period: SMA period

        Returns:
            Series of SMA values
        """
        return prices.rolling(window=period).mean()
