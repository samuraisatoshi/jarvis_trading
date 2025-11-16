"""
Chart generator for candlestick charts with trading signals.

Creates professional trading charts with:
- Candlestick patterns
- Moving averages
- Buy/sell signals from executed orders
- Support/resistance levels
"""

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import tempfile

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import FancyArrowPatch
import mplfinance as mpf
import pandas as pd
import numpy as np
from loguru import logger
import ccxt


class ChartGenerator:
    """Generate trading charts with candlesticks and indicators."""

    def __init__(self, db_path: str = "data/jarvis_trading.db"):
        """Initialize chart generator."""
        self.db_path = db_path
        self.exchange = ccxt.binance()

        # Chart style configuration
        self.chart_style = mpf.make_mpf_style(
            base_mpf_style='charles',
            marketcolors=mpf.make_marketcolors(
                up='#26a69a',
                down='#ef5350',
                edge='inherit',
                wick={'up': '#26a69a', 'down': '#ef5350'},
                volume='in'
            ),
            gridcolor='#2c2e3e',
            gridstyle='--',
            facecolor='#1e1f29'
        )

    def fetch_candles(self, symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
        """Fetch OHLCV data from Binance."""
        try:
            # Convert timeframe to ccxt format
            tf_map = {'1h': '1h', '4h': '4h', '1d': '1d'}
            tf = tf_map.get(timeframe, '1h')

            # Fetch OHLCV data
            ohlcv = self.exchange.fetch_ohlcv(symbol, tf, limit=limit + 200)  # Extra for MA calculation

            # Convert to DataFrame
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )

            # Convert timestamp to datetime with UTC timezone
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
            df.set_index('timestamp', inplace=True)

            # Calculate moving averages based on timeframe
            if timeframe == '1h':
                df['MA50'] = df['close'].rolling(window=50).mean()
                df['MA100'] = df['close'].rolling(window=100).mean()
                df['MA200'] = df['close'].rolling(window=200).mean()
                ma_periods = [50, 100, 200]
            elif timeframe == '4h':
                df['MA50'] = df['close'].rolling(window=50).mean()
                df['MA100'] = df['close'].rolling(window=100).mean()
                df['MA200'] = df['close'].rolling(window=200).mean()
                ma_periods = [50, 100, 200]
            else:  # 1d
                df['MA20'] = df['close'].rolling(window=20).mean()
                df['MA50'] = df['close'].rolling(window=50).mean()
                df['MA200'] = df['close'].rolling(window=200).mean()
                ma_periods = [20, 50, 200]

            # Return only the last 'limit' candles but with MAs calculated
            return df.tail(limit), ma_periods

        except Exception as e:
            logger.error(f"Error fetching candles: {e}")
            raise

    def get_executed_orders(self, symbol: str, hours: int = 120) -> List[Dict]:
        """Get executed orders from database for the symbol."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Calculate time window
            since = datetime.now(timezone.utc) - timedelta(hours=hours)

            # Fetch executed orders
            cursor.execute("""
                SELECT
                    created_at,
                    side,
                    price,
                    quantity,
                    id
                FROM orders
                WHERE symbol = ?
                    AND status = 'FILLED'
                    AND created_at > ?
                ORDER BY created_at
            """, (symbol, since.isoformat()))

            orders = []
            for row in cursor.fetchall():
                orders.append({
                    'timestamp': pd.to_datetime(row[0]),
                    'side': row[1],
                    'price': float(row[2]),
                    'quantity': float(row[3]),
                    'order_id': row[4]
                })

            conn.close()
            return orders

        except Exception as e:
            logger.error(f"Error fetching orders: {e}")
            return []

    def calculate_thresholds(self, df: pd.DataFrame, timeframe: str) -> Dict[str, List[float]]:
        """Calculate support and resistance levels based on MA strategy thresholds."""
        thresholds = {}
        current_price = df['close'].iloc[-1]

        if timeframe == '1h':
            # MA50: ±3.5% threshold
            if 'MA50' in df.columns and not pd.isna(df['MA50'].iloc[-1]):
                ma50 = df['MA50'].iloc[-1]
                thresholds['MA50'] = [
                    ma50 * 0.965,  # -3.5% support
                    ma50 * 1.035   # +3.5% resistance
                ]

            # MA100: ±5% threshold
            if 'MA100' in df.columns and not pd.isna(df['MA100'].iloc[-1]):
                ma100 = df['MA100'].iloc[-1]
                thresholds['MA100'] = [
                    ma100 * 0.95,  # -5% support
                    ma100 * 1.05   # +5% resistance
                ]

        elif timeframe == '4h':
            # MA50: ±3.5% threshold
            if 'MA50' in df.columns and not pd.isna(df['MA50'].iloc[-1]):
                ma50 = df['MA50'].iloc[-1]
                thresholds['MA50'] = [
                    ma50 * 0.965,  # -3.5% support
                    ma50 * 1.035   # +3.5% resistance
                ]

            # MA100: ±3.2% threshold for BNB, varies by asset
            if 'MA100' in df.columns and not pd.isna(df['MA100'].iloc[-1]):
                ma100 = df['MA100'].iloc[-1]
                thresholds['MA100'] = [
                    ma100 * 0.968,  # -3.2% support
                    ma100 * 1.032   # +3.2% resistance
                ]

        else:  # 1d
            # MA200: Asset-specific thresholds
            if 'MA200' in df.columns and not pd.isna(df['MA200'].iloc[-1]):
                ma200 = df['MA200'].iloc[-1]
                # These would vary by asset, using average values
                thresholds['MA200'] = [
                    ma200 * 0.92,  # -8% support (average)
                    ma200 * 1.08   # +8% resistance
                ]

        return thresholds

    def generate_chart(
        self,
        symbol: str,
        timeframe: str = '1h',
        save_path: Optional[str] = None
    ) -> str:
        """Generate candlestick chart with indicators and trading signals."""
        try:
            # Fetch candle data
            df, ma_periods = self.fetch_candles(symbol, timeframe)

            # Get executed orders
            hours = 24 if timeframe == '1h' else 120 if timeframe == '4h' else 720
            orders = self.get_executed_orders(symbol, hours)

            # Calculate thresholds
            thresholds = self.calculate_thresholds(df, timeframe)

            # Create figure with subplots
            fig, axes = mpf.plot(
                df,
                type='candle',
                style=self.chart_style,
                volume=True,
                figsize=(14, 8),
                returnfig=True,
                title=f'{symbol} - {timeframe.upper()}',
                ylabel='Price ($)',
                ylabel_lower='Volume',
                show_nontrading=False
            )

            # Get the main price axis
            ax = axes[0]

            # Plot moving averages
            colors = ['#ffa726', '#42a5f5', '#ab47bc']  # Orange, Blue, Purple
            labels = []

            for i, period in enumerate(ma_periods):
                ma_col = f'MA{period}'
                if ma_col in df.columns:
                    ma_values = df[ma_col].dropna()
                    if not ma_values.empty:
                        ax.plot(
                            df.index[-len(ma_values):],
                            ma_values,
                            color=colors[i % len(colors)],
                            linewidth=1.5,
                            label=ma_col,
                            alpha=0.8
                        )
                        labels.append(ma_col)

            # Plot threshold lines
            for ma_name, levels in thresholds.items():
                support, resistance = levels
                # Support line
                ax.axhline(
                    y=support,
                    color='#4caf50',
                    linestyle='--',
                    linewidth=0.8,
                    alpha=0.5,
                    label=f'{ma_name} Support'
                )
                # Resistance line
                ax.axhline(
                    y=resistance,
                    color='#f44336',
                    linestyle='--',
                    linewidth=0.8,
                    alpha=0.5,
                    label=f'{ma_name} Resistance'
                )

            # Plot executed orders with arrows
            for order in orders:
                # Find the nearest candle to the order timestamp
                time_diff = abs(df.index - order['timestamp'])
                nearest_idx = time_diff.argmin()

                if nearest_idx < len(df):
                    x_pos = df.index[nearest_idx]
                    y_pos = order['price']

                    # Determine arrow properties
                    if order['side'] == 'BUY':
                        arrow_color = '#4caf50'  # Green for buy
                        arrow_start = y_pos - (df['high'].max() - df['low'].min()) * 0.05
                        arrow_direction = 'up'
                        marker = '^'
                    else:
                        arrow_color = '#f44336'  # Red for sell
                        arrow_start = y_pos + (df['high'].max() - df['low'].min()) * 0.05
                        arrow_direction = 'down'
                        marker = 'v'

                    # Plot arrow marker
                    ax.scatter(
                        x_pos,
                        y_pos,
                        color=arrow_color,
                        marker=marker,
                        s=100,
                        zorder=5,
                        alpha=0.9
                    )

                    # Add text annotation
                    ax.annotate(
                        f"{order['side']}\n${y_pos:.2f}",
                        xy=(x_pos, y_pos),
                        xytext=(10, 20 if arrow_direction == 'up' else -30),
                        textcoords='offset points',
                        fontsize=8,
                        color=arrow_color,
                        fontweight='bold',
                        bbox=dict(
                            boxstyle='round,pad=0.3',
                            facecolor='white',
                            edgecolor=arrow_color,
                            alpha=0.7
                        )
                    )

            # Add legend
            ax.legend(
                loc='upper left',
                frameon=True,
                fancybox=True,
                shadow=True,
                borderpad=1,
                framealpha=0.9
            )

            # Add grid
            ax.grid(True, alpha=0.3, linestyle='--')

            # Format x-axis dates
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
            fig.autofmt_xdate()

            # Add current price line
            current_price = df['close'].iloc[-1]
            ax.axhline(
                y=current_price,
                color='#ffffff',
                linestyle='-',
                linewidth=1,
                alpha=0.5
            )
            ax.text(
                df.index[-1],
                current_price,
                f'  ${current_price:.2f}',
                color='#ffffff',
                fontsize=10,
                va='center',
                fontweight='bold'
            )

            # Save or create temporary file
            if save_path:
                output_path = save_path
            else:
                temp_file = tempfile.NamedTemporaryFile(
                    suffix='.png',
                    delete=False,
                    prefix=f'chart_{symbol}_{timeframe}_'
                )
                output_path = temp_file.name

            # Save figure with high quality
            plt.tight_layout()
            fig.savefig(
                output_path,
                dpi=150,
                facecolor='#1e1f29',
                edgecolor='none',
                bbox_inches='tight'
            )
            plt.close(fig)

            logger.info(f"Chart generated: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Error generating chart: {e}")
            raise


def test_chart_generation():
    """Test function for chart generation."""
    generator = ChartGenerator()

    # Test with different symbols and timeframes
    tests = [
        ('BTCUSDT', '1h'),
        ('ETHUSDT', '4h'),
        ('BNBUSDT', '1d'),
    ]

    for symbol, timeframe in tests:
        try:
            path = generator.generate_chart(symbol, timeframe)
            print(f"✅ Generated chart for {symbol} {timeframe}: {path}")
        except Exception as e:
            print(f"❌ Failed to generate chart for {symbol} {timeframe}: {e}")


if __name__ == "__main__":
    test_chart_generation()