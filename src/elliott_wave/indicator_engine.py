"""
Technical indicator engine for Elliott Wave confirmation.

This module provides technical indicators that complement Elliott Wave analysis.
Indicators help confirm or reject wave patterns.

SOLID Principles:
- Single Responsibility: Each indicator class handles ONE indicator
- Open/Closed: Extendable through IndicatorInterface
- Liskov Substitution: All indicators interchangeable
- Interface Segregation: Small, focused indicator interfaces

Design Pattern: Strategy Pattern for different indicators
"""

from abc import ABC, abstractmethod
from typing import Tuple
import pandas as pd
import numpy as np
from .models import TechnicalIndicators, MomentumType, VolumeTrend


class IndicatorInterface(ABC):
    """Abstract interface for technical indicators."""

    @abstractmethod
    def calculate(self, df: pd.DataFrame) -> float:
        """
        Calculate indicator value.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Calculated indicator value
        """
        pass


class RSIIndicator(IndicatorInterface):
    """
    Relative Strength Index (RSI) indicator.

    Measures momentum and identifies overbought/oversold conditions.

    Attributes:
        period: RSI calculation period (default: 14)
    """

    def __init__(self, period: int = 14):
        """
        Initialize RSI indicator.

        Args:
            period: Lookback period for RSI calculation
        """
        self.period = period

    def calculate(self, df: pd.DataFrame) -> float:
        """
        Calculate RSI for the most recent data point.

        Args:
            df: DataFrame with 'close' column

        Returns:
            RSI value (0-100)
        """
        prices = df['close']
        return self.calculate_series(prices).iloc[-1]

    def calculate_series(self, prices: pd.Series) -> pd.Series:
        """
        Calculate RSI series.

        Args:
            prices: Price series

        Returns:
            RSI series (0-100)
        """
        delta = prices.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(window=self.period).mean()
        avg_loss = loss.rolling(window=self.period).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi


class MACDIndicator(IndicatorInterface):
    """
    Moving Average Convergence Divergence (MACD) indicator.

    Identifies trend changes and momentum.

    Attributes:
        fast_period: Fast EMA period (default: 12)
        slow_period: Slow EMA period (default: 26)
        signal_period: Signal line EMA period (default: 9)
    """

    def __init__(self, fast_period: int = 12, slow_period: int = 26,
                 signal_period: int = 9):
        """
        Initialize MACD indicator.

        Args:
            fast_period: Fast EMA period
            slow_period: Slow EMA period
            signal_period: Signal line period
        """
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period

    def calculate(self, df: pd.DataFrame) -> float:
        """
        Calculate MACD histogram for most recent data.

        Args:
            df: DataFrame with 'close' column

        Returns:
            MACD histogram value
        """
        _, _, histogram = self.calculate_all(df['close'])
        return histogram.iloc[-1]

    def calculate_all(self, prices: pd.Series) -> Tuple[pd.Series,
                                                         pd.Series,
                                                         pd.Series]:
        """
        Calculate MACD, signal line, and histogram.

        Args:
            prices: Price series

        Returns:
            Tuple of (macd, signal, histogram) series
        """
        ema_fast = prices.ewm(span=self.fast_period, adjust=False).mean()
        ema_slow = prices.ewm(span=self.slow_period, adjust=False).mean()

        macd = ema_fast - ema_slow
        signal = macd.ewm(span=self.signal_period, adjust=False).mean()
        histogram = macd - signal

        return macd, signal, histogram


class VolumeAnalyzer:
    """
    Volume trend analyzer.

    Analyzes volume patterns to confirm price movements.

    Attributes:
        short_window: Short-term volume average window (default: 10)
        long_window: Long-term volume average window (default: 30)
        threshold: Threshold for significant change (default: 10%)
    """

    def __init__(self, short_window: int = 10, long_window: int = 30,
                 threshold: float = 10.0):
        """
        Initialize volume analyzer.

        Args:
            short_window: Recent volume period
            long_window: Baseline volume period
            threshold: % change threshold for trend classification
        """
        self.short_window = short_window
        self.long_window = long_window
        self.threshold = threshold

    def analyze(self, df: pd.DataFrame) -> VolumeTrend:
        """
        Analyze volume trend.

        Args:
            df: DataFrame with 'volume' column

        Returns:
            VolumeTrend enum (INCREASING, DECREASING, NEUTRAL)
        """
        recent_volume = df['volume'].iloc[-self.short_window:].mean()
        baseline_volume = df['volume'].iloc[-self.long_window:].mean()

        if baseline_volume == 0:
            return VolumeTrend.NEUTRAL

        change_pct = ((recent_volume - baseline_volume) / baseline_volume
                     ) * 100

        if change_pct > self.threshold:
            return VolumeTrend.INCREASING
        elif change_pct < -self.threshold:
            return VolumeTrend.DECREASING
        else:
            return VolumeTrend.NEUTRAL

    def is_climactic(self, df: pd.DataFrame, multiplier: float = 2.0) -> bool:
        """
        Check if current volume is climactic (unusually high).

        Args:
            df: DataFrame with 'volume' column
            multiplier: Multiplier of average for climactic (default: 2.0)

        Returns:
            True if volume is climactic
        """
        current_volume = df['volume'].iloc[-1]
        avg_volume = df['volume'].iloc[-self.long_window:].mean()

        return current_volume > avg_volume * multiplier


