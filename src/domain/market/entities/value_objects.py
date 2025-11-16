"""Value Objects for Market Domain.

Immutable value types representing fundamental market concepts.
"""

from enum import Enum
from typing import Literal


class Timeframe(Enum):
    """Value Object: Trading timeframe."""

    ONE_MINUTE = "1m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    ONE_HOUR = "1h"
    FOUR_HOURS = "4h"
    ONE_DAY = "1d"
    ONE_WEEK = "1w"

    def to_seconds(self) -> int:
        """Convert timeframe to seconds."""
        mapping = {
            "1m": 60,
            "5m": 300,
            "15m": 900,
            "1h": 3600,
            "4h": 14400,
            "1d": 86400,
            "1w": 604800,
        }
        return mapping[self.value]

    def to_binance_format(self) -> str:
        """Get Binance API format."""
        return self.value


class Price(float):
    """Value Object: Price."""

    def __new__(cls, value: float) -> "Price":
        if value < 0:
            raise ValueError("Price cannot be negative")
        return super().__new__(cls, value)


class Volume(float):
    """Value Object: Trading volume."""

    def __new__(cls, value: float) -> "Volume":
        if value < 0:
            raise ValueError("Volume cannot be negative")
        return super().__new__(cls, value)


class TradingPair(str):
    """Value Object: Trading pair (e.g., BTCUSDT)."""

    def __new__(cls, value: str) -> "TradingPair":
        if not value or len(value) < 6:
            raise ValueError("Invalid trading pair format")
        return super().__new__(cls, value.upper())

    @property
    def base_asset(self) -> str:
        """Get base asset (e.g., BTC from BTCUSDT)."""
        # This is a simplified version; real implementation would be more robust
        return self[:3]

    @property
    def quote_asset(self) -> str:
        """Get quote asset (e.g., USDT from BTCUSDT)."""
        return self[3:]
