"""Entities for Market Domain.

Core business objects representing market data.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from src.domain.market.entities.value_objects import Price, Timeframe, TradingPair, Volume


@dataclass
class Candlestick:
    """
    Entity: Represents a price candlestick (OHLCV).

    A candlestick represents price movement within a time period.

    Attributes:
        timestamp: When the candlestick closed
        open_price: Opening price
        high_price: Highest price in period
        low_price: Lowest price in period
        close_price: Closing price
        volume: Trading volume
        timeframe: Trading timeframe
        pair: Trading pair
    """

    timestamp: datetime
    open_price: Price
    high_price: Price
    low_price: Price
    close_price: Price
    volume: Volume
    timeframe: Timeframe
    pair: TradingPair

    def __post_init__(self) -> None:
        """Validate candlestick data."""
        if self.high_price < self.low_price:
            raise ValueError("High price must be >= low price")
        if self.high_price < max(self.open_price, self.close_price):
            raise ValueError("High price must be >= open and close prices")
        if self.low_price > min(self.open_price, self.close_price):
            raise ValueError("Low price must be <= open and close prices")

    def is_bullish(self) -> bool:
        """Check if candlestick is bullish (close > open)."""
        return self.close_price > self.open_price

    def is_bearish(self) -> bool:
        """Check if candlestick is bearish (close < open)."""
        return self.close_price < self.open_price

    def is_doji(self, threshold: float = 0.01) -> bool:
        """Check if candlestick is doji (open ≈ close)."""
        price_range = self.high_price - self.low_price
        if price_range == 0:
            return True
        body = abs(self.close_price - self.open_price)
        return body / price_range < threshold

    def get_body(self) -> Price:
        """Get candlestick body size (absolute price difference)."""
        return Price(abs(self.close_price - self.open_price))

    def get_wick(self) -> Price:
        """Get candlestick wick size (total range)."""
        return Price(self.high_price - self.low_price)

    def get_body_ratio(self) -> float:
        """Get body-to-wick ratio."""
        wick = self.get_wick()
        if wick == 0:
            return 0.0
        return float(self.get_body() / wick)


@dataclass
class MarketData:
    """
    Entity: Aggregated market data for a pair and timeframe.

    Contains multiple candlesticks and metadata.
    """

    pair: TradingPair
    timeframe: Timeframe
    candlesticks: list[Candlestick]
    last_updated: datetime
    source: str = "binance"

    @property
    def latest_candlestick(self) -> Optional[Candlestick]:
        """Get most recent candlestick."""
        return self.candlesticks[-1] if self.candlesticks else None

    @property
    def earliest_candlestick(self) -> Optional[Candlestick]:
        """Get oldest candlestick."""
        return self.candlesticks[0] if self.candlesticks else None

    def get_candles_count(self) -> int:
        """Get number of candlesticks."""
        return len(self.candlesticks)

    def has_recent_data(self, max_age_hours: int = 24) -> bool:
        """Check if data is recent."""
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        return self.last_updated > cutoff
