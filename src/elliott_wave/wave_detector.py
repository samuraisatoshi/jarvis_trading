"""
Wave detection algorithms for Elliott Wave analysis.

This module provides different strategies for detecting significant price swings
(pivot points) which form the basis of Elliott Wave counting.

SOLID Principles:
- Single Responsibility: Focus only on pivot/swing detection
- Open/Closed: Extendable through WaveDetectorInterface
- Liskov Substitution: All detectors interchangeable
- Dependency Inversion: Depends on DataFrame abstraction

Design Pattern: Strategy Pattern for different detection algorithms
"""

from abc import ABC, abstractmethod
from typing import List, Tuple
import pandas as pd
import numpy as np
from .models import PivotPoint


class WaveDetectorInterface(ABC):
    """
    Abstract interface for wave detection algorithms.

    All wave detectors must implement this interface to ensure
    interchangeability and consistent API.
    """

    @abstractmethod
    def detect_pivots(self, df: pd.DataFrame) -> Tuple[List[PivotPoint],
                                                        List[PivotPoint]]:
        """
        Detect pivot highs and lows in price data.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Tuple of (pivot_highs, pivot_lows) as PivotPoint lists
        """
        pass


class PivotDetector(WaveDetectorInterface):
    """
    Standard pivot point detector using swing high/low algorithm.

    A pivot high is confirmed when a high is surrounded by lower highs
    on both sides. A pivot low is confirmed when a low is surrounded
    by higher lows on both sides.

    Attributes:
        window: Number of bars on each side to confirm pivot (default: 5)
        min_price_change: Minimum price change % to consider valid (default: 0.5%)
    """

    def __init__(self, window: int = 5, min_price_change: float = 0.5):
        """
        Initialize pivot detector.

        Args:
            window: Lookback/lookahead window for pivot confirmation
            min_price_change: Minimum % change to filter noise
        """
        self.window = window
        self.min_price_change = min_price_change

    def detect_pivots(self, df: pd.DataFrame) -> Tuple[List[PivotPoint],
                                                        List[PivotPoint]]:
        """
        Detect pivot highs and lows using standard swing algorithm.

        Args:
            df: DataFrame with columns ['high', 'low', 'close']

        Returns:
            Tuple of (pivot_highs, pivot_lows)
        """
        pivot_highs: List[PivotPoint] = []
        pivot_lows: List[PivotPoint] = []

        # Iterate through valid range (excluding edges)
        for i in range(self.window, len(df) - self.window):
            current_high = df.iloc[i]['high']
            current_low = df.iloc[i]['low']

            # Check for pivot high
            if self._is_pivot_high(df, i):
                pivot_highs.append(PivotPoint(
                    index=i,
                    timestamp=df.index[i].isoformat(),
                    price=current_high,
                    pivot_type='high'
                ))

            # Check for pivot low
            if self._is_pivot_low(df, i):
                pivot_lows.append(PivotPoint(
                    index=i,
                    timestamp=df.index[i].isoformat(),
                    price=current_low,
                    pivot_type='low'
                ))

        # Filter by minimum price change
        pivot_highs = self._filter_by_price_change(pivot_highs)
        pivot_lows = self._filter_by_price_change(pivot_lows)

        return pivot_highs, pivot_lows

    def _is_pivot_high(self, df: pd.DataFrame, index: int) -> bool:
        """
        Check if index is a pivot high.

        Args:
            df: DataFrame with price data
            index: Index to check

        Returns:
            True if valid pivot high
        """
        current_high = df.iloc[index]['high']

        # Check left side (all highs must be lower)
        for j in range(1, self.window + 1):
            if df.iloc[index - j]['high'] >= current_high:
                return False

        # Check right side (all highs must be lower)
        for j in range(1, self.window + 1):
            if df.iloc[index + j]['high'] >= current_high:
                return False

        return True

    def _is_pivot_low(self, df: pd.DataFrame, index: int) -> bool:
        """
        Check if index is a pivot low.

        Args:
            df: DataFrame with price data
            index: Index to check

        Returns:
            True if valid pivot low
        """
        current_low = df.iloc[index]['low']

        # Check left side (all lows must be higher)
        for j in range(1, self.window + 1):
            if df.iloc[index - j]['low'] <= current_low:
                return False

        # Check right side (all lows must be higher)
        for j in range(1, self.window + 1):
            if df.iloc[index + j]['low'] <= current_low:
                return False

        return True

    def _filter_by_price_change(self, pivots: List[PivotPoint]
                                ) -> List[PivotPoint]:
        """
        Filter pivots by minimum price change threshold.

        Removes noise by ensuring consecutive pivots have meaningful
        price difference.

        Args:
            pivots: List of pivot points

        Returns:
            Filtered list of pivots
        """
        if len(pivots) < 2:
            return pivots

        filtered = [pivots[0]]  # Always keep first

        for i in range(1, len(pivots)):
            prev_price = filtered[-1].price
            curr_price = pivots[i].price
            change_pct = abs((curr_price - prev_price) / prev_price * 100)

            if change_pct >= self.min_price_change:
                filtered.append(pivots[i])

        return filtered


