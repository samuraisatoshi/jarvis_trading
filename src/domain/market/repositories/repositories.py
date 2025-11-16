"""Repository interfaces for Market Domain.

Abstracts data access layer for market data.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from src.domain.market.entities import Candlestick, MarketData
from src.domain.market.entities.value_objects import Timeframe, TradingPair


class CandlestickRepository(ABC):
    """Repository: Abstracted access to candlestick data."""

    @abstractmethod
    def save(self, candlestick: Candlestick) -> None:
        """Save a single candlestick."""
        pass

    @abstractmethod
    def find_by_timestamp(
        self, pair: TradingPair, timeframe: Timeframe, timestamp: datetime
    ) -> Optional[Candlestick]:
        """Find candlestick by timestamp."""
        pass

    @abstractmethod
    def find_range(
        self,
        pair: TradingPair,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
    ) -> list[Candlestick]:
        """Find candlesticks in time range."""
        pass

    @abstractmethod
    def find_latest(
        self, pair: TradingPair, timeframe: Timeframe, limit: int = 100
    ) -> list[Candlestick]:
        """Find latest candlesticks."""
        pass

    @abstractmethod
    def delete_before(self, pair: TradingPair, before: datetime) -> int:
        """Delete candlesticks before timestamp (for cache cleanup)."""
        pass


class MarketDataRepository(ABC):
    """Repository: Abstracted access to aggregated market data."""

    @abstractmethod
    def save(self, market_data: MarketData) -> None:
        """Save market data."""
        pass

    @abstractmethod
    def find(self, pair: TradingPair, timeframe: Timeframe) -> Optional[MarketData]:
        """Find market data for pair and timeframe."""
        pass

    @abstractmethod
    def update_timestamp(self, pair: TradingPair, timeframe: Timeframe) -> None:
        """Update last_updated timestamp."""
        pass

    @abstractmethod
    def exists(self, pair: TradingPair, timeframe: Timeframe) -> bool:
        """Check if market data exists."""
        pass

    @abstractmethod
    def delete(self, pair: TradingPair, timeframe: Timeframe) -> None:
        """Delete market data."""
        pass
