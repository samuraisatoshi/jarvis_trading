"""
Domain models for multi-asset trading daemon.

Pure domain entities with no infrastructure dependencies.
All models use dataclasses for immutability and type safety.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List
from datetime import datetime
from enum import Enum


class SignalAction(Enum):
    """Trading signal action types."""
    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True)
class Signal:
    """
    Trading signal domain model.

    Represents a detected trading opportunity with all context
    needed for execution decision.
    """
    symbol: str
    timeframe: str
    action: SignalAction
    price: float
    ma: float
    distance: float
    threshold: float
    reason: str
    timestamp: datetime

    def __str__(self) -> str:
        """Human-readable signal representation."""
        return (
            f"{self.action.value} {self.symbol} @ ${self.price:.2f} "
            f"({self.timeframe}): {self.reason}"
        )

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'action': self.action.value,
            'price': self.price,
            'ma': self.ma,
            'distance': self.distance,
            'threshold': self.threshold,
            'reason': self.reason,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class Position:
    """
    Asset position domain model.

    Represents current holdings of a specific asset.
    """
    symbol: str
    currency: str
    quantity: float
    average_price: Optional[float] = None

    def get_value(self, current_price: float) -> float:
        """
        Calculate position value at current price.

        Args:
            current_price: Current market price

        Returns:
            Total position value in quote currency (USD)
        """
        return self.quantity * current_price

    def get_profit_loss(self, current_price: float) -> Optional[float]:
        """
        Calculate unrealized profit/loss.

        Args:
            current_price: Current market price

        Returns:
            P&L in USD, or None if average_price not available
        """
        if self.average_price is None:
            return None

        return (current_price - self.average_price) * self.quantity

    def get_profit_loss_percent(self, current_price: float) -> Optional[float]:
        """
        Calculate unrealized profit/loss percentage.

        Args:
            current_price: Current market price

        Returns:
            P&L percentage, or None if average_price not available
        """
        if self.average_price is None:
            return None

        return ((current_price - self.average_price) / self.average_price) * 100


@dataclass
class PortfolioStatus:
    """
    Portfolio status snapshot.

    Captures complete portfolio state at a point in time.
    """
    total_value: float
    usdt_balance: float
    positions: List[Position]
    timestamp: datetime

    @property
    def num_positions(self) -> int:
        """Number of open positions."""
        return len(self.positions)

    @property
    def invested_value(self) -> float:
        """Total value invested in positions (excludes USDT)."""
        return self.total_value - self.usdt_balance

    @property
    def allocation_percent(self) -> float:
        """Percentage of capital allocated to positions."""
        if self.total_value == 0:
            return 0.0
        return (self.invested_value / self.total_value) * 100

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'total_value': self.total_value,
            'usdt_balance': self.usdt_balance,
            'invested_value': self.invested_value,
            'allocation_percent': self.allocation_percent,
            'num_positions': self.num_positions,
            'positions': [
                {
                    'symbol': p.symbol,
                    'currency': p.currency,
                    'quantity': p.quantity,
                    'average_price': p.average_price
                }
                for p in self.positions
            ],
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class TradeResult:
    """
    Trade execution result.

    Contains outcome of trade execution attempt with all relevant details.
    """
    success: bool
    signal: Signal
    quantity: Optional[float] = None
    total_value: Optional[float] = None
    order_id: Optional[str] = None
    error: Optional[str] = None

    def __str__(self) -> str:
        """Human-readable result representation."""
        if self.success:
            return (
                f"✅ {self.signal.action.value} {self.quantity:.6f} "
                f"{self.signal.symbol} @ ${self.signal.price:.2f} = "
                f"${self.total_value:.2f} (Order: {self.order_id})"
            )
        else:
            return (
                f"❌ {self.signal.action.value} {self.signal.symbol} FAILED: "
                f"{self.error}"
            )

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'success': self.success,
            'signal': self.signal.to_dict(),
            'quantity': self.quantity,
            'total_value': self.total_value,
            'order_id': self.order_id,
            'error': self.error
        }


@dataclass
class DaemonConfig:
    """
    Daemon configuration model.

    Centralizes all daemon operational parameters.
    """
    timeframes: List[str] = field(default_factory=lambda: ['1h', '4h', '1d'])
    check_interval: int = 3600  # seconds between full checks
    position_sizes: Dict[str, float] = field(
        default_factory=lambda: {'1h': 0.1, '4h': 0.2, '1d': 0.3}
    )
    min_check_intervals: Dict[str, int] = field(
        default_factory=lambda: {'1h': 300, '4h': 1200, '1d': 3600}
    )
    min_trade_value: float = 10.0  # Minimum trade size in USD
    status_report_interval: int = 6  # hours between status reports

    def validate(self) -> None:
        """
        Validate configuration parameters.

        Raises:
            ValueError: If configuration is invalid
        """
        if not self.timeframes:
            raise ValueError("At least one timeframe required")

        for tf in self.timeframes:
            if tf not in self.position_sizes:
                raise ValueError(
                    f"Position size not defined for timeframe: {tf}"
                )

        if sum(self.position_sizes.values()) > 1.0:
            raise ValueError(
                "Total position sizes exceed 100% of capital"
            )

        if self.min_trade_value <= 0:
            raise ValueError("Minimum trade value must be positive")

    def get_position_size_percent(self, timeframe: str) -> float:
        """
        Get position size allocation for timeframe.

        Args:
            timeframe: Timeframe identifier

        Returns:
            Allocation percentage (0.0-1.0)
        """
        return self.position_sizes.get(timeframe, 0.1)

    def get_min_check_interval(self, timeframe: str) -> int:
        """
        Get minimum check interval for timeframe.

        Args:
            timeframe: Timeframe identifier

        Returns:
            Minimum seconds between checks
        """
        return self.min_check_intervals.get(timeframe, 600)
