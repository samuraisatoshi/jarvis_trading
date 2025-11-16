"""
Data models for trading strategies.

This module defines data structures used by trading strategies to represent
signals, trends, levels, and other strategy-specific data.

SOLID Principles:
- Single Responsibility: Only defines data structures
- Open/Closed: Can add new models without modifying existing ones
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class TrendType(Enum):
    """Market trend classification."""
    UPTREND = "UPTREND"
    DOWNTREND = "DOWNTREND"
    LATERAL = "LATERAL"
    UNKNOWN = "UNKNOWN"


class SignalType(Enum):
    """Trading signal action types."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class ConfirmationSignal(Enum):
    """Types of confirmation signals for trade validation."""
    # RSI signals
    RSI_BULLISH_DIVERGENCE = "RSI_BULLISH_DIVERGENCE"
    RSI_BEARISH_DIVERGENCE = "RSI_BEARISH_DIVERGENCE"
    RSI_OVERSOLD = "RSI_OVERSOLD"
    RSI_OVERBOUGHT = "RSI_OVERBOUGHT"

    # Volume signals
    VOLUME_SPIKE = "VOLUME_SPIKE"
    VOLUME_DECLINE = "VOLUME_DECLINE"

    # Candlestick patterns (bullish)
    BULLISH_ENGULFING = "BULLISH_ENGULFING"
    HAMMER = "HAMMER"
    MORNING_STAR = "MORNING_STAR"

    # Candlestick patterns (bearish)
    BEARISH_ENGULFING = "BEARISH_ENGULFING"
    SHOOTING_STAR = "SHOOTING_STAR"
    EVENING_STAR = "EVENING_STAR"

    # Moving average signals
    GOLDEN_CROSS = "GOLDEN_CROSS"
    DEATH_CROSS = "DEATH_CROSS"


@dataclass
class FibonacciLevels:
    """
    Fibonacci retracement and extension levels.

    These levels are used to identify potential support/resistance areas
    and price targets based on Fibonacci ratios.

    Attributes:
        high: Swing high price
        low: Swing low price
        level_0236: 23.6% retracement
        level_0382: 38.2% retracement
        level_0500: 50% retracement (Golden Zone start)
        level_0618: 61.8% retracement (Golden Zone end)
        level_0786: 78.6% retracement (stop loss level)
        level_1000: 100% retracement (back to swing low/high)
        level_1618: 161.8% extension (target 1)
        level_2618: 261.8% extension (target 2)
        is_uptrend: True if calculated for uptrend, False for downtrend
    """
    high: float
    low: float
    level_0236: float
    level_0382: float
    level_0500: float
    level_0618: float
    level_0786: float
    level_1000: float
    level_1618: float
    level_2618: float
    is_uptrend: bool

    @property
    def golden_zone_min(self) -> float:
        """Lower bound of Golden Zone (61.8%)."""
        return self.level_0618

    @property
    def golden_zone_max(self) -> float:
        """Upper bound of Golden Zone (50%)."""
        return self.level_0500

    def is_in_golden_zone(self, price: float) -> bool:
        """
        Check if price is within Golden Zone (50%-61.8%).

        Args:
            price: Current price to check

        Returns:
            True if price is in Golden Zone, False otherwise
        """
        if self.is_uptrend:
            # Golden Zone: 61.8% <= price <= 50%
            return self.golden_zone_min <= price <= self.golden_zone_max
        else:
            # Golden Zone: 50% <= price <= 61.8%
            return self.golden_zone_max <= price <= self.golden_zone_min

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for compatibility with existing code."""
        return {
            'high': self.high,
            'low': self.low,
            '0.236': self.level_0236,
            '0.382': self.level_0382,
            '0.500': self.level_0500,
            '0.618': self.level_0618,
            '0.786': self.level_0786,
            '1.000': self.level_1000,
            '1.618': self.level_1618,
            '2.618': self.level_2618,
        }


@dataclass
class TradeSignal:
    """
    Complete trading signal with all necessary information.

    This dataclass encapsulates all information needed to execute a trade,
    including entry, exits, metadata, and reasoning.

    Attributes:
        action: BUY, SELL, or HOLD
        reason: Human-readable explanation
        current_price: Current market price
        trend: Market trend context
        entry: Entry price (None for HOLD)
        stop_loss: Stop loss price (None for HOLD)
        take_profit_1: First take profit target (None for HOLD)
        take_profit_2: Second take profit target (None for HOLD)
        confirmations: List of confirmation signal names
        confidence: Confidence score 0-1
        metadata: Additional strategy-specific data
    """
    action: SignalType
    reason: str
    current_price: float
    trend: TrendType
    entry: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit_1: Optional[float] = None
    take_profit_2: Optional[float] = None
    confirmations: List[str] = field(default_factory=list)
    confidence: Optional[float] = None
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """
        Convert signal to dictionary format.

        This maintains backward compatibility with existing code that expects
        dictionary-based signals.

        Returns:
            Dictionary representation of the signal
        """
        result = {
            'action': self.action.value if isinstance(self.action, SignalType) else self.action,
            'reason': self.reason,
            'current_price': self.current_price,
            'trend': self.trend.value if isinstance(self.trend, TrendType) else self.trend,
        }

        # Add trading parameters if present
        if self.entry is not None:
            result['entry'] = self.entry
        if self.stop_loss is not None:
            result['stop_loss'] = self.stop_loss
        if self.take_profit_1 is not None:
            result['take_profit_1'] = self.take_profit_1
        if self.take_profit_2 is not None:
            result['take_profit_2'] = self.take_profit_2

        # Add optional fields
        if self.confirmations:
            result['confirmations'] = self.confirmations
        if self.confidence is not None:
            result['confidence'] = self.confidence
        if self.metadata:
            result['metadata'] = self.metadata

        return result

    @classmethod
    def from_dict(cls, data: Dict) -> 'TradeSignal':
        """
        Create TradeSignal from dictionary.

        Args:
            data: Dictionary containing signal data

        Returns:
            TradeSignal instance
        """
        # Convert string action to enum if needed
        action = data['action']
        if isinstance(action, str):
            action = SignalType[action]

        # Convert string trend to enum if needed
        trend = data.get('trend', 'UNKNOWN')
        if isinstance(trend, str):
            trend = TrendType[trend]

        return cls(
            action=action,
            reason=data['reason'],
            current_price=data['current_price'],
            trend=trend,
            entry=data.get('entry'),
            stop_loss=data.get('stop_loss'),
            take_profit_1=data.get('take_profit_1'),
            take_profit_2=data.get('take_profit_2'),
            confirmations=data.get('confirmations', []),
            confidence=data.get('confidence'),
            metadata=data.get('metadata', {}),
        )

    def is_actionable(self) -> bool:
        """
        Check if signal is actionable (BUY or SELL with complete parameters).

        Returns:
            True if signal can be acted upon, False otherwise
        """
        if self.action == SignalType.HOLD:
            return False

        # For BUY/SELL, we need entry and at least stop_loss
        return (
            self.entry is not None and
            self.stop_loss is not None
        )


@dataclass
class SwingPoint:
    """
    Swing high or low point in price action.

    Attributes:
        timestamp: When the swing occurred
        price: Price at the swing point
        is_high: True for swing high, False for swing low
        index: Index position in the DataFrame
    """
    timestamp: str
    price: float
    is_high: bool
    index: int
