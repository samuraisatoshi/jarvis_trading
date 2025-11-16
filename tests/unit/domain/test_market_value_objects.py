"""Unit tests for Market domain value objects."""

import pytest

from src.domain.market.entities.value_objects import (
    Price,
    Timeframe,
    TradingPair,
    Volume,
)


class TestTimeframe:
    """Tests for Timeframe value object."""

    def test_timeframe_enum_values(self) -> None:
        """Test timeframe enum values."""
        assert Timeframe.ONE_MINUTE.value == "1m"
        assert Timeframe.ONE_HOUR.value == "1h"
        assert Timeframe.ONE_DAY.value == "1d"

    def test_timeframe_to_seconds(self) -> None:
        """Test timeframe conversion to seconds."""
        assert Timeframe.ONE_MINUTE.to_seconds() == 60
        assert Timeframe.FIVE_MINUTES.to_seconds() == 300
        assert Timeframe.ONE_HOUR.to_seconds() == 3600
        assert Timeframe.ONE_DAY.to_seconds() == 86400

    def test_timeframe_to_binance_format(self) -> None:
        """Test binance format conversion."""
        assert Timeframe.ONE_HOUR.to_binance_format() == "1h"
        assert Timeframe.FOUR_HOURS.to_binance_format() == "4h"


class TestPrice:
    """Tests for Price value object."""

    def test_price_positive_value(self) -> None:
        """Test price accepts positive values."""
        price = Price(100.5)
        assert float(price) == 100.5

    def test_price_zero_value(self) -> None:
        """Test price accepts zero."""
        price = Price(0.0)
        assert float(price) == 0.0

    def test_price_negative_value_raises_error(self) -> None:
        """Test price rejects negative values."""
        with pytest.raises(ValueError):
            Price(-10.0)


class TestVolume:
    """Tests for Volume value object."""

    def test_volume_positive_value(self) -> None:
        """Test volume accepts positive values."""
        volume = Volume(1000.5)
        assert float(volume) == 1000.5

    def test_volume_negative_value_raises_error(self) -> None:
        """Test volume rejects negative values."""
        with pytest.raises(ValueError):
            Volume(-100.0)


class TestTradingPair:
    """Tests for TradingPair value object."""

    def test_trading_pair_valid(self) -> None:
        """Test valid trading pair."""
        pair = TradingPair("BTCUSDT")
        assert pair == "BTCUSDT"

    def test_trading_pair_case_insensitive(self) -> None:
        """Test trading pair is case insensitive."""
        pair = TradingPair("btcusdt")
        assert pair == "BTCUSDT"

    def test_trading_pair_invalid_format(self) -> None:
        """Test invalid trading pair raises error."""
        with pytest.raises(ValueError):
            TradingPair("BTC")

    def test_trading_pair_base_asset(self) -> None:
        """Test extracting base asset."""
        pair = TradingPair("BTCUSDT")
        assert pair.base_asset == "BTC"

    def test_trading_pair_quote_asset(self) -> None:
        """Test extracting quote asset."""
        pair = TradingPair("BTCUSDT")
        assert pair.quote_asset == "USDT"
