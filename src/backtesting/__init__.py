"""
Backtesting module for trading strategies.

This module provides a comprehensive backtesting framework following SOLID principles:
- Strategy Pattern for extensible strategy implementations
- Dependency Injection for testability
- Clear separation of concerns

Main components:
- models: Data structures (Trade, BacktestMetrics)
- engine: Core backtest execution engine
- metrics_calculator: Performance metrics computation
- baseline_strategies: Baseline comparison strategies (Buy & Hold, etc.)
- visualizer: Chart generation and reporting
- fibonacci_strategy: Fibonacci Golden Zone strategy implementation

Example:
    >>> from src.backtesting import FibonacciBacktester, MetricsCalculator
    >>> backtester = FibonacciBacktester(initial_balance=5000)
    >>> df = backtester.fetch_historical_data('BNB_USDT', '4h', '2023-11-01')
    >>> trades, portfolio = backtester.run(df)
    >>> metrics = MetricsCalculator.calculate(trades, portfolio, 5000, 'BNB_USDT', '4h')
"""

from .models import Trade, BacktestMetrics, TradeType, ExitReason, PortfolioState
from .engine import BacktestEngine, TradingStrategy
from .metrics_calculator import MetricsCalculator
from .baseline_strategies import (
    BaselineStrategy,
    BuyAndHoldBaseline,
    SimpleDCABaseline,
    compare_with_baseline,
    print_baseline_comparison
)
from .visualizer import BacktestVisualizer
from .fibonacci_strategy import FibonacciBacktestStrategy, FibonacciBacktester

__all__ = [
    # Models
    'Trade',
    'BacktestMetrics',
    'TradeType',
    'ExitReason',
    'PortfolioState',
    # Engine
    'BacktestEngine',
    'TradingStrategy',
    # Metrics
    'MetricsCalculator',
    # Baselines
    'BaselineStrategy',
    'BuyAndHoldBaseline',
    'SimpleDCABaseline',
    'compare_with_baseline',
    'print_baseline_comparison',
    # Visualization
    'BacktestVisualizer',
    # Fibonacci Strategy
    'FibonacciBacktestStrategy',
    'FibonacciBacktester',
]

__version__ = '1.0.0'
