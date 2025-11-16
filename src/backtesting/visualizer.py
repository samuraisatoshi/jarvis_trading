"""
Backtest visualization and reporting.

This module creates comprehensive charts and visual reports for backtest results.
Supports multiple chart types: price action, portfolio value, drawdown, trade distribution, etc.

SOLID Principles:
- Single Responsibility: Only handles visualization
- Open/Closed: Easy to add new chart types
- Dependency Inversion: Works with abstracted data models
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.dates import DateFormatter
from typing import List, Dict, Optional
from pathlib import Path

from .models import Trade


class BacktestVisualizer:
    """
    Comprehensive visualization generator for backtest results.

    Creates multi-panel charts showing:
    - Price action with trade signals
    - Portfolio value comparison
    - Drawdown evolution
    - Trade PnL distribution
    - Cumulative returns
    - Period returns (monthly/quarterly)

    All charts are publication-quality with clear labels and legends.
    """

    def __init__(self, figsize: tuple = (20, 14), dpi: int = 150):
        """
        Initialize visualizer.

        Args:
            figsize: Figure size in inches (width, height)
            dpi: Resolution in dots per inch
        """
        self.figsize = figsize
        self.dpi = dpi

    def create_comprehensive_chart(
        self,
        portfolio_df: pd.DataFrame,
        price_df: pd.DataFrame,
        trades: List[Trade],
        baseline_dict: Optional[Dict] = None,
        initial_balance: float = 5000,
        output_path: Optional[str] = None,
        symbol: str = "ASSET",
        strategy_name: str = "Strategy"
    ) -> None:
        """
        Create comprehensive multi-panel backtest visualization.

        Args:
            portfolio_df: DataFrame with portfolio value history
            price_df: DataFrame with OHLCV price data
            trades: List of executed trades
            baseline_dict: Optional baseline (e.g., Buy & Hold) metrics
            initial_balance: Starting capital
            output_path: Path to save chart (if None, displays interactively)
            symbol: Trading pair symbol for labels
            strategy_name: Strategy name for title

        Raises:
            ValueError: If required data is missing or invalid
        """
        if portfolio_df.empty or price_df.empty:
            raise ValueError("portfolio_df and price_df cannot be empty")

        fig = plt.figure(figsize=self.figsize)
        gs = gridspec.GridSpec(4, 2, figure=fig, hspace=0.3, wspace=0.25)

        # 1. Price Chart with Entry/Exit points
        self._plot_price_with_signals(
            fig.add_subplot(gs[0, :]),
            price_df,
            trades,
            symbol
        )

        # 2. Portfolio Value Comparison
        self._plot_portfolio_comparison(
            fig.add_subplot(gs[1, :]),
            portfolio_df,
            price_df,
            baseline_dict,
            initial_balance,
            strategy_name
        )

        # 3. Drawdown Chart
        self._plot_drawdown(
            fig.add_subplot(gs[2, 0]),
            portfolio_df
        )

        # 4. Trade Distribution
        self._plot_trade_distribution(
            fig.add_subplot(gs[2, 1]),
            trades
        )

        # 5. Cumulative Returns
        self._plot_cumulative_returns(
            fig.add_subplot(gs[3, 0]),
            portfolio_df,
            initial_balance
        )

        # 6. Period Returns (Monthly)
        self._plot_period_returns(
            fig.add_subplot(gs[3, 1]),
            portfolio_df
        )

        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=self.dpi, bbox_inches='tight')
            print(f"\nComprehensive chart saved: {output_path}")
        else:
            plt.show()

        plt.close()

    def _plot_price_with_signals(
        self,
        ax: plt.Axes,
        price_df: pd.DataFrame,
        trades: List[Trade],
        symbol: str
    ) -> None:
        """Plot price action with trade entry/exit signals."""
        # Price line
        ax.plot(
            price_df.index,
            price_df['close'],
            label=f'{symbol} Price',
            color='blue',
            linewidth=1,
            alpha=0.7
        )

        # Mark trades
        for trade in trades:
            if not trade.exit_time:
                continue

            entry_time = pd.to_datetime(trade.entry_time)
            exit_time = pd.to_datetime(trade.exit_time)

            # Find nearest indices
            entry_idx = price_df.index.get_indexer([entry_time], method='nearest')[0]
            exit_idx = price_df.index.get_indexer([exit_time], method='nearest')[0]

            # Color based on profit/loss
            color = 'green' if trade.is_winner() else 'red'

            # Markers based on trade side
            entry_marker = '^' if trade.side == 'LONG' else 'v'
            exit_marker = 'v' if trade.side == 'LONG' else '^'

            # Plot entry
            ax.scatter(
                price_df.index[entry_idx],
                price_df.iloc[entry_idx]['close'],
                marker=entry_marker,
                color=color,
                s=100,
                alpha=0.7,
                zorder=5
            )

            # Plot exit
            ax.scatter(
                price_df.index[exit_idx],
                price_df.iloc[exit_idx]['close'],
                marker=exit_marker,
                color=color,
                s=100,
                alpha=0.7,
                zorder=5
            )

        ax.set_ylabel('Price (USD)', fontsize=12, fontweight='bold')
        ax.set_title(f'{symbol} Price with Trade Signals', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend()

    def _plot_portfolio_comparison(
        self,
        ax: plt.Axes,
        portfolio_df: pd.DataFrame,
        price_df: pd.DataFrame,
        baseline_dict: Optional[Dict],
        initial_balance: float,
        strategy_name: str
    ) -> None:
        """Plot portfolio value with baseline comparison."""
        # Strategy portfolio
        ax.plot(
            portfolio_df.index,
            portfolio_df['portfolio_value'],
            label=strategy_name,
            color='green',
            linewidth=2
        )

        # Baseline (if provided)
        if baseline_dict:
            start_idx = 200  # Match engine warmup
            if len(price_df) > start_idx:
                quantity = baseline_dict.get('quantity', 0)
                baseline_values = price_df['close'].iloc[start_idx:] * quantity
                ax.plot(
                    baseline_values.index,
                    baseline_values,
                    label=baseline_dict.get('strategy_name', 'Baseline'),
                    color='orange',
                    linewidth=2,
                    linestyle='--'
                )

        # Initial balance reference line
        ax.axhline(
            initial_balance,
            color='gray',
            linestyle=':',
            linewidth=1,
            alpha=0.7,
            label='Initial Balance'
        )

        ax.set_ylabel('Portfolio Value (USD)', fontsize=12, fontweight='bold')
        ax.set_title('Strategy Performance Comparison', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend()

    def _plot_drawdown(
        self,
        ax: plt.Axes,
        portfolio_df: pd.DataFrame
    ) -> None:
        """Plot drawdown evolution over time."""
        peak = portfolio_df['portfolio_value'].expanding(min_periods=1).max()
        drawdown = (portfolio_df['portfolio_value'] - peak) / peak * 100

        ax.fill_between(
            portfolio_df.index,
            0,
            drawdown,
            color='red',
            alpha=0.3
        )
        ax.plot(
            portfolio_df.index,
            drawdown,
            color='red',
            linewidth=1
        )

        ax.set_ylabel('Drawdown (%)', fontsize=11, fontweight='bold')
        ax.set_title('Drawdown Over Time', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)

    def _plot_trade_distribution(
        self,
        ax: plt.Axes,
        trades: List[Trade]
    ) -> None:
        """Plot distribution of trade PnL."""
        if not trades:
            ax.text(
                0.5, 0.5,
                'No trades executed',
                ha='center',
                va='center',
                transform=ax.transAxes,
                fontsize=12
            )
            return

        # Separate wins and losses
        trade_pnls = [t.pnl_pct for t in trades if t.pnl_pct is not None]
        wins = [p for p in trade_pnls if p > 0]
        losses = [p for p in trade_pnls if p <= 0]

        if wins or losses:
            ax.hist(
                [wins, losses],
                bins=20,
                label=['Wins', 'Losses'],
                color=['green', 'red'],
                alpha=0.7,
                edgecolor='black'
            )
            ax.axvline(0, color='black', linestyle='--', linewidth=1)
            ax.set_xlabel('PnL (%)', fontsize=11, fontweight='bold')
            ax.set_ylabel('Frequency', fontsize=11, fontweight='bold')
            ax.set_title('Trade PnL Distribution', fontsize=12, fontweight='bold')
            ax.legend()
            ax.grid(True, alpha=0.3)

    def _plot_cumulative_returns(
        self,
        ax: plt.Axes,
        portfolio_df: pd.DataFrame,
        initial_balance: float
    ) -> None:
        """Plot cumulative returns over time."""
        cumulative_returns = (
            portfolio_df['portfolio_value'] / initial_balance - 1
        ) * 100

        ax.plot(
            portfolio_df.index,
            cumulative_returns,
            color='purple',
            linewidth=2
        )
        ax.fill_between(
            portfolio_df.index,
            0,
            cumulative_returns,
            alpha=0.3,
            color='purple'
        )
        ax.axhline(0, color='black', linestyle='--', linewidth=1)

        ax.set_ylabel('Cumulative Return (%)', fontsize=11, fontweight='bold')
        ax.set_title('Cumulative Returns', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)

    def _plot_period_returns(
        self,
        ax: plt.Axes,
        portfolio_df: pd.DataFrame,
        period: str = 'M'
    ) -> None:
        """Plot returns by period (monthly/quarterly)."""
        if portfolio_df.empty:
            return

        # Resample to period
        period_data = portfolio_df.resample(period).last()
        period_returns = period_data['portfolio_value'].pct_change() * 100
        period_returns = period_returns.dropna()

        if period_returns.empty:
            ax.text(
                0.5, 0.5,
                'Insufficient data for period analysis',
                ha='center',
                va='center',
                transform=ax.transAxes,
                fontsize=10
            )
            return

        # Color bars by positive/negative
        colors = ['green' if r > 0 else 'red' for r in period_returns]
        period_labels = [d.strftime('%Y-%m') for d in period_returns.index]

        ax.bar(
            range(len(period_returns)),
            period_returns,
            color=colors,
            alpha=0.7,
            edgecolor='black'
        )
        ax.axhline(0, color='black', linestyle='--', linewidth=1)
        ax.set_xticks(range(len(period_returns)))
        ax.set_xticklabels(period_labels, rotation=45, ha='right', fontsize=8)
        ax.set_ylabel('Return (%)', fontsize=11, fontweight='bold')

        period_name = 'Monthly' if period == 'M' else 'Quarterly'
        ax.set_title(f'{period_name} Returns', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')

    def create_simple_chart(
        self,
        portfolio_df: pd.DataFrame,
        output_path: Optional[str] = None
    ) -> None:
        """
        Create simple portfolio value chart.

        Args:
            portfolio_df: DataFrame with portfolio value history
            output_path: Path to save chart
        """
        fig, ax = plt.subplots(figsize=(12, 6))

        ax.plot(
            portfolio_df.index,
            portfolio_df['portfolio_value'],
            color='blue',
            linewidth=2
        )

        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Portfolio Value (USD)', fontsize=12)
        ax.set_title('Portfolio Value Over Time', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=self.dpi, bbox_inches='tight')
            print(f"\nSimple chart saved: {output_path}")
        else:
            plt.show()

        plt.close()
