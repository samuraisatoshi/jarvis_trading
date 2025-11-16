"""
DCA Visualizer - Chart generation module.

This module creates comprehensive visualization charts for DCA strategy analysis.

SOLID Principles:
- Single Responsibility: Only visualization
- Open/Closed: Can add new chart types without modifying existing
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Dict
from .strategy import DCASmartStrategy

# Styling
sns.set_style("darkgrid")
plt.rcParams['figure.figsize'] = (16, 10)


class DCAVisualizer:
    """
    Create visualization charts for DCA strategy analysis.
    """

    def __init__(self, strategy: DCASmartStrategy, df: pd.DataFrame, results: Dict):
        """
        Initialize visualizer.

        Args:
            strategy: Strategy to visualize
            df: Historical data
            results: Results from analyzer
        """
        self.strategy = strategy
        self.df = df
        self.results = results

    def create_comprehensive_chart(self, output_path: Path) -> None:
        """
        Create comprehensive analysis chart with 6 subplots.

        Args:
            output_path: Path to save chart
        """
        fig = plt.figure(figsize=(20, 14))

        # 1. Portfolio Value Comparison
        self._plot_portfolio_value(plt.subplot(3, 2, 1))

        # 2. BNB Price + Trades
        self._plot_price_with_trades(plt.subplot(3, 2, 2))

        # 3. RSI + Buy Intensity
        self._plot_rsi_with_dip_buys(plt.subplot(3, 2, 3))

        # 4. Strategy Comparison
        self._plot_strategy_comparison(plt.subplot(3, 2, 4))

        # 5. Cost Basis Evolution
        self._plot_cost_basis(plt.subplot(3, 2, 5))

        # 6. Investment Summary
        self._plot_summary_text(plt.subplot(3, 2, 6))

        plt.tight_layout()

        # Save
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"\nVisualization saved: {output_path}")

        plt.close()

    def _plot_portfolio_value(self, ax) -> None:
        """Plot portfolio value over time vs Buy & Hold."""
        portfolio_df = pd.DataFrame(self.strategy.portfolio_values)
        portfolio_df.set_index('date', inplace=True)

        # Calculate baselines
        first_price = self.df['close'].iloc[0]
        bh_value = (self.results['initial_capital'] / first_price) * self.df['close']

        ax.plot(portfolio_df.index, portfolio_df['value'],
                label='DCA Smart', linewidth=2, color='green')
        ax.plot(self.df.index, bh_value,
                label='Buy & Hold', linewidth=2, color='blue', alpha=0.7)
        ax.axhline(self.results['initial_capital'], color='gray',
                   linestyle='--', alpha=0.5, label='Initial Capital')
        ax.set_title('Portfolio Value Over Time', fontsize=14, fontweight='bold')
        ax.set_ylabel('Portfolio Value (USD)')
        ax.legend()
        ax.grid(True, alpha=0.3)

    def _plot_price_with_trades(self, ax) -> None:
        """Plot BNB price with trade markers."""
        ax.plot(self.df.index, self.df['close'], label='BNB Price', color='orange', linewidth=1.5)

        # Mark trades
        buy_trades = [t for t in self.strategy.trades if t.type == 'buy']
        sell_trades = [t for t in self.strategy.trades if t.type == 'sell']

        if buy_trades:
            buy_dates = [pd.to_datetime(t.date) for t in buy_trades]
            buy_prices = [t.price for t in buy_trades]
            ax.scatter(buy_dates, buy_prices, color='green', marker='^',
                      s=100, alpha=0.6, label='Buys', zorder=5)

        if sell_trades:
            sell_dates = [pd.to_datetime(t.date) for t in sell_trades]
            sell_prices = [t.price for t in sell_trades]
            ax.scatter(sell_dates, sell_prices, color='red', marker='v',
                      s=150, alpha=0.8, label='Sells (Profit Taking)', zorder=5)

        ax.set_title('BNB Price + Trade Markers', fontsize=14, fontweight='bold')
        ax.set_ylabel('Price (USD)')
        ax.legend()
        ax.grid(True, alpha=0.3)

    def _plot_rsi_with_dip_buys(self, ax) -> None:
        """Plot RSI with dip buying opportunities."""
        ax.plot(self.df.index, self.df['rsi'], label='RSI', color='purple', linewidth=1)
        ax.axhline(70, color='red', linestyle='--', alpha=0.5, label='Overbought')
        ax.axhline(30, color='green', linestyle='--', alpha=0.5, label='Oversold')
        ax.fill_between(self.df.index, 0, 30, alpha=0.1, color='green')
        ax.fill_between(self.df.index, 70, 100, alpha=0.1, color='red')

        # Mark dip buys
        buy_trades = [t for t in self.strategy.trades if t.type == 'buy']
        dip_buys = [t for t in buy_trades if t.multiplier >= 2.0]
        if dip_buys:
            dip_dates = [pd.to_datetime(t.date) for t in dip_buys]
            dip_rsi = [t.rsi for t in dip_buys]
            ax.scatter(dip_dates, dip_rsi, color='darkgreen', marker='o',
                      s=200, alpha=0.8, label='Dip Buys (2x+)', zorder=5)

        ax.set_title('RSI + Dip Buying Opportunities', fontsize=14, fontweight='bold')
        ax.set_ylabel('RSI')
        ax.legend()
        ax.grid(True, alpha=0.3)

    def _plot_strategy_comparison(self, ax) -> None:
        """Plot strategy performance comparison."""
        strategies = ['DCA Smart', 'Buy & Hold', 'B&H + DCA', 'DCA Fixed']
        returns = [
            self.results['total_return_pct'],
            self.results['buy_hold_return_pct'],
            self.results['buy_hold_dca_return_pct'],
            self.results['dca_fixed_return_pct']
        ]
        colors = ['green', 'blue', 'cyan', 'orange']

        bars = ax.barh(strategies, returns, color=colors, alpha=0.7)
        ax.set_xlabel('Return (%)')
        ax.set_title('Strategy Performance Comparison', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='x')

        # Add value labels
        for i, (bar, ret) in enumerate(zip(bars, returns)):
            ax.text(ret + 5, i, f"{ret:.1f}%", va='center', fontweight='bold')

    def _plot_cost_basis(self, ax) -> None:
        """Plot cost basis evolution."""
        cost_basis_history = []
        running_invested = 0
        running_bnb = 0

        buy_trades = [t for t in self.strategy.trades if t.type == 'buy']
        for trade in buy_trades:
            running_invested += trade.amount_usd
            running_bnb += trade.quantity
            cost_basis_history.append({
                'date': pd.to_datetime(trade.date),
                'cost_basis': running_invested / running_bnb if running_bnb > 0 else 0,
                'price': trade.price
            })

        if cost_basis_history:
            cb_df = pd.DataFrame(cost_basis_history)
            ax.plot(cb_df['date'], cb_df['cost_basis'],
                   label='Average Cost Basis', color='green', linewidth=2)
            ax.plot(cb_df['date'], cb_df['price'],
                   label='Market Price', color='orange', linewidth=1, alpha=0.7)
            ax.fill_between(cb_df['date'], cb_df['cost_basis'], cb_df['price'],
                           where=(cb_df['price'] >= cb_df['cost_basis']),
                           alpha=0.2, color='green', label='Profit Zone')
            ax.set_title('Cost Basis vs Market Price', fontsize=14, fontweight='bold')
            ax.set_ylabel('Price (USD)')
            ax.legend()
            ax.grid(True, alpha=0.3)

    def _plot_summary_text(self, ax) -> None:
        """Plot investment summary as text."""
        ax.axis('off')

        summary_text = f"""
    DCA SMART STRATEGY - SUMMARY
    {'='*50}

    PORTFOLIO
    Final Value:        ${self.results['final_portfolio']:,.2f}
    BNB Holdings:       {self.results['bnb_balance']:.4f} BNB
    USDT Balance:       ${self.results['usdt_balance']:,.2f}
    Reserved (Profits): ${self.results['usdt_reserved']:,.2f}

    PERFORMANCE
    Total Return:       {self.results['total_return_pct']:.2f}% (${self.results['total_return_usd']:,.2f})
    Buy & Hold:         {self.results['buy_hold_return_pct']:.2f}%
    B&H + DCA:          {self.results['buy_hold_dca_return_pct']:.2f}%
    DCA Fixed:          {self.results['dca_fixed_return_pct']:.2f}%

    INVESTMENT
    Total Invested:     ${self.results['total_invested']:,.2f}
    Average Cost:       ${self.results['avg_cost']:.2f}
    Final Price:        ${self.results['final_price']:.2f}

    TRADING ACTIVITY
    Total Trades:       {self.results['total_trades']}
    Buys:              {self.results['buy_trades']}
    Dip Buys (2x+):    {self.results['dip_buys']}
    Profit Sells:      {self.results['sell_trades']}
    Profit Taken:      ${self.results['total_profit_taken']:,.2f}

    VERDICT
    {'✅ SUPERIOR' if self.results['total_return_pct'] > self.results['buy_hold_return_pct'] else '❌ INFERIOR'} to Buy & Hold
    Alpha: {self.results['total_return_pct'] - self.results['buy_hold_return_pct']:+.2f}%
    """

        ax.text(0.1, 0.5, summary_text, fontsize=10, family='monospace',
                verticalalignment='center')
