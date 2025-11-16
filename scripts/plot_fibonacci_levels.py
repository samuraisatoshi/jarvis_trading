#!/usr/bin/env python3
"""
Fibonacci Levels Visualization Tool

Creates visual charts showing:
- Candlestick patterns
- Fibonacci retracement levels (23.6%, 38.2%, 50%, 61.8%, 78.6%)
- Golden Zone highlighted (50%-61.8%)
- Swing points marked
- Entry/exit signals
- EMAs for trend identification

Usage:
    # Visualize current market
    python scripts/plot_fibonacci_levels.py --symbol BNB_USDT --timeframe 1d

    # Save to specific path
    python scripts/plot_fibonacci_levels.py --symbol BNB_USDT --output my_chart.png

    # Show last N candles
    python scripts/plot_fibonacci_levels.py --symbol BNB_USDT --candles 100

Example:
    $ python scripts/plot_fibonacci_levels.py --symbol BNB_USDT --timeframe 1d
    Fetching 300 candles for BNBUSDT 1d...
    Running Fibonacci analysis...
    UPTREND detected
    Golden Zone: $615.20 - $622.50
    Signal: BUY (3 confirmations)
    Chart saved to: data/fibonacci_analysis_BNB_USDT_20251115_120530.png
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.dates import DateFormatter
import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.exchange.binance_rest_client import BinanceRESTClient

sys.path.insert(0, str(project_root / 'scripts'))
from fibonacci_golden_zone_strategy import FibonacciGoldenZoneStrategy


class FibonacciChartPlotter:
    """
    Creates visual charts for Fibonacci Golden Zone analysis.

    Features:
    - Candlestick charts
    - Fibonacci levels as horizontal lines
    - Golden Zone shaded area
    - Swing points marked
    - EMAs plotted
    - Signal annotations
    """

    def __init__(self):
        """Initialize plotter with default styling."""
        self.strategy = FibonacciGoldenZoneStrategy()
        plt.style.use('seaborn-v0_8-darkgrid')

    def fetch_data(self, symbol: str, timeframe: str, limit: int = 300) -> pd.DataFrame:
        """
        Fetch candle data from Binance.

        Args:
            symbol: Trading pair (e.g., 'BNB_USDT')
            timeframe: Candle timeframe (e.g., '1d')
            limit: Number of candles to fetch

        Returns:
            DataFrame with OHLCV data
        """
        print(f"Fetching {limit} candles for {symbol.replace('_', '')} {timeframe}...")

        client = BinanceRESTClient(testnet=False)
        binance_symbol = symbol.replace("_", "")

        klines = client.get_klines(symbol=binance_symbol, interval=timeframe, limit=limit)

        if not klines:
            raise ValueError("No data received from Binance")

        df = pd.DataFrame(klines)
        df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms")
        df = df[["timestamp", "open", "high", "low", "close", "volume"]]
        df.set_index("timestamp", inplace=True)

        print(f"Fetched {len(df)} candles from {df.index[0]} to {df.index[-1]}")

        return df

    def plot_candlesticks(self, ax, df: pd.DataFrame, num_candles: int = 100):
        """
        Plot candlesticks on given axis.

        Args:
            ax: Matplotlib axis
            df: DataFrame with OHLCV data
            num_candles: Number of recent candles to plot
        """
        # Get last N candles
        df_plot = df.tail(num_candles).copy()

        # Create candles
        for idx, row in df_plot.iterrows():
            # Candle body
            open_price = row['open']
            close_price = row['close']
            high_price = row['high']
            low_price = row['low']

            color = 'green' if close_price >= open_price else 'red'
            body_height = abs(close_price - open_price)

            # Draw body
            body = patches.Rectangle(
                (idx, min(open_price, close_price)),
                width=pd.Timedelta(hours=12),  # Half day width
                height=body_height,
                facecolor=color,
                edgecolor='black',
                linewidth=0.5,
                alpha=0.8
            )
            ax.add_patch(body)

            # Draw wicks
            ax.plot([idx, idx], [low_price, high_price], color='black', linewidth=0.5)

        ax.set_xlim(df_plot.index[0], df_plot.index[-1])
        ax.set_ylabel('Price (USD)', fontsize=12, fontweight='bold')

    def plot_fibonacci_levels(self, ax, fib_levels: dict, trend: str):
        """
        Plot Fibonacci retracement levels as horizontal lines.

        Args:
            ax: Matplotlib axis
            fib_levels: Dict of Fibonacci levels from strategy
            trend: 'UPTREND' or 'DOWNTREND'
        """
        # Colors for each level
        level_colors = {
            '0.236': '#00BCD4',  # Cyan
            '0.382': '#4CAF50',  # Green
            '0.500': '#FFC107',  # Amber (Golden Zone start)
            '0.618': '#FF9800',  # Orange (Golden Zone end)
            '0.786': '#F44336',  # Red (Stop loss)
        }

        # Plot each level
        for level, price in fib_levels.items():
            if level in level_colors:
                ax.axhline(
                    y=price,
                    color=level_colors[level],
                    linestyle='--',
                    linewidth=2,
                    alpha=0.7,
                    label=f'Fib {level} (${price:,.2f})'
                )

        # Highlight Golden Zone (50%-61.8%)
        golden_min = fib_levels['0.618']
        golden_max = fib_levels['0.500']

        ax.fill_between(
            ax.get_xlim(),
            golden_min,
            golden_max,
            color='gold',
            alpha=0.2,
            label='Golden Zone'
        )

        # Mark high and low
        ax.axhline(
            y=fib_levels['high'],
            color='blue',
            linestyle='-',
            linewidth=2,
            alpha=0.5,
            label=f'Swing High (${fib_levels["high"]:,.2f})'
        )
        ax.axhline(
            y=fib_levels['low'],
            color='purple',
            linestyle='-',
            linewidth=2,
            alpha=0.5,
            label=f'Swing Low (${fib_levels["low"]:,.2f})'
        )

    def plot_emas(self, ax, df: pd.DataFrame, num_candles: int = 100):
        """
        Plot EMAs (20, 50, 200) for trend identification.

        Args:
            ax: Matplotlib axis
            df: DataFrame with close prices
            num_candles: Number of recent candles to plot
        """
        df_plot = df.tail(num_candles).copy()

        # Calculate EMAs
        ema20 = df['close'].ewm(span=20, adjust=False).mean()
        ema50 = df['close'].ewm(span=50, adjust=False).mean()
        ema200 = df['close'].ewm(span=200, adjust=False).mean()

        # Plot
        ax.plot(df_plot.index, ema20.tail(num_candles), label='EMA 20', color='blue', linewidth=2, alpha=0.7)
        ax.plot(df_plot.index, ema50.tail(num_candles), label='EMA 50', color='orange', linewidth=2, alpha=0.7)
        ax.plot(df_plot.index, ema200.tail(num_candles), label='EMA 200', color='red', linewidth=2, alpha=0.7)

    def plot_swing_points(self, ax, swing_highs: pd.DataFrame, swing_lows: pd.DataFrame, num_candles: int = 100):
        """
        Mark swing high and low points.

        Args:
            ax: Matplotlib axis
            swing_highs: DataFrame of swing highs
            swing_lows: DataFrame of swing lows
            num_candles: Number of recent candles being plotted
        """
        # Get time range
        xlim = ax.get_xlim()

        # Filter swing points within visible range
        for idx, row in swing_highs.iterrows():
            if xlim[0] <= idx.timestamp() <= xlim[1]:
                ax.plot(idx, row['high'], marker='v', color='red', markersize=10, label='Swing High' if idx == swing_highs.index[0] else '')

        for idx, row in swing_lows.iterrows():
            if xlim[0] <= idx.timestamp() <= xlim[1]:
                ax.plot(idx, row['low'], marker='^', color='green', markersize=10, label='Swing Low' if idx == swing_lows.index[0] else '')

    def plot_signal(self, ax, signal: dict, df: pd.DataFrame):
        """
        Annotate chart with trading signal.

        Args:
            ax: Matplotlib axis
            signal: Signal dict from strategy
            df: DataFrame with candles
        """
        action = signal['action']
        latest_timestamp = df.index[-1]
        current_price = signal['current_price']

        # Signal annotation
        if action == 'BUY':
            ax.annotate(
                f'BUY SIGNAL\n${current_price:,.2f}\n{signal["reason"][:40]}...',
                xy=(latest_timestamp, current_price),
                xytext=(20, 50),
                textcoords='offset points',
                fontsize=10,
                bbox=dict(boxstyle='round,pad=0.5', facecolor='green', alpha=0.7),
                arrowprops=dict(arrowstyle='->', color='green', lw=2),
                color='white',
                fontweight='bold'
            )

            # Mark stop loss and targets if available
            if 'stop_loss' in signal:
                ax.axhline(signal['stop_loss'], color='red', linestyle=':', linewidth=1, alpha=0.5)
                ax.text(latest_timestamp, signal['stop_loss'], f'  SL: ${signal["stop_loss"]:,.2f}', fontsize=8, color='red')

            if 'take_profit_1' in signal:
                ax.axhline(signal['take_profit_1'], color='green', linestyle=':', linewidth=1, alpha=0.5)
                ax.text(latest_timestamp, signal['take_profit_1'], f'  TP1: ${signal["take_profit_1"]:,.2f}', fontsize=8, color='green')

            if 'take_profit_2' in signal:
                ax.axhline(signal['take_profit_2'], color='darkgreen', linestyle=':', linewidth=1, alpha=0.5)
                ax.text(latest_timestamp, signal['take_profit_2'], f'  TP2: ${signal["take_profit_2"]:,.2f}', fontsize=8, color='darkgreen')

        elif action == 'SELL':
            ax.annotate(
                f'SELL SIGNAL\n${current_price:,.2f}\n{signal["reason"][:40]}...',
                xy=(latest_timestamp, current_price),
                xytext=(20, -50),
                textcoords='offset points',
                fontsize=10,
                bbox=dict(boxstyle='round,pad=0.5', facecolor='red', alpha=0.7),
                arrowprops=dict(arrowstyle='->', color='red', lw=2),
                color='white',
                fontweight='bold'
            )

        elif action == 'HOLD':
            ax.annotate(
                f'HOLD\n${current_price:,.2f}\n{signal["reason"][:40]}...',
                xy=(latest_timestamp, current_price),
                xytext=(20, 0),
                textcoords='offset points',
                fontsize=10,
                bbox=dict(boxstyle='round,pad=0.5', facecolor='gray', alpha=0.7),
                arrowprops=dict(arrowstyle='->', color='gray', lw=2),
                color='white',
                fontweight='bold'
            )

    def create_chart(
        self,
        symbol: str,
        timeframe: str,
        num_candles: int = 100,
        output_path: str = None
    ) -> str:
        """
        Create complete Fibonacci analysis chart.

        Args:
            symbol: Trading pair (e.g., 'BNB_USDT')
            timeframe: Candle timeframe (e.g., '1d')
            num_candles: Number of recent candles to plot
            output_path: Path to save chart (auto-generated if None)

        Returns:
            Path to saved chart file
        """
        # Fetch data
        df = self.fetch_data(symbol, timeframe, limit=300)

        # Run Fibonacci analysis
        print("Running Fibonacci analysis...")
        signal = self.strategy.generate_signal(df)

        print(f"\nAnalysis Results:")
        print(f"  Trend: {signal['trend']}")
        print(f"  Action: {signal['action']}")
        print(f"  Reason: {signal['reason']}")
        if 'confirmations' in signal:
            print(f"  Confirmations: {', '.join(signal['confirmations'])}")

        # Create figure
        fig, ax = plt.subplots(figsize=(16, 10))

        # Plot candlesticks
        self.plot_candlesticks(ax, df, num_candles)

        # Plot EMAs
        self.plot_emas(ax, df, num_candles)

        # Plot Fibonacci levels if available
        if 'fib_levels' in signal:
            self.plot_fibonacci_levels(ax, signal['fib_levels'], signal['trend'])

            # Find and plot swing points
            swing_highs, swing_lows = self.strategy.find_swing_points(df)
            self.plot_swing_points(ax, swing_highs, swing_lows, num_candles)

        # Plot signal
        self.plot_signal(ax, signal, df)

        # Formatting
        ax.set_title(
            f'Fibonacci Golden Zone Analysis - {symbol} {timeframe}\n'
            f'{signal["trend"]} | {signal["action"]} Signal',
            fontsize=16,
            fontweight='bold'
        )
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper left', fontsize=10, framealpha=0.9)

        # Format x-axis dates
        ax.xaxis.set_major_formatter(DateFormatter('%Y-%m-%d'))
        plt.xticks(rotation=45, ha='right')

        plt.tight_layout()

        # Save chart
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = str(project_root / 'data' / f'fibonacci_analysis_{symbol}_{timestamp}.png')

        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"\nChart saved to: {output_path}")

        plt.close()

        return output_path


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Visualize Fibonacci Golden Zone analysis")
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
        help="Candle timeframe (e.g., 1d, 4h, 1h)"
    )
    parser.add_argument(
        "--candles",
        type=int,
        default=100,
        help="Number of recent candles to plot"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file path (auto-generated if not specified)"
    )

    args = parser.parse_args()

    # Create plotter
    plotter = FibonacciChartPlotter()

    # Create chart
    try:
        output_path = plotter.create_chart(
            symbol=args.symbol,
            timeframe=args.timeframe,
            num_candles=args.candles,
            output_path=args.output
        )
        print(f"\n✅ Success! Chart saved to: {output_path}")

    except Exception as e:
        print(f"\n❌ Error creating chart: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
