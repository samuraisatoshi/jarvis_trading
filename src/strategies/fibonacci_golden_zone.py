"""
Fibonacci Golden Zone Trading Strategy.

A strategy based on Fibonacci retracement levels, specifically targeting the
"Golden Zone" (50%-61.8% retracement) for high-probability trade setups.

Core Concept:
- In uptrends: Wait for price to retrace to 50%-61.8% before buying
- In downtrends: Wait for price to rally to 50%-61.8% before selling
- In sideways: HOLD (no trades)

Confirmation Signals (need 2+ of 4):
1. RSI Bullish Divergence
2. Volume Spike (>1.5x average)
3. Bullish Engulfing Candle
4. Hammer Candle Pattern

Risk Management:
- Stop Loss: 78.6% retracement level
- Take Profit 1: 161.8% extension
- Take Profit 2: 261.8% extension

SOLID Principles:
- Single Responsibility: Only Fibonacci Golden Zone strategy logic
- Open/Closed: Extends TradingStrategy, closed for modification
- Liskov Substitution: Can replace any TradingStrategy
- Dependency Inversion: Depends on TradingStrategy abstraction

Example:
    >>> from src.strategies.fibonacci_golden_zone import FibonacciGoldenZoneStrategy
    >>> strategy = FibonacciGoldenZoneStrategy()
    >>> signal = strategy.generate_signal(df)
    >>> print(signal['action'])  # 'BUY', 'SELL', or 'HOLD'
"""

import pandas as pd
import numpy as np
from typing import Tuple, Dict, List
from loguru import logger

from src.strategies.base import BaseIndicatorStrategy
from src.strategies.models import FibonacciLevels, TrendType, SignalType