class ZigZagDetector(WaveDetectorInterface):
    """
    ZigZag indicator-based pivot detector.

    Identifies significant price swings using percentage-based threshold.
    More aggressive than standard pivot detector.

    Attributes:
        threshold_pct: Minimum % price change to register new pivot (default: 3%)
    """

    def __init__(self, threshold_pct: float = 3.0):
        """
        Initialize ZigZag detector.

        Args:
            threshold_pct: Minimum % move to create new pivot
        """
        self.threshold_pct = threshold_pct

    def detect_pivots(self, df: pd.DataFrame) -> Tuple[List[PivotPoint],
                                                        List[PivotPoint]]:
        """
        Detect pivots using ZigZag algorithm.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Tuple of (pivot_highs, pivot_lows)
        """
        pivot_highs: List[PivotPoint] = []
        pivot_lows: List[PivotPoint] = []

        if len(df) < 3:
            return pivot_highs, pivot_lows

        # Initialize with first point
        pivots = []
        last_pivot = {
            'index': 0,
            'timestamp': df.index[0].isoformat(),
            'price': df.iloc[0]['close'],
            'type': 'start'
        }
        pivots.append(last_pivot)

        # Track current trend
        trend = None  # 'up' or 'down'
        extreme_idx = 0
        extreme_price = df.iloc[0]['close']

        for i in range(1, len(df)):
            high = df.iloc[i]['high']
            low = df.iloc[i]['low']

            # Calculate % change from last extreme
            high_change = ((high - extreme_price) / extreme_price * 100)
            low_change = ((extreme_price - low) / extreme_price * 100)

            if trend is None:
                # Establish initial trend
                if high_change >= self.threshold_pct:
                    trend = 'up'
                    extreme_idx = i
                    extreme_price = high
                elif low_change >= self.threshold_pct:
                    trend = 'down'
                    extreme_idx = i
                    extreme_price = low

            elif trend == 'up':
                # In uptrend, track new highs
                if high > extreme_price:
                    extreme_idx = i
                    extreme_price = high
                # Check for reversal
                elif low_change >= self.threshold_pct:
                    # Reversal confirmed - save pivot high
                    pivot_highs.append(PivotPoint(
                        index=extreme_idx,
                        timestamp=df.index[extreme_idx].isoformat(),
                        price=extreme_price,
                        pivot_type='high'
                    ))
                    # Switch to downtrend
                    trend = 'down'
                    extreme_idx = i
                    extreme_price = low

            elif trend == 'down':
                # In downtrend, track new lows
                if low < extreme_price:
                    extreme_idx = i
                    extreme_price = low
                # Check for reversal
                elif high_change >= self.threshold_pct:
                    # Reversal confirmed - save pivot low
                    pivot_lows.append(PivotPoint(
                        index=extreme_idx,
                        timestamp=df.index[extreme_idx].isoformat(),
                        price=extreme_price,
                        pivot_type='low'
                    ))
                    # Switch to uptrend
                    trend = 'up'
                    extreme_idx = i
                    extreme_price = high

        return pivot_highs, pivot_lows


class AdaptivePivotDetector(WaveDetectorInterface):
    """
    Adaptive pivot detector using ATR-based thresholds.

    Adjusts sensitivity based on market volatility (ATR).
    More lenient in volatile markets, stricter in calm markets.

    Attributes:
        window: Base window for pivot confirmation (default: 5)
        atr_multiplier: ATR multiplier for threshold (default: 1.5)
        atr_period: Period for ATR calculation (default: 14)
    """

    def __init__(self, window: int = 5, atr_multiplier: float = 1.5,
                 atr_period: int = 14):
        """
        Initialize adaptive pivot detector.

        Args:
            window: Base pivot confirmation window
            atr_multiplier: Multiplier for ATR-based threshold
            atr_period: ATR calculation period
        """
        self.window = window
        self.atr_multiplier = atr_multiplier
        self.atr_period = atr_period

    def detect_pivots(self, df: pd.DataFrame) -> Tuple[List[PivotPoint],
                                                        List[PivotPoint]]:
        """
        Detect pivots using ATR-adaptive thresholds.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Tuple of (pivot_highs, pivot_lows)
        """
        # Calculate ATR
        atr = self._calculate_atr(df)

        pivot_highs: List[PivotPoint] = []
        pivot_lows: List[PivotPoint] = []

        # Standard pivot detection
        base_detector = PivotDetector(window=self.window)
        candidate_highs, candidate_lows = base_detector.detect_pivots(df)

        # Filter by ATR threshold
        for pivot in candidate_highs:
            if self._validate_with_atr(pivot, df, atr):
                pivot_highs.append(pivot)

        for pivot in candidate_lows:
            if self._validate_with_atr(pivot, df, atr):
                pivot_lows.append(pivot)

        return pivot_highs, pivot_lows

    def _calculate_atr(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate Average True Range.

        Args:
            df: DataFrame with OHLC data

        Returns:
            ATR series
        """
        high = df['high']
        low = df['low']
        close = df['close']

        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())

        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(window=self.atr_period).mean()

        return atr

    def _validate_with_atr(self, pivot: PivotPoint, df: pd.DataFrame,
                          atr: pd.Series) -> bool:
        """
        Validate pivot against ATR threshold.

        Args:
            pivot: Pivot point to validate
            df: DataFrame with price data
            atr: ATR series

        Returns:
            True if pivot meets ATR threshold
        """
        if pivot.index >= len(atr) or pd.isna(atr.iloc[pivot.index]):
            return True  # Can't validate, accept

        threshold = atr.iloc[pivot.index] * self.atr_multiplier

        # Check if pivot represents significant move
        window_start = max(0, pivot.index - self.window)
        window_end = min(len(df), pivot.index + self.window + 1)

        if pivot.pivot_type == 'high':
            window_low = df.iloc[window_start:window_end]['low'].min()
            move = pivot.price - window_low
        else:  # 'low'
            window_high = df.iloc[window_start:window_end]['high'].max()
            move = window_high - pivot.price

        return move >= threshold
