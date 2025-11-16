"""
Chart generator for candlestick charts with trading signals.
Fixed version using mplfinance addplot correctly.
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

    def fetch_candles(self, symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
        """Fetch OHLCV data from Binance."""
        try:
            # Convert timeframe to ccxt format
            tf_map = {'1h': '1h', '4h': '4h', '1d': '1d'}
            tf = tf_map.get(timeframe, '1h')

            # Fetch OHLCV data - get extra for MA calculation
            ohlcv = self.exchange.fetch_ohlcv(symbol, tf, limit=limit + 200)

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

        # Choose only the most relevant MA for thresholds (closest to current price)
        best_ma = None
        best_ma_value = None
        min_distance = float('inf')

        if timeframe == '1h':
            # Check which MA is closest to current price
            if 'MA50' in df.columns and not pd.isna(df['MA50'].iloc[-1]):
                ma50 = df['MA50'].iloc[-1]
                distance = abs(current_price - ma50)
                if distance < min_distance:
                    min_distance = distance
                    best_ma = 'MA50'
                    best_ma_value = ma50

            if 'MA100' in df.columns and not pd.isna(df['MA100'].iloc[-1]):
                ma100 = df['MA100'].iloc[-1]
                distance = abs(current_price - ma100)
                if distance < min_distance:
                    min_distance = distance
                    best_ma = 'MA100'
                    best_ma_value = ma100

            # Set thresholds for the closest MA only
            if best_ma == 'MA50' and best_ma_value:
                thresholds['MA50'] = [
                    best_ma_value * 0.965,  # -3.5% support
                    best_ma_value * 1.035   # +3.5% resistance
                ]
            elif best_ma == 'MA100' and best_ma_value:
                thresholds['MA100'] = [
                    best_ma_value * 0.95,  # -5% support
                    best_ma_value * 1.05   # +5% resistance
                ]

        elif timeframe == '4h':
            # Similar logic for 4h
            if 'MA50' in df.columns and not pd.isna(df['MA50'].iloc[-1]):
                ma50 = df['MA50'].iloc[-1]
                distance = abs(current_price - ma50)
                if distance < min_distance:
                    min_distance = distance
                    best_ma = 'MA50'
                    best_ma_value = ma50

            if 'MA100' in df.columns and not pd.isna(df['MA100'].iloc[-1]):
                ma100 = df['MA100'].iloc[-1]
                distance = abs(current_price - ma100)
                if distance < min_distance:
                    min_distance = distance
                    best_ma = 'MA100'
                    best_ma_value = ma100

            # Set thresholds for the closest MA only
            if best_ma == 'MA50' and best_ma_value:
                thresholds['MA50'] = [
                    best_ma_value * 0.965,  # -3.5% support
                    best_ma_value * 1.035   # +3.5% resistance
                ]
            elif best_ma == 'MA100' and best_ma_value:
                thresholds['MA100'] = [
                    best_ma_value * 0.968,  # -3.2% support
                    best_ma_value * 1.032   # +3.2% resistance
                ]

        else:  # 1d
            # MA200: Asset-specific thresholds
            if 'MA200' in df.columns and not pd.isna(df['MA200'].iloc[-1]):
                ma200 = df['MA200'].iloc[-1]
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

            # Prepare addplot items for mplfinance
            addplot_items = []

            # Add moving averages
            colors_ma = ['#ffa726', '#42a5f5', '#ab47bc']  # Orange, Blue, Purple
            for i, period in enumerate(ma_periods):
                ma_col = f'MA{period}'
                if ma_col in df.columns:
                    addplot_items.append(
                        mpf.make_addplot(
                            df[ma_col],
                            color=colors_ma[i % len(colors_ma)],
                            width=1.5,
                            label=ma_col
                        )
                    )

            # Add horizontal lines for thresholds
            hlines_dict = {}
            for ma_name, levels in thresholds.items():
                support, resistance = levels
                # Support lines
                if 'support' not in hlines_dict:
                    hlines_dict['support'] = []
                hlines_dict['support'].append(support)

                # Resistance lines
                if 'resistance' not in hlines_dict:
                    hlines_dict['resistance'] = []
                hlines_dict['resistance'].append(resistance)

            # Prepare buy/sell markers
            buy_markers = []
            sell_markers = []

            for order in orders:
                # Find the nearest candle to the order timestamp
                time_diff = abs(df.index - order['timestamp'])
                nearest_idx = time_diff.argmin()

                if order['side'] == 'BUY':
                    # Create a series with NaN except at the buy point
                    buy_marker = pd.Series(index=df.index, data=np.nan)
                    buy_marker.iloc[nearest_idx] = order['price']
                    buy_markers.append(buy_marker)
                else:
                    # Create a series with NaN except at the sell point
                    sell_marker = pd.Series(index=df.index, data=np.nan)
                    sell_marker.iloc[nearest_idx] = order['price']
                    sell_markers.append(sell_marker)

            # Add buy markers
            for buy_marker in buy_markers:
                addplot_items.append(
                    mpf.make_addplot(
                        buy_marker,
                        type='scatter',
                        markersize=100,
                        marker='^',
                        color='#4caf50'
                    )
                )

            # Add sell markers
            for sell_marker in sell_markers:
                addplot_items.append(
                    mpf.make_addplot(
                        sell_marker,
                        type='scatter',
                        markersize=100,
                        marker='v',
                        color='#f44336'
                    )
                )

            # Create custom style with dark theme
            custom_style = mpf.make_mpf_style(
                base_mpf_style='nightclouds',
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

            # Prepare horizontal lines
            hlines = []
            colors_hlines = []
            linestyles = []
            linewidths = []

            # Add current price line (white)
            current_price = df['close'].iloc[-1]
            hlines.append(current_price)
            colors_hlines.append('#ffffff')
            linestyles.append('-')
            linewidths.append(1.2)

            # Add support lines
            if 'support' in hlines_dict:
                for support_level in hlines_dict['support']:
                    hlines.append(support_level)
                    colors_hlines.append('#4caf50')
                    linestyles.append('--')
                    linewidths.append(0.8)

            # Add resistance lines
            if 'resistance' in hlines_dict:
                for resistance_level in hlines_dict['resistance']:
                    hlines.append(resistance_level)
                    colors_hlines.append('#f44336')
                    linestyles.append('--')
                    linewidths.append(0.8)

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

            # Create the plot
            fig, axes = mpf.plot(
                df,
                type='candle',
                style=custom_style,
                volume=True,
                figsize=(14, 8),
                title=f'{symbol} - {timeframe.upper()}',
                ylabel='Price ($)',
                ylabel_lower='Volume',
                addplot=addplot_items if addplot_items else None,
                hlines=dict(
                    hlines=hlines,
                    colors=colors_hlines,
                    linestyle=linestyles,
                    linewidths=linewidths
                ) if hlines else None,
                returnfig=True,
                savefig=dict(
                    fname=output_path,
                    dpi=150,
                    bbox_inches='tight',
                    facecolor='#1e1f29'
                )
            )

            # Add current price annotation
            ax = axes[0]

            # Add current price label
            ax.text(
                0.02, 0.98,
                f'Current: ${current_price:,.2f}',
                transform=ax.transAxes,
                fontsize=10,
                color='white',
                fontweight='bold',
                va='top',
                bbox=dict(
                    boxstyle='round,pad=0.3',
                    facecolor='#2c2e3e',
                    edgecolor='white',
                    alpha=0.8
                )
            )

            # Add order annotations
            for order in orders:
                time_diff = abs(df.index - order['timestamp'])
                nearest_idx = time_diff.argmin()

                if nearest_idx < len(df):
                    x_pos = df.index[nearest_idx]
                    y_pos = order['price']

                    # Add text annotation
                    arrow_color = '#4caf50' if order['side'] == 'BUY' else '#f44336'
                    ax.annotate(
                        f"{order['side']}\n${y_pos:.2f}",
                        xy=(mdates.date2num(x_pos), y_pos),
                        xytext=(10, 20 if order['side'] == 'BUY' else -30),
                        textcoords='offset points',
                        fontsize=8,
                        color='white',
                        fontweight='bold',
                        bbox=dict(
                            boxstyle='round,pad=0.3',
                            facecolor=arrow_color,
                            edgecolor='white',
                            alpha=0.7
                        ),
                        arrowprops=dict(
                            arrowstyle='->',
                            color=arrow_color,
                            alpha=0.7
                        )
                    )

            plt.close(fig)

            logger.info(f"Chart generated: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Error generating chart: {e}")
            raise