class FibonacciGoldenZoneStrategy(BaseIndicatorStrategy):
    """
    Fibonacci Golden Zone Trading Strategy implementation.

    This strategy identifies high-probability trade setups by combining:
    - Trend identification (EMA 20/50/200)
    - Swing point detection (pivot highs/lows)
    - Fibonacci retracement levels
    - Golden Zone detection (50%-61.8%)
    - Multiple confirmation signals

    Attributes:
        golden_zone: Tuple of (min, max) Fibonacci levels for Golden Zone
        stop_level: Fibonacci level for stop loss
        targets: List of Fibonacci extension levels for take profit
    """

    def __init__(self):
        """Initialize strategy with default parameters."""
        self.golden_zone = (0.50, 0.618)  # 50% to 61.8% retracement
        self.stop_level = 0.786  # 78.6% retracement for stop loss
        self.targets = [1.618, 2.618]  # Extension levels for take profit

        logger.info(
            f"Fibonacci Golden Zone Strategy initialized:\n"
            f"  Golden Zone: {self.golden_zone[0]:.1%} - {self.golden_zone[1]:.1%}\n"
            f"  Stop Level: {self.stop_level:.1%}\n"
            f"  Targets: {[f'{t:.1%}' for t in self.targets]}"
        )

    def identify_trend(self, df: pd.DataFrame) -> str:
        """
        Identify market trend using EMA crossovers.

        Trend Rules:
        - UPTREND: EMA20 > EMA50 > EMA200
        - DOWNTREND: EMA20 < EMA50 < EMA200
        - LATERAL: EMAs entangled (difference < 2%)

        Args:
            df: DataFrame with 'close' prices

        Returns:
            'UPTREND', 'DOWNTREND', or 'LATERAL'

        Raises:
            ValueError: If DataFrame has insufficient data
        """
        if len(df) < 200:
            raise ValueError(f"Need at least 200 candles for trend identification, got {len(df)}")

        # Calculate EMAs
        ema20 = self.calculate_ema(df['close'], 20)
        ema50 = self.calculate_ema(df['close'], 50)
        ema200 = self.calculate_ema(df['close'], 200)

        # Get latest values
        e20 = ema20.iloc[-1]
        e50 = ema50.iloc[-1]
        e200 = ema200.iloc[-1]

        # Check for uptrend
        if e20 > e50 > e200:
            logger.debug(f"UPTREND detected: EMA20={e20:.2f} > EMA50={e50:.2f} > EMA200={e200:.2f}")
            return 'UPTREND'

        # Check for downtrend
        if e20 < e50 < e200:
            logger.debug(f"DOWNTREND detected: EMA20={e20:.2f} < EMA50={e50:.2f} < EMA200={e200:.2f}")
            return 'DOWNTREND'

        # Check if EMAs are entangled (difference < 2%)
        max_ema = max(e20, e50, e200)
        min_ema = min(e20, e50, e200)
        diff_pct = (max_ema - min_ema) / min_ema

        logger.debug(
            f"LATERAL detected: EMAs entangled\n"
            f"  EMA20={e20:.2f}, EMA50={e50:.2f}, EMA200={e200:.2f}\n"
            f"  Difference: {diff_pct:.2%}"
        )
        return 'LATERAL'

    def find_swing_points(
        self, df: pd.DataFrame, lookback: int = 20
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Find significant swing highs and lows (pivot points).

        A swing high is a local maximum where the high is greater than
        the highs of 'lookback' candles before and after it.

        A swing low is a local minimum where the low is less than
        the lows of 'lookback' candles before and after it.

        Args:
            df: DataFrame with 'high' and 'low' columns
            lookback: Number of candles to look before/after for pivot

        Returns:
            Tuple of (swing_highs_df, swing_lows_df)

        Raises:
            ValueError: If DataFrame has insufficient data
        """
        min_candles = lookback * 2 + 1
        if len(df) < min_candles:
            raise ValueError(f"Need at least {min_candles} candles for swing points, got {len(df)}")

        # Find local maxima (swing highs)
        highs_rolling = df['high'].rolling(window=lookback*2+1, center=True).max()
        is_swing_high = df['high'] == highs_rolling
        swing_highs = df[is_swing_high].copy()

        # Find local minima (swing lows)
        lows_rolling = df['low'].rolling(window=lookback*2+1, center=True).min()
        is_swing_low = df['low'] == lows_rolling
        swing_lows = df[is_swing_low].copy()

        # Remove NaN rows (from rolling window edges)
        swing_highs = swing_highs.dropna(subset=['high'])
        swing_lows = swing_lows.dropna(subset=['low'])

        logger.debug(
            f"Found {len(swing_highs)} swing highs and {len(swing_lows)} swing lows "
            f"(lookback={lookback})"
        )

        return swing_highs, swing_lows

    def calculate_fibonacci_levels(
        self, high: float, low: float, is_uptrend: bool = True
    ) -> FibonacciLevels:
        """
        Calculate Fibonacci retracement and extension levels.

        In uptrend (buying):
        - Retracements measure pullbacks from high to low
        - Extensions project targets above high

        In downtrend (selling):
        - Retracements measure rallies from low to high
        - Extensions project targets below low

        Args:
            high: Swing high price
            low: Swing low price
            is_uptrend: True if calculating for uptrend, False for downtrend

        Returns:
            FibonacciLevels dataclass with all levels

        Raises:
            ValueError: If high <= low
        """
        if high <= low:
            raise ValueError(f"High ({high}) must be greater than low ({low})")

        diff = high - low

        if is_uptrend:
            # In uptrend: retracements go DOWN from high, extensions go UP
            levels = FibonacciLevels(
                high=high,
                low=low,
                level_0236=high - (diff * 0.236),
                level_0382=high - (diff * 0.382),
                level_0500=high - (diff * 0.500),  # Golden Zone start
                level_0618=high - (diff * 0.618),  # Golden Zone end
                level_0786=high - (diff * 0.786),  # Stop loss level
                level_1000=low,
                level_1618=high + (diff * 0.618),  # Target 1
                level_2618=high + (diff * 1.618),  # Target 2
                is_uptrend=True
            )
        else:
            # In downtrend: retracements go UP from low, extensions go DOWN
            levels = FibonacciLevels(
                high=high,
                low=low,
                level_0236=low + (diff * 0.236),
                level_0382=low + (diff * 0.382),
                level_0500=low + (diff * 0.500),  # Golden Zone start
                level_0618=low + (diff * 0.618),  # Golden Zone end
                level_0786=low + (diff * 0.786),  # Stop loss level
                level_1000=high,
                level_1618=low - (diff * 0.618),  # Target 1
                level_2618=low - (diff * 1.618),  # Target 2
                is_uptrend=False
            )

        logger.debug(
            f"Fibonacci levels calculated ({('UPTREND' if is_uptrend else 'DOWNTREND')}):\n"
            f"  High: ${high:.2f}\n"
            f"  Low: ${low:.2f}\n"
            f"  Golden Zone: ${levels.golden_zone_min:.2f} - ${levels.golden_zone_max:.2f}\n"
            f"  Stop Loss: ${levels.level_0786:.2f}\n"
            f"  Target 1: ${levels.level_1618:.2f}\n"
            f"  Target 2: ${levels.level_2618:.2f}"
        )

        return levels

    def is_in_golden_zone(
        self, price: float, fib_levels: FibonacciLevels, trend: str
    ) -> bool:
        """
        Check if current price is within Golden Zone (50%-61.8%).

        Args:
            price: Current price
            fib_levels: FibonacciLevels object
            trend: 'UPTREND' or 'DOWNTREND'

        Returns:
            True if price is in Golden Zone, False otherwise
        """
        in_zone = fib_levels.is_in_golden_zone(price)

        if in_zone:
            logger.debug(f"Price ${price:.2f} is IN Golden Zone")
        else:
            logger.debug(
                f"Price ${price:.2f} is OUTSIDE Golden Zone: "
                f"${fib_levels.golden_zone_min:.2f} - ${fib_levels.golden_zone_max:.2f}"
            )

        return in_zone

    def check_confirmation_signals(
        self, df: pd.DataFrame, index: int
    ) -> List[str]:
        """
        Check for multiple confirmation signals at given index.

        Signals checked:
        1. RSI_BULLISH_DIVERGENCE: Price lower but RSI higher (bullish)
        2. RSI_BEARISH_DIVERGENCE: Price higher but RSI lower (bearish)
        3. VOLUME_SPIKE: Volume > 1.5x 20-period average
        4. BULLISH_ENGULFING: Current candle engulfs previous bearish candle
        5. BEARISH_ENGULFING: Current candle engulfs previous bullish candle
        6. HAMMER: Long lower shadow (>2x body), small upper shadow
        7. SHOOTING_STAR: Long upper shadow (>2x body), small lower shadow

        Args:
            df: DataFrame with OHLCV data
            index: Index position to check (usually -1 for latest)

        Returns:
            List of confirmation signal names detected
        """
        confirmations = []

        # Need at least 6 candles for divergence check
        if index < 5 or index >= len(df):
            return confirmations

        # Calculate RSI if not present
        if 'rsi' not in df.columns:
            df['rsi'] = self.calculate_rsi(df['close'], period=14)

        # 1. RSI Divergence (bullish)
        price_now = df['close'].iloc[index]
        price_prev = df['close'].iloc[index - 5]
        rsi_now = df['rsi'].iloc[index]
        rsi_prev = df['rsi'].iloc[index - 5]

        if not pd.isna(rsi_now) and not pd.isna(rsi_prev):
            # Bullish divergence: price lower, RSI higher
            if price_now < price_prev and rsi_now > rsi_prev:
                confirmations.append('RSI_BULLISH_DIVERGENCE')
                logger.debug(
                    f"RSI Bullish Divergence: "
                    f"Price {price_prev:.2f}->{price_now:.2f}, "
                    f"RSI {rsi_prev:.1f}->{rsi_now:.1f}"
                )

            # Bearish divergence: price higher, RSI lower
            elif price_now > price_prev and rsi_now < rsi_prev:
                confirmations.append('RSI_BEARISH_DIVERGENCE')
                logger.debug(
                    f"RSI Bearish Divergence: "
                    f"Price {price_prev:.2f}->{price_now:.2f}, "
                    f"RSI {rsi_prev:.1f}->{rsi_now:.1f}"
                )

        # 2. Volume Spike
        volume_now = df['volume'].iloc[index]
        avg_volume = df['volume'].rolling(20).mean().iloc[index]

        if not pd.isna(avg_volume) and avg_volume > 0:
            if volume_now > avg_volume * 1.5:
                confirmations.append('VOLUME_SPIKE')
                logger.debug(
                    f"Volume Spike: {volume_now:.0f} > "
                    f"{avg_volume * 1.5:.0f} (1.5x avg)"
                )

        # 3. Candlestick Patterns (need previous candle)
        if index > 0:
            current = df.iloc[index]
            prev = df.iloc[index - 1]

            # Bullish Engulfing
            prev_bearish = prev['close'] < prev['open']
            current_bullish = current['close'] > current['open']
            current_engulfs = (
                current['close'] > prev['open'] and
                current['open'] < prev['close']
            )

            if prev_bearish and current_bullish and current_engulfs:
                confirmations.append('BULLISH_ENGULFING')
                logger.debug("Bullish Engulfing candle detected")

            # Bearish Engulfing
            prev_bullish = prev['close'] > prev['open']
            current_bearish = current['close'] < current['open']
            current_engulfs_bear = (
                current['open'] > prev['close'] and
                current['close'] < prev['open']
            )

            if prev_bullish and current_bearish and current_engulfs_bear:
                confirmations.append('BEARISH_ENGULFING')
                logger.debug("Bearish Engulfing candle detected")

            # Hammer (bullish reversal)
            body = abs(current['close'] - current['open'])
            lower_shadow = min(current['open'], current['close']) - current['low']
            upper_shadow = current['high'] - max(current['open'], current['close'])

            if body > 0 and lower_shadow > body * 2 and upper_shadow < body:
                confirmations.append('HAMMER')
                logger.debug("Hammer candle detected")

            # Shooting Star (bearish reversal)
            if body > 0 and upper_shadow > body * 2 and lower_shadow < body:
                confirmations.append('SHOOTING_STAR')
                logger.debug("Shooting Star candle detected")

        return confirmations

    def generate_signal(self, df: pd.DataFrame) -> Dict:
        """
        Generate trading signal based on complete strategy.

        Process:
        1. Identify trend (EMA analysis)
        2. If LATERAL -> HOLD
        3. Find swing points
        4. Calculate Fibonacci levels
        5. Check if price in Golden Zone
        6. Verify confirmation signals (need 2+)
        7. Generate BUY/SELL/HOLD signal with entry/stop/targets

        Args:
            df: DataFrame with OHLCV data (needs 200+ candles)

        Returns:
            Dict with signal information (compatible with existing code)
        """
        try:
            # 1. Identify trend
            trend = self.identify_trend(df)

            if trend == 'LATERAL':
                return {
                    'action': 'HOLD',
                    'reason': 'Mercado lateral - sem tendência clara definida',
                    'trend': trend,
                    'current_price': df['close'].iloc[-1]
                }

            # 2. Find swing points
            swing_highs, swing_lows = self.find_swing_points(df)

            if len(swing_highs) == 0 or len(swing_lows) == 0:
                return {
                    'action': 'HOLD',
                    'reason': 'Sem swing points identificados - aguardando formação de padrão',
                    'trend': trend,
                    'current_price': df['close'].iloc[-1]
                }

            # 3. Get most recent swing high and low
            last_high = swing_highs.iloc[-1]['high']
            last_low = swing_lows.iloc[-1]['low']

            # 4. Calculate Fibonacci levels
            fib_levels = self.calculate_fibonacci_levels(
                high=last_high,
                low=last_low,
                is_uptrend=(trend == 'UPTREND')
            )

            # 5. Get current price
            current_price = df['close'].iloc[-1]

            # 6. Check if in Golden Zone
            if not self.is_in_golden_zone(current_price, fib_levels, trend):
                golden_zone_str = f"${fib_levels.golden_zone_min:.2f} - ${fib_levels.golden_zone_max:.2f}"
                return {
                    'action': 'HOLD',
                    'reason': f'Preço fora da Golden Zone (aguardando retração)',
                    'trend': trend,
                    'current_price': current_price,
                    'golden_zone': golden_zone_str,
                    'fib_levels': fib_levels.to_dict()
                }

            # 7. Check confirmation signals
            confirmations = self.check_confirmation_signals(df, len(df) - 1)

            # Need at least 2 confirmations
            if len(confirmations) < 2:
                return {
                    'action': 'HOLD',
                    'reason': f'Na Golden Zone mas apenas {len(confirmations)} confirmação(ões) - precisa 2+',
                    'trend': trend,
                    'current_price': current_price,
                    'golden_zone': f"${fib_levels.golden_zone_min:.2f} - ${fib_levels.golden_zone_max:.2f}",
                    'confirmations': confirmations,
                    'fib_levels': fib_levels.to_dict()
                }

            # 8. Generate BUY or SELL signal
            if trend == 'UPTREND':
                # Filter for bullish confirmations
                bullish_confirmations = [
                    c for c in confirmations
                    if c in ['RSI_BULLISH_DIVERGENCE', 'VOLUME_SPIKE', 'BULLISH_ENGULFING', 'HAMMER']
                ]

                if len(bullish_confirmations) >= 2:
                    return {
                        'action': 'BUY',
                        'reason': f'Golden Zone em UPTREND com {len(bullish_confirmations)} confirmações bullish',
                        'trend': trend,
                        'entry': current_price,
                        'stop_loss': fib_levels.level_0786,
                        'take_profit_1': fib_levels.level_1618,
                        'take_profit_2': fib_levels.level_2618,
                        'confirmations': bullish_confirmations,
                        'fib_levels': fib_levels.to_dict()
                    }

            elif trend == 'DOWNTREND':
                # Filter for bearish confirmations
                bearish_confirmations = [
                    c for c in confirmations
                    if c in ['RSI_BEARISH_DIVERGENCE', 'VOLUME_SPIKE', 'BEARISH_ENGULFING', 'SHOOTING_STAR']
                ]

                if len(bearish_confirmations) >= 2:
                    return {
                        'action': 'SELL',
                        'reason': f'Golden Zone em DOWNTREND com {len(bearish_confirmations)} confirmações bearish',
                        'trend': trend,
                        'entry': current_price,
                        'stop_loss': fib_levels.level_0786,
                        'take_profit_1': fib_levels.level_1618,
                        'take_profit_2': fib_levels.level_2618,
                        'confirmations': bearish_confirmations,
                        'fib_levels': fib_levels.to_dict()
                    }

            # Default: HOLD (in Golden Zone but confirmations don't match trend)
            return {
                'action': 'HOLD',
                'reason': 'Confirmações não alinham com tendência - aguardando',
                'trend': trend,
                'current_price': current_price,
                'golden_zone': f"${fib_levels.golden_zone_min:.2f} - ${fib_levels.golden_zone_max:.2f}",
                'confirmations': confirmations,
                'fib_levels': fib_levels.to_dict()
            }

        except Exception as e:
            logger.error(f"Erro ao gerar sinal: {e}", exc_info=True)
            return {
                'action': 'HOLD',
                'reason': f'Erro na análise: {str(e)}',
                'trend': 'UNKNOWN',
                'current_price': df['close'].iloc[-1] if len(df) > 0 else 0
            }
