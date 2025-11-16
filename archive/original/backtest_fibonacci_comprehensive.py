#!/usr/bin/env python3
"""
Comprehensive Fibonacci Golden Zone Strategy Backtest

Executes detailed backtesting comparing:
1. Fibonacci Golden Zone Strategy
2. Buy & Hold baseline

Features:
- 2-year historical analysis (Nov 2023 - Nov 2025)
- Quarterly performance breakdown
- Detailed trade analysis
- Visual comparisons
- Risk metrics (Sharpe, Max Drawdown, Win Rate, etc.)
- Market condition analysis

Usage:
    python scripts/backtest_fibonacci_comprehensive.py --symbol BNB_USDT --timeframe 4h --balance 5000
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.dates import DateFormatter

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.exchange.binance_rest_client import BinanceRESTClient

sys.path.insert(0, str(project_root / 'scripts'))
from fibonacci_golden_zone_strategy import FibonacciGoldenZoneStrategy


@dataclass
class Trade:
    """Single trade record."""
    entry_time: str
    entry_price: float
    exit_time: Optional[str] = None
    exit_price: Optional[float] = None
    quantity: float = 0.0
    side: str = 'LONG'
    stop_loss: Optional[float] = None
    take_profit_1: Optional[float] = None
    take_profit_2: Optional[float] = None
    confirmations: Optional[List[str]] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    duration_hours: Optional[float] = None
    exit_reason: Optional[str] = None

    def close(self, exit_time: str, exit_price: float, reason: str = 'manual'):
        """Close the trade and calculate PnL."""
        self.exit_time = exit_time
        self.exit_price = exit_price
        self.exit_reason = reason

        if self.side == 'LONG':
            self.pnl = (exit_price - self.entry_price) * self.quantity
            self.pnl_pct = ((exit_price - self.entry_price) / self.entry_price) * 100
        else:  # SHORT
            self.pnl = (self.entry_price - exit_price) * self.quantity
            self.pnl_pct = ((self.entry_price - exit_price) / self.entry_price) * 100

        # Duration
        entry_dt = pd.to_datetime(self.entry_time)
        exit_dt = pd.to_datetime(exit_time)
        self.duration_hours = (exit_dt - entry_dt).total_seconds() / 3600


@dataclass
class BacktestMetrics:
    """Backtest performance metrics."""
    strategy_name: str
    symbol: str
    timeframe: str
    start_date: str
    end_date: str
    initial_balance: float
    final_balance: float
    total_return_pct: float
    total_return_usd: float
    annualized_return_pct: float
    sharpe_ratio: float
    max_drawdown_pct: float
    max_drawdown_usd: float
    win_rate_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    average_win_pct: float
    average_loss_pct: float
    profit_factor: float
    best_trade_pct: float
    worst_trade_pct: float
    avg_trade_duration_hours: float
    longest_win_streak: int
    longest_loss_streak: int
    time_in_market_pct: float


class FibonacciBacktester:
    """
    Comprehensive backtesting engine for Fibonacci Golden Zone strategy.
    """

    def __init__(self, initial_balance: float = 5000):
        """Initialize backtester."""
        self.initial_balance = initial_balance
        self.strategy = FibonacciGoldenZoneStrategy()
        print(f"\nInitialized backtester with ${initial_balance:,.2f}")

    def fetch_historical_data(
        self, symbol: str, timeframe: str, start_date: str
    ) -> pd.DataFrame:
        """Fetch historical candle data from Binance."""
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

            print(f"  Fetched {len(all_klines)} candles so far...")

        if not all_klines:
            raise ValueError(f"No data received from Binance for {symbol}")

        df = pd.DataFrame(all_klines)
        df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms")
        df = df[["timestamp", "open", "high", "low", "close", "volume"]]
        df.set_index("timestamp", inplace=True)

        print(f"\nTotal fetched: {len(df)} candles")
        print(f"Date range: {df.index[0]} to {df.index[-1]}")

        return df

    def simulate_trades(self, df: pd.DataFrame) -> Tuple[List[Trade], pd.DataFrame]:
        """
        Simulate trading on historical data.

        Returns:
            Tuple of (trades_list, portfolio_df)
        """
        print("\n" + "="*80)
        print("SIMULATING TRADES")
        print("="*80)

        trades = []
        current_trade: Optional[Trade] = None

        # Portfolio tracking
        portfolio_data = []

        # Need at least 200 candles for strategy
        if len(df) < 200:
            raise ValueError(f"Need at least 200 candles, got {len(df)}")

        # Start from candle 200 (after EMA warmup)
        start_idx = 200

        # Initialize portfolio
        cash = self.initial_balance
        position_value = 0.0

        # Iterate through candles
        for i in range(start_idx, len(df)):
            df_slice = df.iloc[:i+1]
            current_candle = df_slice.iloc[-1]
            current_time = df_slice.index[-1]
            current_price = current_candle['close']

            # Update position value if in trade
            if current_trade:
                if current_trade.side == 'LONG':
                    position_value = current_trade.quantity * current_price
                else:  # SHORT
                    # For short: PnL = (entry - current) * quantity
                    position_value = current_trade.quantity * current_trade.entry_price + \
                                   (current_trade.entry_price - current_price) * current_trade.quantity
            else:
                position_value = 0.0

            portfolio_value = cash + position_value

            # Check if we have open position
            if current_trade:
                # Check stop loss
                if current_trade.stop_loss:
                    hit_sl = False
                    if current_trade.side == 'LONG' and current_price <= current_trade.stop_loss:
                        hit_sl = True
                    elif current_trade.side == 'SHORT' and current_price >= current_trade.stop_loss:
                        hit_sl = True

                    if hit_sl:
                        current_trade.close(str(current_time), current_trade.stop_loss, 'stop_loss')
                        cash += self.initial_balance + current_trade.pnl
                        trades.append(current_trade)
                        print(f"[{current_time.strftime('%Y-%m-%d %H:%M')}] STOP LOSS @ ${current_trade.stop_loss:,.2f} | PnL: ${current_trade.pnl:+,.2f} ({current_trade.pnl_pct:+.2f}%)")
                        current_trade = None
                        position_value = 0.0
                        portfolio_value = cash
                        portfolio_data.append({
                            'timestamp': current_time,
                            'price': current_price,
                            'cash': cash,
                            'position_value': position_value,
                            'portfolio_value': portfolio_value,
                            'in_position': False
                        })
                        continue

                # Check take profit 1
                if current_trade.take_profit_1:
                    hit_tp = False
                    if current_trade.side == 'LONG' and current_price >= current_trade.take_profit_1:
                        hit_tp = True
                    elif current_trade.side == 'SHORT' and current_price <= current_trade.take_profit_1:
                        hit_tp = True

                    if hit_tp:
                        current_trade.close(str(current_time), current_trade.take_profit_1, 'take_profit')
                        cash += self.initial_balance + current_trade.pnl
                        trades.append(current_trade)
                        print(f"[{current_time.strftime('%Y-%m-%d %H:%M')}] TAKE PROFIT @ ${current_trade.take_profit_1:,.2f} | PnL: ${current_trade.pnl:+,.2f} ({current_trade.pnl_pct:+.2f}%)")
                        current_trade = None
                        position_value = 0.0
                        portfolio_value = cash
                        portfolio_data.append({
                            'timestamp': current_time,
                            'price': current_price,
                            'cash': cash,
                            'position_value': position_value,
                            'portfolio_value': portfolio_value,
                            'in_position': False
                        })
                        continue

            # Record portfolio state
            portfolio_data.append({
                'timestamp': current_time,
                'price': current_price,
                'cash': cash,
                'position_value': position_value,
                'portfolio_value': portfolio_value,
                'in_position': current_trade is not None
            })

            # Look for entry signal if not in position
            if not current_trade:
                signal = self.strategy.generate_signal(df_slice)

                if signal['action'] == 'BUY':
                    quantity = cash / current_price
                    current_trade = Trade(
                        entry_time=str(current_time),
                        entry_price=current_price,
                        quantity=quantity,
                        side='LONG',
                        stop_loss=signal.get('stop_loss'),
                        take_profit_1=signal.get('take_profit_1'),
                        take_profit_2=signal.get('take_profit_2'),
                        confirmations=signal.get('confirmations', [])
                    )
                    print(f"[{current_time.strftime('%Y-%m-%d %H:%M')}] BUY @ ${current_price:,.2f} | Qty: {quantity:.4f} | SL: ${current_trade.stop_loss:,.2f} | TP: ${current_trade.take_profit_1:,.2f}")
                    cash = 0

                elif signal['action'] == 'SELL':
                    quantity = cash / current_price
                    current_trade = Trade(
                        entry_time=str(current_time),
                        entry_price=current_price,
                        quantity=quantity,
                        side='SHORT',
                        stop_loss=signal.get('stop_loss'),
                        take_profit_1=signal.get('take_profit_1'),
                        take_profit_2=signal.get('take_profit_2'),
                        confirmations=signal.get('confirmations', [])
                    )
                    print(f"[{current_time.strftime('%Y-%m-%d %H:%M')}] SELL @ ${current_price:,.2f} | Qty: {quantity:.4f} | SL: ${current_trade.stop_loss:,.2f} | TP: ${current_trade.take_profit_1:,.2f}")
                    cash = 0

        # Close any remaining open trade
        if current_trade:
            final_time = df.index[-1]
            final_price = df.iloc[-1]['close']
            current_trade.close(str(final_time), final_price, 'end_of_period')
            cash += self.initial_balance + current_trade.pnl
            trades.append(current_trade)
            print(f"[{final_time.strftime('%Y-%m-%d %H:%M')}] CLOSE (End) @ ${final_price:,.2f} | PnL: ${current_trade.pnl:+,.2f} ({current_trade.pnl_pct:+.2f}%)")

        # Final portfolio state
        portfolio_df = pd.DataFrame(portfolio_data)
        portfolio_df.set_index('timestamp', inplace=True)

        print(f"\nSimulation complete: {len(trades)} trades executed")

        return trades, portfolio_df

    def calculate_metrics(
        self,
        trades: List[Trade],
        portfolio_df: pd.DataFrame,
        symbol: str,
        timeframe: str
    ) -> BacktestMetrics:
        """Calculate comprehensive performance metrics."""

        if portfolio_df.empty:
            raise ValueError("Portfolio dataframe is empty")

        final_balance = portfolio_df['portfolio_value'].iloc[-1]
        total_return_usd = final_balance - self.initial_balance
        total_return_pct = (total_return_usd / self.initial_balance) * 100

        # Annualized return
        days = (portfolio_df.index[-1] - portfolio_df.index[0]).days
        years = days / 365.25
        annualized_return_pct = ((final_balance / self.initial_balance) ** (1 / years) - 1) * 100 if years > 0 else 0

        # Trade statistics
        winning_trades = [t for t in trades if t.pnl and t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl and t.pnl < 0]

        win_rate = (len(winning_trades) / len(trades) * 100) if trades else 0
        avg_win = np.mean([t.pnl_pct for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t.pnl_pct for t in losing_trades]) if losing_trades else 0

        # Profit factor
        total_profit = sum(t.pnl for t in winning_trades) if winning_trades else 0
        total_loss = abs(sum(t.pnl for t in losing_trades)) if losing_trades else 0
        profit_factor = (total_profit / total_loss) if total_loss > 0 else float('inf')

        # Best/worst trades
        best_trade = max([t.pnl_pct for t in trades]) if trades else 0
        worst_trade = min([t.pnl_pct for t in trades]) if trades else 0

        # Average trade duration
        avg_duration = np.mean([t.duration_hours for t in trades if t.duration_hours]) if trades else 0

        # Win/Loss streaks
        streaks = {'win': [], 'loss': []}
        current_streak = 0
        current_type = None

        for trade in trades:
            is_win = trade.pnl and trade.pnl > 0
            if is_win:
                if current_type == 'win':
                    current_streak += 1
                else:
                    if current_type is not None:
                        streaks['loss'].append(current_streak)
                    current_streak = 1
                    current_type = 'win'
            else:
                if current_type == 'loss':
                    current_streak += 1
                else:
                    if current_type is not None:
                        streaks['win'].append(current_streak)
                    current_streak = 1
                    current_type = 'loss'

        # Add final streak
        if current_type:
            streaks[current_type].append(current_streak)

        longest_win_streak = max(streaks['win']) if streaks['win'] else 0
        longest_loss_streak = max(streaks['loss']) if streaks['loss'] else 0

        # Time in market
        time_in_market = portfolio_df['in_position'].sum() / len(portfolio_df) * 100

        # Sharpe Ratio
        returns = portfolio_df['portfolio_value'].pct_change().dropna()
        if len(returns) > 0 and returns.std() > 0:
            # Assuming 4h timeframe: 6 periods per day, 252 trading days
            periods_per_year = 6 * 252 if timeframe == '4h' else 252
            sharpe = (returns.mean() / returns.std()) * np.sqrt(periods_per_year)
        else:
            sharpe = 0

        # Max Drawdown
        peak = portfolio_df['portfolio_value'].expanding(min_periods=1).max()
        drawdown = (portfolio_df['portfolio_value'] - peak) / peak * 100
        max_drawdown_pct = drawdown.min()
        max_drawdown_usd = (peak.max() - portfolio_df['portfolio_value'].min())

        return BacktestMetrics(
            strategy_name='Fibonacci Golden Zone',
            symbol=symbol,
            timeframe=timeframe,
            start_date=str(portfolio_df.index[0].date()),
            end_date=str(portfolio_df.index[-1].date()),
            initial_balance=self.initial_balance,
            final_balance=final_balance,
            total_return_pct=total_return_pct,
            total_return_usd=total_return_usd,
            annualized_return_pct=annualized_return_pct,
            sharpe_ratio=sharpe,
            max_drawdown_pct=max_drawdown_pct,
            max_drawdown_usd=max_drawdown_usd,
            win_rate_pct=win_rate,
            total_trades=len(trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            average_win_pct=avg_win,
            average_loss_pct=avg_loss,
            profit_factor=profit_factor,
            best_trade_pct=best_trade,
            worst_trade_pct=worst_trade,
            avg_trade_duration_hours=avg_duration,
            longest_win_streak=longest_win_streak,
            longest_loss_streak=longest_loss_streak,
            time_in_market_pct=time_in_market
        )

    def calculate_buy_hold(self, df: pd.DataFrame, start_idx: int = 200) -> Dict:
        """Calculate Buy & Hold baseline."""
        entry_price = df.iloc[start_idx]['close']
        exit_price = df.iloc[-1]['close']

        quantity = self.initial_balance / entry_price
        final_value = quantity * exit_price

        total_return_usd = final_value - self.initial_balance
        total_return_pct = (total_return_usd / self.initial_balance) * 100

        # Annualized return
        days = (df.index[-1] - df.index[start_idx]).days
        years = days / 365.25
        annualized_return_pct = ((final_value / self.initial_balance) ** (1 / years) - 1) * 100 if years > 0 else 0

        # Max drawdown for buy & hold
        bh_values = df['close'].iloc[start_idx:] * quantity
        peak = bh_values.expanding(min_periods=1).max()
        drawdown = (bh_values - peak) / peak * 100
        max_drawdown_pct = drawdown.min()

        return {
            'strategy_name': 'Buy & Hold',
            'initial_balance': self.initial_balance,
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

    def analyze_by_period(self, trades: List[Trade], portfolio_df: pd.DataFrame) -> pd.DataFrame:
        """Analyze performance by quarter."""
        periods = []

        # Group by quarter
        portfolio_df['quarter'] = portfolio_df.index.to_period('Q')

        for quarter, group in portfolio_df.groupby('quarter'):
            quarter_start = group.index[0]
            quarter_end = group.index[-1]
            start_value = group['portfolio_value'].iloc[0]
            end_value = group['portfolio_value'].iloc[-1]

            # Trades in this quarter
            quarter_trades = [
                t for t in trades
                if quarter_start <= pd.to_datetime(t.entry_time) <= quarter_end
            ]

            quarter_return = ((end_value - start_value) / start_value * 100) if start_value > 0 else 0

            periods.append({
                'period': str(quarter),
                'start_date': quarter_start.strftime('%Y-%m-%d'),
                'end_date': quarter_end.strftime('%Y-%m-%d'),
                'start_value': start_value,
                'end_value': end_value,
                'return_pct': quarter_return,
                'num_trades': len(quarter_trades),
                'winning_trades': len([t for t in quarter_trades if t.pnl and t.pnl > 0])
            })

        return pd.DataFrame(periods)

    def create_comprehensive_chart(
        self,
        portfolio_df: pd.DataFrame,
        buy_hold_dict: Dict,
        trades: List[Trade],
        df: pd.DataFrame,
        output_path: str
    ):
        """Create comprehensive visualization."""
        fig = plt.figure(figsize=(20, 14))
        gs = gridspec.GridSpec(4, 2, figure=fig, hspace=0.3, wspace=0.25)

        # 1. Price Chart with Entry/Exit points
        ax1 = fig.add_subplot(gs[0, :])
        ax1.plot(df.index, df['close'], label='BNB Price', color='blue', linewidth=1, alpha=0.7)

        # Mark trades
        for trade in trades:
            entry_time = pd.to_datetime(trade.entry_time)
            entry_idx = df.index.get_indexer([entry_time], method='nearest')[0]

            if trade.exit_time:
                exit_time = pd.to_datetime(trade.exit_time)
                exit_idx = df.index.get_indexer([exit_time], method='nearest')[0]

                color = 'green' if trade.pnl and trade.pnl > 0 else 'red'
                marker_buy = '^' if trade.side == 'LONG' else 'v'
                marker_sell = 'v' if trade.side == 'LONG' else '^'

                ax1.scatter(df.index[entry_idx], df.iloc[entry_idx]['close'],
                           marker=marker_buy, color=color, s=100, alpha=0.7, zorder=5)
                ax1.scatter(df.index[exit_idx], df.iloc[exit_idx]['close'],
                           marker=marker_sell, color=color, s=100, alpha=0.7, zorder=5)

        ax1.set_ylabel('Price (USD)', fontsize=12, fontweight='bold')
        ax1.set_title('BNB/USDT Price with Trade Signals', fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.legend()

        # 2. Portfolio Value Comparison
        ax2 = fig.add_subplot(gs[1, :])
        ax2.plot(portfolio_df.index, portfolio_df['portfolio_value'],
                label='Fibonacci Strategy', color='green', linewidth=2)

        # Buy & Hold
        start_idx = 200
        bh_quantity = buy_hold_dict['quantity']
        bh_values = df['close'].iloc[start_idx:] * bh_quantity
        ax2.plot(bh_values.index, bh_values,
                label='Buy & Hold', color='orange', linewidth=2, linestyle='--')

        ax2.axhline(self.initial_balance, color='gray', linestyle=':', linewidth=1, alpha=0.7, label='Initial Balance')
        ax2.set_ylabel('Portfolio Value (USD)', fontsize=12, fontweight='bold')
        ax2.set_title('Strategy Performance Comparison', fontsize=14, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        ax2.legend()

        # 3. Drawdown Chart
        ax3 = fig.add_subplot(gs[2, 0])
        peak = portfolio_df['portfolio_value'].expanding(min_periods=1).max()
        drawdown = (portfolio_df['portfolio_value'] - peak) / peak * 100
        ax3.fill_between(portfolio_df.index, 0, drawdown, color='red', alpha=0.3)
        ax3.plot(portfolio_df.index, drawdown, color='red', linewidth=1)
        ax3.set_ylabel('Drawdown (%)', fontsize=11, fontweight='bold')
        ax3.set_title('Drawdown Over Time', fontsize=12, fontweight='bold')
        ax3.grid(True, alpha=0.3)

        # 4. Trade Distribution
        ax4 = fig.add_subplot(gs[2, 1])
        if trades:
            trade_pnls = [t.pnl_pct for t in trades if t.pnl_pct is not None]
            wins = [p for p in trade_pnls if p > 0]
            losses = [p for p in trade_pnls if p <= 0]

            ax4.hist([wins, losses], bins=20, label=['Wins', 'Losses'],
                    color=['green', 'red'], alpha=0.7, edgecolor='black')
            ax4.axvline(0, color='black', linestyle='--', linewidth=1)
            ax4.set_xlabel('PnL (%)', fontsize=11, fontweight='bold')
            ax4.set_ylabel('Frequency', fontsize=11, fontweight='bold')
            ax4.set_title('Trade PnL Distribution', fontsize=12, fontweight='bold')
            ax4.legend()
            ax4.grid(True, alpha=0.3)

        # 5. Cumulative Returns
        ax5 = fig.add_subplot(gs[3, 0])
        cumulative_returns = (portfolio_df['portfolio_value'] / self.initial_balance - 1) * 100
        ax5.plot(portfolio_df.index, cumulative_returns, color='purple', linewidth=2)
        ax5.fill_between(portfolio_df.index, 0, cumulative_returns, alpha=0.3, color='purple')
        ax5.axhline(0, color='black', linestyle='--', linewidth=1)
        ax5.set_ylabel('Cumulative Return (%)', fontsize=11, fontweight='bold')
        ax5.set_title('Cumulative Returns', fontsize=12, fontweight='bold')
        ax5.grid(True, alpha=0.3)

        # 6. Monthly Returns Heatmap (simplified bar chart)
        ax6 = fig.add_subplot(gs[3, 1])
        if not portfolio_df.empty:
            monthly_data = portfolio_df.resample('M').last()
            monthly_returns = monthly_data['portfolio_value'].pct_change() * 100
            monthly_returns = monthly_returns.dropna()

            colors = ['green' if r > 0 else 'red' for r in monthly_returns]
            months = [d.strftime('%Y-%m') for d in monthly_returns.index]

            ax6.bar(range(len(monthly_returns)), monthly_returns, color=colors, alpha=0.7, edgecolor='black')
            ax6.axhline(0, color='black', linestyle='--', linewidth=1)
            ax6.set_xticks(range(len(monthly_returns)))
            ax6.set_xticklabels(months, rotation=45, ha='right', fontsize=8)
            ax6.set_ylabel('Return (%)', fontsize=11, fontweight='bold')
            ax6.set_title('Monthly Returns', fontsize=12, fontweight='bold')
            ax6.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"\nComprehensive chart saved: {output_path}")
        plt.close()


def print_executive_summary(metrics: BacktestMetrics, buy_hold: Dict, trades: List[Trade]):
    """Print executive summary."""
    print("\n" + "="*80)
    print(" EXECUTIVE SUMMARY")
    print("="*80)

    outperformance = metrics.total_return_pct - buy_hold['total_return_pct']
    winner = "FIBONACCI WINS" if outperformance > 0 else "BUY & HOLD WINS"

    print(f"\n Winner: {winner}")
    print(f" Outperformance: {outperformance:+.2f}%")
    print(f"\n Period: {metrics.start_date} to {metrics.end_date}")
    print(f" Initial Capital: ${metrics.initial_balance:,.2f}")

    print(f"\n {'Metric':<30} {'Fibonacci':<20} {'Buy & Hold':<20}")
    print(" " + "-"*70)
    print(f" {'Final Balance':<30} ${metrics.final_balance:>18,.2f} ${buy_hold['final_balance']:>18,.2f}")
    print(f" {'Total Return':<30} {metrics.total_return_pct:>17.2f}% {buy_hold['total_return_pct']:>17.2f}%")
    print(f" {'Annualized Return':<30} {metrics.annualized_return_pct:>17.2f}% {buy_hold['annualized_return_pct']:>17.2f}%")
    print(f" {'Max Drawdown':<30} {metrics.max_drawdown_pct:>17.2f}% {buy_hold['max_drawdown_pct']:>17.2f}%")
    print(f" {'Sharpe Ratio':<30} {metrics.sharpe_ratio:>19.2f} {'N/A':>20}")
    print(f" {'Win Rate':<30} {metrics.win_rate_pct:>17.2f}% {'N/A':>20}")
    print(f" {'Profit Factor':<30} {metrics.profit_factor:>19.2f} {'N/A':>20}")
    print(f" {'Total Trades':<30} {metrics.total_trades:>19} {'1':>20}")

    print("\n" + "="*80)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Comprehensive Fibonacci Golden Zone backtest"
    )
    parser.add_argument("--symbol", type=str, default="BNB_USDT", help="Trading pair")
    parser.add_argument("--timeframe", type=str, default="4h", help="Candle timeframe")
    parser.add_argument("--start", type=str, default="2023-11-01", help="Start date")
    parser.add_argument("--balance", type=float, default=5000, help="Initial balance")
    parser.add_argument("--output", type=str, default=None, help="Output directory")

    args = parser.parse_args()

    # Setup output
    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = project_root / 'data' / 'backtests'

    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = output_dir / f'fibonacci_comprehensive_{args.symbol}_{timestamp}.json'
    chart_path = output_dir / f'fibonacci_comprehensive_{args.symbol}_{timestamp}.png'
    trades_path = output_dir / f'fibonacci_trades_{args.symbol}_{timestamp}.csv'
    periods_path = output_dir / f'fibonacci_periods_{args.symbol}_{timestamp}.csv'

    print("\n" + "="*80)
    print(f" FIBONACCI GOLDEN ZONE - COMPREHENSIVE BACKTEST")
    print("="*80)
    print(f"\n Symbol: {args.symbol}")
    print(f" Timeframe: {args.timeframe}")
    print(f" Start Date: {args.start}")
    print(f" Initial Balance: ${args.balance:,.2f}")
    print(f"\n Output Directory: {output_dir}")

    try:
        # Initialize
        backtester = FibonacciBacktester(initial_balance=args.balance)

        # Fetch data
        df = backtester.fetch_historical_data(args.symbol, args.timeframe, args.start)

        # Simulate
        trades, portfolio_df = backtester.simulate_trades(df)

        # Calculate metrics
        print("\nCalculating metrics...")
        metrics = backtester.calculate_metrics(trades, portfolio_df, args.symbol, args.timeframe)
        buy_hold = backtester.calculate_buy_hold(df)

        # Period analysis
        print("Analyzing by period...")
        periods_df = backtester.analyze_by_period(trades, portfolio_df)

        # Print results
        print_executive_summary(metrics, buy_hold, trades)

        print("\n" + "="*80)
        print(" DETAILED METRICS - FIBONACCI STRATEGY")
        print("="*80)
        print(f"\n Trades: {metrics.total_trades} ({metrics.winning_trades}W / {metrics.losing_trades}L)")
        print(f" Win Rate: {metrics.win_rate_pct:.2f}%")
        print(f" Profit Factor: {metrics.profit_factor:.2f}")
        print(f" Average Win: {metrics.average_win_pct:+.2f}%")
        print(f" Average Loss: {metrics.average_loss_pct:.2f}%")
        print(f" Best Trade: {metrics.best_trade_pct:+.2f}%")
        print(f" Worst Trade: {metrics.worst_trade_pct:.2f}%")
        print(f" Longest Win Streak: {metrics.longest_win_streak}")
        print(f" Longest Loss Streak: {metrics.longest_loss_streak}")
        print(f" Avg Trade Duration: {metrics.avg_trade_duration_hours:.1f} hours")
        print(f" Time in Market: {metrics.time_in_market_pct:.1f}%")

        print("\n" + "="*80)
        print(" QUARTERLY PERFORMANCE")
        print("="*80)
        print(periods_df.to_string(index=False))

        # Save results
        print("\n" + "="*80)
        print(" SAVING RESULTS")
        print("="*80)

        report = {
            'fibonacci_strategy': asdict(metrics),
            'buy_hold_baseline': buy_hold,
            'outperformance_pct': metrics.total_return_pct - buy_hold['total_return_pct'],
            'quarterly_performance': periods_df.to_dict('records'),
            'trades': [asdict(t) for t in trades],
            'parameters': {
                'symbol': args.symbol,
                'timeframe': args.timeframe,
                'start_date': args.start,
                'initial_balance': args.balance
            }
        }

        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f" Report: {report_path}")

        # Save trades
        if trades:
            trades_df = pd.DataFrame([asdict(t) for t in trades])
            trades_df.to_csv(trades_path, index=False)
            print(f" Trades: {trades_path}")

        # Save periods
        periods_df.to_csv(periods_path, index=False)
        print(f" Periods: {periods_path}")

        # Create chart
        print("\nGenerating comprehensive chart...")
        backtester.create_comprehensive_chart(portfolio_df, buy_hold, trades, df, str(chart_path))

        print("\n" + "="*80)
        print(" BACKTEST COMPLETE!")
        print("="*80 + "\n")

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
