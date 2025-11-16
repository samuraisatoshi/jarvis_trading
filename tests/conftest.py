"""Shared test fixtures and configuration."""

import pytest


@pytest.fixture
def sample_btc_data():
    """Fixture providing sample BTC market data."""
    return {
        "pair": "BTCUSDT",
        "timeframe": "1h",
        "data": [
            {
                "timestamp": 1700000000,
                "open": 42000.0,
                "high": 42500.0,
                "low": 41500.0,
                "close": 42200.0,
                "volume": 1000.5,
            },
        ],
    }


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Fixture providing temporary cache directory."""
    return tmp_path / "cache"
