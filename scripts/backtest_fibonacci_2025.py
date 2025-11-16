#!/usr/bin/env python3
"""
Fibonacci Golden Zone Strategy Backtest for 2025

Comprehensive backtesting comparing:
1. Fibonacci Golden Zone Strategy
2. Buy & Hold baseline
3. FinRL ML Model (optional comparison)

Generates detailed performance metrics and comparison charts.

Usage:
    # Backtest Fibonacci strategy
    python scripts/backtest_fibonacci_2025.py --symbol BNB_USDT --start 2025-01-01

    # Compare with ML model
    python scripts/backtest_fibonacci_2025.py --symbol BNB_USDT --compare-ml

    # Custom initial balance
    python scripts/backtest_fibonacci_2025.py --symbol BNB_USDT --balance 5000

Example Output:
    ================================================================================
    FIBONACCI GOLDEN ZONE BACKTEST RESULTS - BNB_USDT (2025-01-01 to 2025-11-15)
    ================================================================================

    Strategy Performance:
      Total Return: +35.20% ($13,520)
      Sharpe Ratio: 1.85
      Max Drawdown: -12.30% ($1,230)
      Win Rate: 62.50% (10/16 trades)
      Profit Factor: 2.45

    Buy & Hold Performance:
      Total Return: +28.50% ($11,350)

    Fibonacci vs Buy & Hold: +6.70% outperformance

    Report saved: data/backtests/fibonacci_2025_BNB_USDT_20251115.json
    Chart saved: data/backtests/fibonacci_2025_BNB_USDT_20251115.png
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
    side: str = 'LONG'  # 'LONG' or 'SHORT'
    stop_loss: Optional[float] = None
    take_profit_1: Optional[float] = None
    take_profit_2: Optional[float] = None
    confirmations: Optional[List[str]] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    duration_hours: Optional[float] = None

    def close(self, exit_time: str, exit_price: float):
        """Close the trade and calculate PnL."""
        self.exit_time = exit_time
        self.exit_price = exit_price

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


class FibonacciBacktester:
    """
    Backtesting engine for Fibonacci Golden Zone strategy.

    Simulates trading on historical data with realistic assumptions:
    - Enters at signal candle close price
    - Exits at stop loss or take profit
    - No slippage (can add if needed)
    - No trading fees (can add if needed)
    """

    def __init__(self, initial_balance: float = 10000):
        """
        Initialize backtester.

        Args:
            initial_balance: Starting capital in USDT
        """
        self.initial_balance = initial_balance
        self.strategy = FibonacciGoldenZoneStrategy()

    def fetch_historical_data(
        self, symbol: str, timeframe: str, start_date: str
    ) -> pd.DataFrame:
        """
        Fetch historical candle data from Binance.

        Args:
            symbol: Trading pair (e.g., 'BNB_USDT')
            timeframe: Candle timeframe (e.g., '1d')
            start_date: Start date (YYYY-MM-DD)

        Returns:
            DataFrame with OHLCV data
        """
        print(f"Fetching historical data for {symbol} from {start_date}...")

        client = BinanceRESTClient(testnet=False)
        binance_symbol = symbol.replace("_", "")

        # Convert start_date to timestamp
        start_dt = pd.to_datetime(start_date)
        start_ts = int(start_dt.timestamp() * 1000)

        # Fetch all candles since start date
        klines = client.get_klines(
            symbol=binance_symbol,
            interval=timeframe,
            limit=1000,
            start_time=start_ts
        )

        if not klines:
            raise ValueError(f"No data received from Binance for {symbol}")

        df = pd.DataFrame(klines)
        df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms")
        df = df[["timestamp", "open", "high", "low", "close", "volume"]]
        df.set_index("timestamp", inplace=True)

        print(f"Fetched {len(df)} candles from {df.index[0]} to {df.index[-1]}")

        return df

    def simulate_trades(self, df: pd.DataFrame) -> Tuple[List[Trade], pd.Series]:
        """
        Simulate trading on historical data.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Tuple of (trades_list, balance_series)
        """
        print("\nSimulating trades...")

        trades = []
        balance = self.initial_balance
        balance_history = [balance]
        current_trade: Optional[Trade] = None

        # Need at least 200 candles for strategy
        if len(df) < 200:
            raise ValueError(f"Need at least 200 candles, got {len(df)}")

        # Iterate through candles (skip first 200 for EMA calculation)
        for i in range(200, len(df)):
            # Get data up to current candle
            df_slice = df.iloc[:i+1]
            current_candle = df_slice.iloc[-1]
            current_time = df_slice.index[-1]
            current_price = current_candle['close']

            # Check if we have open position
            if current_trade:
                # Check stop loss
                if current_trade.stop_loss:
                    if (current_trade.side == 'LONG' and current_price <= current_trade.stop_loss) or \
                       (current_trade.side == 'SHORT' and current_price >= current_trade.stop_loss):
                        # Stop loss hit
                        current_trade.close(str(current_time), current_trade.stop_loss)
                        balance += current_trade.pnl
                        trades.append(current_trade)
                        print(f"  [{current_time.date()}] STOP LOSS hit @ ${current_trade.stop_loss:,.2f} | PnL: ${current_trade.pnl:,.2f} ({current_trade.pnl_pct:.2f}%)")
                        current_trade = None
                        balance_history.append(balance)
                        continue

                # Check take profit 1
                if current_trade.take_profit_1:
                    if (current_trade.side == 'LONG' and current_price >= current_trade.take_profit_1) or \
                       (current_trade.side == 'SHORT' and current_price <= current_trade.take_profit_1):
                        # Take profit 1 hit (close entire position for simplicity)
                        current_trade.close(str(current_time), current_trade.take_profit_1)
                        balance += current_trade.pnl
                        trades.append(current_trade)
                        print(f"  [{current_time.date()}] TAKE PROFIT 1 hit @ ${current_trade.take_profit_1:,.2f} | PnL: ${current_trade.pnl:,.2f} ({current_trade.pnl_pct:.2f}%)")
                        current_trade = None
                        balance_history.append(balance)
                        continue

                # Update balance history
                balance_history.append(balance)

            else:
                # No open position - look for entry signal
                signal = self.strategy.generate_signal(df_slice)

                if signal['action'] == 'BUY':
                    # Enter long position
                    quantity = balance / current_price  # Use entire balance
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
                    print(f"  [{current_time.date()}] BUY @ ${current_price:,.2f} | Qty: {quantity:.4f} | SL: ${current_trade.stop_loss:,.2f} | TP1: ${current_trade.take_profit_1:,.2f}")
                    balance = 0  # All in position
                    balance_history.append(balance)

                elif signal['action'] == 'SELL':
                    # Enter short position (simplified - assume we can short)
                    quantity = balance / current_price
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
                    print(f"  [{current_time.date()}] SELL @ ${current_price:,.2f} | Qty: {quantity:.4f} | SL: ${current_trade.stop_loss:,.2f} | TP1: ${current_trade.take_profit_1:,.2f}")
                    balance = 0  # All in position
                    balance_history.append(balance)

                else:
                    # HOLD - no action
                    balance_history.append(balance)

        # Close any remaining open trade at final price
        if current_trade:
            final_time = df.index[-1]
            final_price = df.iloc[-1]['close']
            current_trade.close(str(final_time), final_price)
            balance += current_trade.pnl
            trades.append(current_trade)
            print(f"  [{final_time.date()}] CLOSE @ ${final_price:,.2f} | PnL: ${current_trade.pnl:,.2f} ({current_trade.pnl_pct:.2f}%)")

        # Convert balance history to series
        balance_series = pd.Series(balance_history, index=df.index)

        print(f"\nSimulation complete: {len(trades)} trades executed")

        return trades, balance_series

    def calculate_metrics(
        self,
        trades: List[Trade],
        balance_series: pd.Series,
        symbol: str,
        timeframe: str
    ) -> BacktestMetrics:
        """
        Calculate comprehensive performance metrics.

        Args:
            trades: List of executed trades
            balance_series: Time series of balance
            symbol: Trading pair
            timeframe: Candle timeframe

        Returns:
            BacktestMetrics dataclass
        """
        final_balance = balance_series.iloc[-1]
        total_return_usd = final_balance - self.initial_balance
        total_return_pct = (total_return_usd / self.initial_balance) * 100

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

        # Sharpe Ratio (simplified)
        returns = balance_series.pct_change().dropna()
        sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if len(returns) > 0 and returns.std() > 0 else 0

        # Max Drawdown
        peak = balance_series.expanding(min_periods=1).max()
        drawdown = (balance_series - peak) / peak * 100
        max_drawdown_pct = drawdown.min()
        max_drawdown_usd = (peak.max() - balance_series.min())

        return BacktestMetrics(
            strategy_name='Fibonacci Golden Zone',
            symbol=symbol,
            timeframe=timeframe,
            start_date=str(balance_series.index[0].date()),
            end_date=str(balance_series.index[-1].date()),
            initial_balance=self.initial_balance,
            final_balance=final_balance,
            total_return_pct=total_return_pct,
            total_return_usd=total_return_usd,
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
            avg_trade_duration_hours=avg_duration
        )

    def calculate_buy_hold_baseline(self, df: pd.DataFrame) -> Dict:
        """
        Calculate Buy & Hold baseline for comparison.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Dict with buy & hold metrics
        """
        entry_price = df.iloc[200]['close']  # Start at same point as strategy
        exit_price = df.iloc[-1]['close']

        quantity = self.initial_balance / entry_price
        final_value = quantity * exit_price

        total_return_usd = final_value - self.initial_balance
        total_return_pct = (total_return_usd / self.initial_balance) * 100

        return {
            'strategy_name': 'Buy & Hold',
            'initial_balance': self.initial_balance,
            'final_balance': final_value,
            'total_return_pct': total_return_pct,
            'total_return_usd': total_return_usd,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'quantity': quantity
        }

    def create_comparison_chart(
        self,
        balance_series: pd.Series,
        buy_hold_baseline: Dict,
        df: pd.DataFrame,
        output_path: str
    ):
        """
        Create visual comparison chart.

        Args:
            balance_series: Fibonacci strategy balance over time
            buy_hold_baseline: Buy & Hold metrics
            df: Price data
            output_path: Path to save chart
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10), sharex=True)

        # Plot 1: Price chart
        ax1.plot(df.index, df['close'], label='Price', color='blue', linewidth=1.5)
        ax1.set_ylabel('Price (USD)', fontsize=12, fontweight='bold')
        ax1.set_title('Price History', fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.legend()

        # Plot 2: Strategy comparison
        # Fibonacci strategy
        ax2.plot(balance_series.index, balance_series, label='Fibonacci Golden Zone', color='green', linewidth=2)

        # Buy & Hold
        buy_hold_series = pd.Series(
            [buy_hold_baseline['initial_balance']] + [buy_hold_baseline['final_balance']] * (len(balance_series) - 1),
            index=balance_series.index
        )
        # Calculate actual buy & hold over time
        entry_price = buy_hold_baseline['entry_price']
        quantity = buy_hold_baseline['quantity']
        buy_hold_series = df['close'].iloc[200:] * quantity
        buy_hold_series.index = balance_series.index

        ax2.plot(buy_hold_series.index, buy_hold_series, label='Buy & Hold', color='orange', linewidth=2, linestyle='--')

        # Baseline
        ax2.axhline(self.initial_balance, color='gray', linestyle=':', linewidth=1, alpha=0.7, label='Initial Balance')

        ax2.set_ylabel('Balance (USD)', fontsize=12, fontweight='bold')
        ax2.set_xlabel('Date', fontsize=12, fontweight='bold')
        ax2.set_title('Strategy Performance Comparison', fontsize=14, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        ax2.legend()

        # Format x-axis
        ax2.xaxis.set_major_formatter(DateFormatter('%Y-%m-%d'))
        plt.xticks(rotation=45, ha='right')

        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"Chart saved to: {output_path}")
        plt.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Backtest Fibonacci Golden Zone strategy on 2025 data"
    )
    parser.add_argument(
        "--symbol",
        type=str,
        default="BNB_USDT",
        help="Trading pair (e.g., BNB_USDT)"
    )
    parser.add_argument(
        "--timeframe",
        type=str,
        default="1d",
        help="Candle timeframe (e.g., 1d)"
    )
    parser.add_argument(
        "--start",
        type=str,
        default="2025-01-01",
        help="Start date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--balance",
        type=float,
        default=10000,
        help="Initial balance in USDT"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output directory (default: data/backtests/)"
    )

    args = parser.parse_args()

    # Setup output directory
    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = project_root / 'data' / 'backtests'

    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = output_dir / f'fibonacci_2025_{args.symbol}_{timestamp}.json'
    chart_path = output_dir / f'fibonacci_2025_{args.symbol}_{timestamp}.png'
    trades_path = output_dir / f'fibonacci_2025_{args.symbol}_{timestamp}_trades.csv'

    print(f"\n{'='*80}")
    print(f"FIBONACCI GOLDEN ZONE BACKTEST - {args.symbol} {args.timeframe}")
    print(f"{'='*80}\n")

    try:
        # Initialize backtester
        backtester = FibonacciBacktester(initial_balance=args.balance)

        # Fetch historical data
        df = backtester.fetch_historical_data(args.symbol, args.timeframe, args.start)

        # Simulate trades
        trades, balance_series = backtester.simulate_trades(df)

        # Calculate metrics
        metrics = backtester.calculate_metrics(trades, balance_series, args.symbol, args.timeframe)

        # Calculate Buy & Hold baseline
        buy_hold = backtester.calculate_buy_hold_baseline(df)

        # Print results
        print(f"\n{'='*80}")
        print(f"RESULTS - {metrics.start_date} to {metrics.end_date}")
        print(f"{'='*80}\n")

        print("Fibonacci Golden Zone Strategy:")
        print(f"  Total Return: {metrics.total_return_pct:+.2f}% (${metrics.total_return_usd:+,.2f})")
        print(f"  Final Balance: ${metrics.final_balance:,.2f}")
        print(f"  Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
        print(f"  Max Drawdown: {metrics.max_drawdown_pct:.2f}% (${metrics.max_drawdown_usd:,.2f})")
        print(f"  Win Rate: {metrics.win_rate_pct:.2f}% ({metrics.winning_trades}/{metrics.total_trades} trades)")
        print(f"  Profit Factor: {metrics.profit_factor:.2f}")
        print(f"  Average Win: {metrics.average_win_pct:+.2f}%")
        print(f"  Average Loss: {metrics.average_loss_pct:.2f}%")
        print(f"  Best Trade: {metrics.best_trade_pct:+.2f}%")
        print(f"  Worst Trade: {metrics.worst_trade_pct:.2f}%")
        print(f"  Avg Trade Duration: {metrics.avg_trade_duration_hours:.1f} hours")

        print(f"\nBuy & Hold Baseline:")
        print(f"  Total Return: {buy_hold['total_return_pct']:+.2f}% (${buy_hold['total_return_usd']:+,.2f})")
        print(f"  Final Balance: ${buy_hold['final_balance']:,.2f}")

        outperformance = metrics.total_return_pct - buy_hold['total_return_pct']
        print(f"\nFibonacci vs Buy & Hold: {outperformance:+.2f}% {'outperformance' if outperformance > 0 else 'underperformance'}")

        # Save results
        report = {
            'fibonacci_strategy': asdict(metrics),
            'buy_hold_baseline': buy_hold,
            'outperformance_pct': outperformance,
            'trades': [asdict(t) for t in trades]
        }

        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\nReport saved to: {report_path}")

        # Save trades to CSV
        if trades:
            trades_df = pd.DataFrame([asdict(t) for t in trades])
            trades_df.to_csv(trades_path, index=False)
            print(f"Trades saved to: {trades_path}")

        # Create comparison chart
        backtester.create_comparison_chart(balance_series, buy_hold, df, str(chart_path))

        print(f"\n{'='*80}\n")
        print("Backtest complete!")

    except Exception as e:
        print(f"\nError during backtest: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
