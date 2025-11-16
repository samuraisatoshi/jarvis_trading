"""Unit tests for Market domain entities."""

from datetime import datetime

import pytest

from src.domain.market.entities import Candlestick, MarketData
from src.domain.market.entities.value_objects import Price, Timeframe, TradingPair, Volume


class TestCandlestick:
    """Tests for Candlestick entity."""

    def setup_method(self) -> None:
        """Setup test data."""
        self.timestamp = datetime.utcnow()
        self.pair = TradingPair("BTCUSDT")
        self.timeframe = Timeframe.ONE_HOUR

    def create_candlestick(
        self,
        open_price: float = 100.0,
        high_price: float = 105.0,
        low_price: float = 95.0,
        close_price: float = 102.0,
        volume: float = 1000.0,
    ) -> Candlestick:
        """Helper to create candlestick."""
        return Candlestick(
            timestamp=self.timestamp,
            open_price=Price(open_price),
            high_price=Price(high_price),
            low_price=Price(low_price),
            close_price=Price(close_price),
            volume=Volume(volume),
            timeframe=self.timeframe,
            pair=self.pair,
        )

    def test_candlestick_creation(self) -> None:
        """Test candlestick creation."""
        candle = self.create_candlestick()
        assert candle.pair == self.pair
        assert candle.timeframe == self.timeframe

    def test_candlestick_validation_high_low(self) -> None:
        """Test candlestick validates high >= low."""
        with pytest.raises(ValueError):
            self.create_candlestick(high_price=90.0, low_price=100.0)

    def test_candlestick_is_bullish(self) -> None:
        """Test bullish candlestick detection."""
        candle = self.create_candlestick(open_price=100.0, close_price=105.0)
        assert candle.is_bullish()

    def test_candlestick_is_bearish(self) -> None:
        """Test bearish candlestick detection."""
        candle = self.create_candlestick(open_price=100.0, close_price=95.0)
        assert candle.is_bearish()

    def test_candlestick_is_doji(self) -> None:
        """Test doji candlestick detection."""
        candle = self.create_candlestick(open_price=100.0, close_price=100.01)
        assert candle.is_doji()

    def test_candlestick_body(self) -> None:
        """Test candlestick body calculation."""
        candle = self.create_candlestick(open_price=100.0, close_price=105.0)
        assert candle.get_body() == Price(5.0)

    def test_candlestick_wick(self) -> None:
        """Test candlestick wick calculation."""
        candle = self.create_candlestick(
            high_price=110.0, low_price=95.0, open_price=100.0, close_price=105.0
        )
        assert candle.get_wick() == Price(15.0)


class TestMarketData:
    """Tests for MarketData entity."""

    def setup_method(self) -> None:
        """Setup test data."""
        self.pair = TradingPair("BTCUSDT")
        self.timeframe = Timeframe.ONE_HOUR
        self.timestamp = datetime.utcnow()

    def create_candlestick(self) -> Candlestick:
        """Helper to create candlestick."""
        return Candlestick(
            timestamp=self.timestamp,
            open_price=Price(100.0),
            high_price=Price(105.0),
            low_price=Price(95.0),
            close_price=Price(102.0),
            volume=Volume(1000.0),
            timeframe=self.timeframe,
            pair=self.pair,
        )

    def test_market_data_creation(self) -> None:
        """Test market data creation."""
        candles = [self.create_candlestick()]
        market_data = MarketData(
            pair=self.pair,
            timeframe=self.timeframe,
            candlesticks=candles,
            last_updated=self.timestamp,
        )
        assert market_data.pair == self.pair
        assert market_data.get_candles_count() == 1

    def test_market_data_latest_candlestick(self) -> None:
        """Test getting latest candlestick."""
        candles = [self.create_candlestick()]
        market_data = MarketData(
            pair=self.pair,
            timeframe=self.timeframe,
            candlesticks=candles,
            last_updated=self.timestamp,
        )
        assert market_data.latest_candlestick == candles[0]

    def test_market_data_empty_latest(self) -> None:
        """Test empty market data returns None."""
        market_data = MarketData(
            pair=self.pair,
            timeframe=self.timeframe,
            candlesticks=[],
            last_updated=self.timestamp,
        )
        assert market_data.latest_candlestick is None
