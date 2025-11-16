"""
Baseline comparison strategies for backtesting.

This module provides baseline strategies to compare against custom trading strategies.
Common baselines include Buy & Hold and Simple DCA.

SOLID Principles:
- Single Responsibility: Each baseline strategy has one clear behavior
- Open/Closed: Easy to add new baseline strategies
- Liskov Substitution: All baselines implement same interface
"""

import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from typing import Dict


class BaselineStrategy(ABC):
    """
    Abstract base class for baseline strategies.

    Baseline strategies provide comparison benchmarks for custom strategies.
    All baselines should implement calculate() method.
    """

    @abstractmethod
    def calculate(
        self,
        df: pd.DataFrame,
        initial_balance: float,
        start_idx: int = 0
    ) -> Dict:
        """
        Calculate baseline strategy performance.

        Args:
            df: DataFrame with OHLCV data
            initial_balance: Starting capital
            start_idx: Index to start baseline from

        Returns:
            Dictionary with performance metrics
        """
        pass


class BuyAndHoldBaseline(BaselineStrategy):
    """
    Buy & Hold baseline strategy.

    This strategy simulates buying the asset at the start and holding until the end.
    It provides a simple benchmark that many active strategies struggle to beat.

    The strategy:
    1. Buy asset at entry price with all capital
    2. Hold through all market movements
    3. Sell at exit price

    Metrics calculated:
    - Total return (USD and %)
    - Annualized return
    - Max drawdown
    - Entry/exit prices and dates
    """

    def calculate(
        self,
        df: pd.DataFrame,
        initial_balance: float,
        start_idx: int = 200
    ) -> Dict:
        """
        Calculate Buy & Hold performance.

        Args:
            df: DataFrame with OHLCV data (must have 'close' column)
            initial_balance: Starting capital in USD
            start_idx: Index to start baseline from (default 200 for indicator warmup)

        Returns:
            Dictionary with:
                - strategy_name: 'Buy & Hold'
                - initial_balance: Starting capital
                - final_balance: Ending capital
                - total_return_pct: Total return percentage
                - total_return_usd: Total return in USD
                - annualized_return_pct: Annualized return percentage
                - max_drawdown_pct: Maximum drawdown percentage
                - entry_price: Price at entry
                - exit_price: Price at exit
                - quantity: Amount of asset purchased
                - entry_date: Entry date
                - exit_date: Exit date

        Raises:
            ValueError: If start_idx is out of range
        """
        if start_idx >= len(df):
            raise ValueError(
                f"start_idx ({start_idx}) exceeds dataframe length ({len(df)})"
            )

        # Entry and exit prices
        entry_price = df.iloc[start_idx]['close']
        exit_price = df.iloc[-1]['close']

        # Calculate quantity and final value
        quantity = initial_balance / entry_price
        final_value = quantity * exit_price

        # Returns
        total_return_usd = final_value - initial_balance
        total_return_pct = (total_return_usd / initial_balance) * 100

        # Annualized return
        days = (df.index[-1] - df.index[start_idx]).days
        years = days / 365.25
        annualized_return_pct = (
            ((final_value / initial_balance) ** (1 / years) - 1) * 100
            if years > 0 else 0
        )

        # Max drawdown
        portfolio_values = df['close'].iloc[start_idx:] * quantity
        peak = portfolio_values.expanding(min_periods=1).max()
        drawdown = (portfolio_values - peak) / peak * 100
        max_drawdown_pct = drawdown.min()

        return {
            'strategy_name': 'Buy & Hold',
            'initial_balance': initial_balance,
            'final_balance': final_value,
            'total_return_pct': total_return_pct,
            'total_return_usd': total_return_usd,
            'annualized_return_pct': annualized_return_pct,
            'max_drawdown_pct': max_drawdown_pct,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'quantity': quantity,
            'entry_date': str(df.index[start_idx].date()),
            'exit_date': str(df.index[-1].date())
        }


