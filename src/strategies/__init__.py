"""
Trading strategies package.

This package provides a Strategy Pattern implementation for trading strategies,
enabling flexible and extensible algorithm selection for backtesting, live trading,
and paper trading.

Available Strategies:
- FibonacciGoldenZoneStrategy: Fibonacci retracement-based strategy targeting 50%-61.8% zone

Base Classes:
- TradingStrategy: Abstract base class for all strategies
- BaseIndicatorStrategy: Extended base for indicator-based strategies

Data Models:
- FibonacciLevels: Fibonacci retracement/extension levels
- TradeSignal: Complete trading signal with metadata
- TrendType: Market trend classification (UPTREND, DOWNTREND, LATERAL)
- SignalType: Trading signal types (BUY, SELL, HOLD)
- ConfirmationSignal: Types of confirmation signals

Example:
    >>> from src.strategies import FibonacciGoldenZoneStrategy
    >>> strategy = FibonacciGoldenZoneStrategy()
    >>> signal = strategy.generate_signal(market_data)
    >>> if signal['action'] == 'BUY':
    ...     execute_trade(signal)
"""

from src.strategies.base import TradingStrategy, BaseIndicatorStrategy
from src.strategies.models import (
    FibonacciLevels,
    TradeSignal,
    TrendType,
    SignalType,
    ConfirmationSignal,
    SwingPoint,
)
from src.strategies.fibonacci_golden_zone import FibonacciGoldenZoneStrategy

__all__ = [
    # Base classes
    'TradingStrategy',
    'BaseIndicatorStrategy',

    # Concrete strategies
    'FibonacciGoldenZoneStrategy',

    # Data models
    'FibonacciLevels',
    'TradeSignal',
    'TrendType',
    'SignalType',
    'ConfirmationSignal',
    'SwingPoint',
]

__version__ = '1.0.0'
