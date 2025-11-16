"""
Data models for Elliott Wave analysis.

This module defines core data structures used throughout the Elliott Wave system.
All models are immutable dataclasses for thread-safety and predictability.

SOLID Principles:
- Single Responsibility: Each class represents ONE concept
- Open/Closed: Extensible through inheritance
- Liskov Substitution: Subtypes can replace base types
- Interface Segregation: Small, focused data models
"""

from dataclasses import dataclass, asdict, field
from typing import Optional, List, Dict
from enum import Enum


class WaveType(Enum):
    """Elliott Wave pattern types."""
    IMPULSIVE = 'impulsive'
    CORRECTIVE = 'corrective'
    UNKNOWN = 'unknown'


class WavePosition(Enum):
    """Position within wave structure."""
    WAVE_1 = '1'
    WAVE_2 = '2'
    WAVE_3 = '3'
    WAVE_4 = '4'
    WAVE_5 = '5'
    WAVE_A = 'A'
    WAVE_B = 'B'
    WAVE_C = 'C'
    UNKNOWN = '?'


class SignalAction(Enum):
    """Trading signal actions."""
    BUY = 'BUY'
    SELL = 'SELL'
    HOLD = 'HOLD'


class MomentumType(Enum):
    """Market momentum types."""
    BULLISH = 'bullish'
    BEARISH = 'bearish'
    NEUTRAL = 'neutral'


class VolumeTrend(Enum):
    """Volume trend types."""
    INCREASING = 'increasing'
    DECREASING = 'decreasing'
    NEUTRAL = 'neutral'


@dataclass
class PivotPoint:
    """
    Pivot point (swing high/low) in price action.

    Attributes:
        index: Position in the DataFrame
        timestamp: ISO format timestamp
        price: Price at the pivot
        pivot_type: 'high' or 'low'
    """
    index: int
    timestamp: str
    price: float
    pivot_type: str  # 'high' or 'low'

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return asdict(self)


@dataclass
class FibonacciLevels:
    """
    Fibonacci retracement and extension levels.

    Calculated from a wave movement (start to end price).
    Used for identifying potential support/resistance and targets.

    Attributes:
        level_0: 0% retracement (wave start)
        level_236: 23.6% retracement
        level_382: 38.2% retracement
        level_500: 50% retracement
        level_618: 61.8% retracement (Golden Ratio)
        level_786: 78.6% retracement
        level_100: 100% retracement (wave end)
        level_1618: 161.8% extension
        level_2618: 261.8% extension
    """
    level_0: float
    level_236: float
    level_382: float
    level_500: float
    level_618: float
    level_786: float
    level_100: float
    level_1618: float
    level_2618: float

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return asdict(self)

    def get_level(self, percentage: float) -> Optional[float]:
        """
        Get level by percentage.

        Args:
            percentage: Fibonacci percentage (e.g., 61.8)

        Returns:
            Price level or None if not found
        """
        mapping = {
            0.0: self.level_0,
            23.6: self.level_236,
            38.2: self.level_382,
            50.0: self.level_500,
            61.8: self.level_618,
            78.6: self.level_786,
            100.0: self.level_100,
            161.8: self.level_1618,
            261.8: self.level_2618
        }
        return mapping.get(percentage)


@dataclass
class WavePattern:
    """
    Identified Elliott Wave pattern.

    Represents the current wave structure and confidence level.

    Attributes:
        wave_type: Type of wave (impulsive/corrective)
        current_wave: Current wave position (1-5 or A-B-C)
        confidence: Confidence level (0-100%)
        start_price: Price at wave start
        current_price: Current market price
        projected_target: Projected price target (if calculable)
        invalidation_level: Price level that invalidates pattern
    """
    wave_type: WaveType
    current_wave: WavePosition
    confidence: float
    start_price: float
    current_price: float
    projected_target: Optional[float] = None
    invalidation_level: Optional[float] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        # Convert enums to their values
        data['wave_type'] = self.wave_type.value
        data['current_wave'] = self.current_wave.value
        return data

    def is_impulsive(self) -> bool:
        """Check if pattern is impulsive."""
        return self.wave_type == WaveType.IMPULSIVE

    def is_corrective(self) -> bool:
        """Check if pattern is corrective."""
        return self.wave_type == WaveType.CORRECTIVE

    def is_confident(self, threshold: float = 70.0) -> bool:
        """
        Check if confidence exceeds threshold.

        Args:
            threshold: Minimum confidence percentage (default 70%)

        Returns:
            True if confidence >= threshold
        """
        return self.confidence >= threshold