class SimpleDCABaseline(BaselineStrategy):
    """
    Simple Dollar Cost Averaging baseline.

    This strategy simulates regular purchases at fixed intervals regardless of price.

    The strategy:
    1. Invest fixed amount at regular intervals
    2. Accumulate position over time
    3. Final value = accumulated quantity * final price

    Metrics calculated:
    - Total return (USD and %)
    - Average cost basis
    - Number of purchases
    - Final quantity
    """

    def __init__(self, investment_amount: float, interval_days: int = 7):
        """
        Initialize Simple DCA baseline.

        Args:
            investment_amount: Amount to invest per interval
            interval_days: Days between investments (default 7 for weekly)
        """
        self.investment_amount = investment_amount
        self.interval_days = interval_days

    def calculate(
        self,
        df: pd.DataFrame,
        initial_balance: float,
        start_idx: int = 200
    ) -> Dict:
        """
        Calculate Simple DCA performance.

        Args:
            df: DataFrame with OHLCV data
            initial_balance: Starting capital (not used, but kept for interface)
            start_idx: Index to start baseline from

        Returns:
            Dictionary with performance metrics
        """
        if start_idx >= len(df):
            raise ValueError(
                f"start_idx ({start_idx}) exceeds dataframe length ({len(df)})"
            )

        df_subset = df.iloc[start_idx:].copy()

        # Resample to interval frequency
        freq_str = f'{self.interval_days}D'
        resampled = df_subset.resample(freq_str).first()

        # Simulate regular purchases
        total_invested = 0
        total_quantity = 0

        for date, row in resampled.iterrows():
            price = row['close']
            if not pd.isna(price):
                quantity = self.investment_amount / price
                total_quantity += quantity
                total_invested += self.investment_amount

        # Final value
        final_price = df.iloc[-1]['close']
        final_value = total_quantity * final_price

        # Returns
        total_return_usd = final_value - total_invested
        total_return_pct = (
            (total_return_usd / total_invested) * 100
            if total_invested > 0 else 0
        )

        # Average cost basis
        avg_cost_basis = (
            total_invested / total_quantity
            if total_quantity > 0 else 0
        )

        # Annualized return
        days = (df.index[-1] - df.index[start_idx]).days
        years = days / 365.25
        annualized_return_pct = (
            ((final_value / total_invested) ** (1 / years) - 1) * 100
            if years > 0 and total_invested > 0 else 0
        )

        return {
            'strategy_name': f'Simple DCA ({self.interval_days}d)',
            'initial_balance': total_invested,
            'final_balance': final_value,
            'total_return_pct': total_return_pct,
            'total_return_usd': total_return_usd,
            'annualized_return_pct': annualized_return_pct,
            'num_purchases': len(resampled),
            'total_quantity': total_quantity,
            'avg_cost_basis': avg_cost_basis,
            'entry_date': str(df.index[start_idx].date()),
            'exit_date': str(df.index[-1].date())
        }


def compare_with_baseline(
    strategy_metrics: Dict,
    baseline_metrics: Dict
) -> Dict:
    """
    Compare strategy performance with baseline.

    Args:
        strategy_metrics: Metrics from active strategy
        baseline_metrics: Metrics from baseline strategy

    Returns:
        Dictionary with comparison results
    """
    # Extract returns
    strategy_return = strategy_metrics.get('total_return_pct', 0)
    baseline_return = baseline_metrics.get('total_return_pct', 0)

    # Calculate outperformance
    outperformance = strategy_return - baseline_return

    # Determine winner
    if outperformance > 0:
        winner = strategy_metrics.get('strategy_name', 'Strategy')
    elif outperformance < 0:
        winner = baseline_metrics.get('strategy_name', 'Baseline')
    else:
        winner = 'TIE'

    return {
        'winner': winner,
        'outperformance_pct': outperformance,
        'strategy_return_pct': strategy_return,
        'baseline_return_pct': baseline_return,
        'strategy_sharpe': strategy_metrics.get('sharpe_ratio'),
        'strategy_max_dd': strategy_metrics.get('max_drawdown_pct'),
        'baseline_max_dd': baseline_metrics.get('max_drawdown_pct')
    }


def print_baseline_comparison(
    strategy_metrics: Dict,
    baseline_metrics: Dict
) -> None:
    """
    Print formatted comparison between strategy and baseline.

    Args:
        strategy_metrics: Metrics from active strategy
        baseline_metrics: Metrics from baseline strategy
    """
    comparison = compare_with_baseline(strategy_metrics, baseline_metrics)

    print("\n" + "="*80)
    print(" STRATEGY vs BASELINE COMPARISON")
    print("="*80)
    print(f"\n Winner: {comparison['winner']}")
    print(f" Outperformance: {comparison['outperformance_pct']:+.2f}%")

    print(f"\n {'Metric':<30} {'Strategy':<25} {'Baseline':<25}")
    print(" " + "-"*80)

    # Strategy names
    strat_name = strategy_metrics.get('strategy_name', 'Strategy')
    base_name = baseline_metrics.get('strategy_name', 'Baseline')
    print(f" {'Name':<30} {strat_name:<25} {base_name:<25}")

    # Returns
    print(f" {'Total Return':<30} "
          f"{strategy_metrics.get('total_return_pct', 0):>23.2f}% "
          f"{baseline_metrics.get('total_return_pct', 0):>23.2f}%")

    print(f" {'Annualized Return':<30} "
          f"{strategy_metrics.get('annualized_return_pct', 0):>23.2f}% "
          f"{baseline_metrics.get('annualized_return_pct', 0):>23.2f}%")

    # Risk metrics
    print(f" {'Max Drawdown':<30} "
          f"{strategy_metrics.get('max_drawdown_pct', 0):>23.2f}% "
          f"{baseline_metrics.get('max_drawdown_pct', 0):>23.2f}%")

    # Sharpe (if available)
    if 'sharpe_ratio' in strategy_metrics:
        print(f" {'Sharpe Ratio':<30} "
              f"{strategy_metrics.get('sharpe_ratio', 0):>24.2f} "
              f"{'N/A':>25}")

    print("="*80 + "\n")