class MomentumAnalyzer:
    """
    Momentum analyzer combining RSI and MACD.

    Provides overall momentum classification for wave confirmation.

    Attributes:
        rsi_oversold: RSI threshold for oversold (default: 40)
        rsi_overbought: RSI threshold for overbought (default: 60)
    """

    def __init__(self, rsi_oversold: float = 40, rsi_overbought: float = 60):
        """
        Initialize momentum analyzer.

        Args:
            rsi_oversold: RSI level for bearish momentum
            rsi_overbought: RSI level for bullish momentum
        """
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought

    def analyze(self, rsi: float, macd_histogram: float) -> MomentumType:
        """
        Analyze overall momentum.

        Args:
            rsi: RSI value
            macd_histogram: MACD histogram value

        Returns:
            MomentumType enum (BULLISH, BEARISH, NEUTRAL)
        """
        bullish_signals = 0
        bearish_signals = 0

        # RSI signals
        if rsi > self.rsi_overbought:
            bullish_signals += 1
        elif rsi < self.rsi_oversold:
            bearish_signals += 1

        # MACD signals
        if macd_histogram > 0:
            bullish_signals += 1
        elif macd_histogram < 0:
            bearish_signals += 1

        if bullish_signals > bearish_signals:
            return MomentumType.BULLISH
        elif bearish_signals > bullish_signals:
            return MomentumType.BEARISH
        else:
            return MomentumType.NEUTRAL


class IndicatorEngine:
    """
    Central engine coordinating all technical indicators.

    Aggregates individual indicators into TechnicalIndicators model.
    """

    def __init__(self):
        """Initialize indicator engine with default indicators."""
        self.rsi_indicator = RSIIndicator(period=14)
        self.macd_indicator = MACDIndicator(fast=12, slow=26, signal=9)
        self.volume_analyzer = VolumeAnalyzer(short=10, long=30)
        self.momentum_analyzer = MomentumAnalyzer(oversold=40, overbought=60)

    def calculate_all(self, df: pd.DataFrame) -> TechnicalIndicators:
        """
        Calculate all indicators for the DataFrame.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            TechnicalIndicators model with all values
        """
        # Calculate RSI
        rsi = self.rsi_indicator.calculate(df)

        # Calculate MACD
        macd, macd_signal, macd_histogram = self.macd_indicator.calculate_all(
            df['close']
        )

        # Analyze volume
        volume_trend = self.volume_analyzer.analyze(df)

        # Analyze momentum
        momentum = self.momentum_analyzer.analyze(rsi, macd_histogram.iloc[-1])

        return TechnicalIndicators(
            rsi=rsi,
            macd=macd.iloc[-1],
            macd_signal=macd_signal.iloc[-1],
            macd_histogram=macd_histogram.iloc[-1],
            volume_trend=volume_trend,
            momentum=momentum
        )

    def configure_rsi(self, period: int) -> None:
        """Configure RSI period."""
        self.rsi_indicator = RSIIndicator(period=period)

    def configure_macd(self, fast: int, slow: int, signal: int) -> None:
        """Configure MACD periods."""
        self.macd_indicator = MACDIndicator(fast, slow, signal)

    def configure_volume(self, short: int, long: int, threshold: float
                        ) -> None:
        """Configure volume analyzer."""
        self.volume_analyzer = VolumeAnalyzer(short, long, threshold)

    def configure_momentum(self, oversold: float, overbought: float) -> None:
        """Configure momentum thresholds."""
        self.momentum_analyzer = MomentumAnalyzer(oversold, overbought)