@dataclass
class TechnicalIndicators:
    """
    Technical indicators for wave confirmation.

    Provides complementary indicators to validate Elliott Wave patterns.

    Attributes:
        rsi: Relative Strength Index (0-100)
        macd: MACD line value
        macd_signal: MACD signal line value
        macd_histogram: MACD histogram value
        volume_trend: Volume trend classification
        momentum: Overall momentum classification
    """
    rsi: float
    macd: float
    macd_signal: float
    macd_histogram: float
    volume_trend: VolumeTrend
    momentum: MomentumType

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        # Convert enums to their values
        data['volume_trend'] = self.volume_trend.value
        data['momentum'] = self.momentum.value
        return data

    def is_oversold(self, threshold: float = 30.0) -> bool:
        """Check if RSI indicates oversold condition."""
        return self.rsi < threshold

    def is_overbought(self, threshold: float = 70.0) -> bool:
        """Check if RSI indicates overbought condition."""
        return self.rsi > threshold

    def has_bullish_macd(self) -> bool:
        """Check if MACD shows bullish signal."""
        return self.macd > self.macd_signal and self.macd_histogram > 0

    def has_bearish_macd(self) -> bool:
        """Check if MACD shows bearish signal."""
        return self.macd < self.macd_signal and self.macd_histogram < 0


@dataclass
class TradingSignal:
    """
    Trading signal with risk management.

    Generated from Elliott Wave analysis and technical indicators.
    Includes complete risk management parameters.

    Attributes:
        action: Trading action to take (BUY/SELL/HOLD)
        confidence: Signal confidence (0-100%)
        entry_price: Suggested entry price
        stop_loss: Stop loss price level
        take_profit_1: First take profit target
        take_profit_2: Second take profit target
        take_profit_3: Third take profit target
        risk_reward_ratio: Risk/Reward ratio (reward / risk)
        reasoning: Human-readable explanation
    """
    action: SignalAction
    confidence: float
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    take_profit_3: float
    risk_reward_ratio: float
    reasoning: str

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['action'] = self.action.value
        return data

    def is_actionable(self, min_confidence: float = 60.0,
                     min_risk_reward: float = 1.5) -> bool:
        """
        Check if signal meets minimum thresholds for action.

        Args:
            min_confidence: Minimum confidence percentage
            min_risk_reward: Minimum risk/reward ratio

        Returns:
            True if signal meets both thresholds
        """
        return (self.confidence >= min_confidence and
                self.risk_reward_ratio >= min_risk_reward and
                self.action != SignalAction.HOLD)

    def get_risk_amount(self) -> float:
        """Calculate risk amount per unit."""
        return abs(self.entry_price - self.stop_loss)

    def get_reward_amount(self, target_level: int = 2) -> float:
        """
        Calculate reward amount for specified target.

        Args:
            target_level: Which take profit level (1, 2, or 3)

        Returns:
            Reward amount per unit
        """
        targets = {
            1: self.take_profit_1,
            2: self.take_profit_2,
            3: self.take_profit_3
        }
        target_price = targets.get(target_level, self.take_profit_2)
        return abs(target_price - self.entry_price)


@dataclass
class WaveAnalysis:
    """
    Complete Elliott Wave analysis for a single timeframe.

    Aggregates all analysis components into a single structure.

    Attributes:
        timeframe: Candle timeframe (e.g., '4h', '1d')
        current_price: Current market price
        wave_pattern: Identified wave pattern
        fibonacci_levels: Calculated Fibonacci levels
        indicators: Technical indicators
        signal: Generated trading signal
        pivot_highs: Recent pivot highs
        pivot_lows: Recent pivot lows
        timestamp: Analysis timestamp (ISO format)
    """
    timeframe: str
    current_price: float
    wave_pattern: WavePattern
    fibonacci_levels: FibonacciLevels
    indicators: TechnicalIndicators
    signal: TradingSignal
    pivot_highs: List[PivotPoint] = field(default_factory=list)
    pivot_lows: List[PivotPoint] = field(default_factory=list)
    timestamp: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'timeframe': self.timeframe,
            'current_price': self.current_price,
            'wave_pattern': self.wave_pattern.to_dict(),
            'fibonacci_levels': self.fibonacci_levels.to_dict(),
            'indicators': self.indicators.to_dict(),
            'signal': self.signal.to_dict(),
            'pivot_highs': [p.to_dict() for p in self.pivot_highs],
            'pivot_lows': [p.to_dict() for p in self.pivot_lows],
            'timestamp': self.timestamp
        }

    def get_key_levels(self) -> List[float]:
        """
        Get key price levels (Fibonacci + invalidation).

        Returns:
            Sorted list of key price levels
        """
        levels = [
            self.fibonacci_levels.level_618,
            self.fibonacci_levels.level_500,
            self.fibonacci_levels.level_382,
            self.fibonacci_levels.level_1618,
        ]
        if self.wave_pattern.invalidation_level:
            levels.append(self.wave_pattern.invalidation_level)

        return sorted(set(levels))
