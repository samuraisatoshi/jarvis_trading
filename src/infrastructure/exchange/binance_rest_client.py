"""
Binance REST API Client for fetching market data.
Uses REST API instead of WebSocket for more reliable candle-close timing.
"""
import requests
from datetime import datetime
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class BinanceRESTClient:
    """
    REST API client for Binance market data.
    Designed for fetching candlestick data at precise intervals.
    """

    BASE_URL = "https://api.binance.com/api/v3"
    TESTNET_URL = "https://testnet.binance.vision/api/v3"

    def __init__(self, testnet: bool = False):
        """
        Initialize Binance REST client.

        Args:
            testnet: Use testnet or production API
        """
        self.base_url = self.TESTNET_URL if testnet else self.BASE_URL
        self.testnet = testnet
        self.session = requests.Session()

    def get_klines(
        self, symbol: str, interval: str, limit: int = 100, start_time: Optional[int] = None
    ) -> List[Dict]:
        """
        Get candlestick data from Binance.

        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            interval: Candle interval (1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w)
            limit: Number of candles to fetch (default 100, max 1000)
            start_time: Optional start time in milliseconds

        Returns:
            List of kline data with OHLCV
        """
        endpoint = f"{self.base_url}/klines"
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": min(limit, 1000),  # Binance max is 1000
        }

        if start_time:
            params["startTime"] = start_time

        try:
            response = self.session.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            return self._parse_klines(response.json())
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching klines for {symbol}: {e}")
            return []

    def get_ticker_price(self, symbol: str) -> Optional[float]:
        """
        Get current price for a symbol.

        Args:
            symbol: Trading pair

        Returns:
            Current price or None if error
        """
        endpoint = f"{self.base_url}/ticker/price"
        params = {"symbol": symbol}

        try:
            response = self.session.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            return float(response.json()["price"])
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            return None

    def get_24h_ticker(self, symbol: str) -> Optional[Dict]:
        """
        Get 24-hour ticker statistics.

        Args:
            symbol: Trading pair

        Returns:
            24h ticker data or None if error
        """
        endpoint = f"{self.base_url}/ticker/24hr"
        params = {"symbol": symbol}

        try:
            response = self.session.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching 24h ticker for {symbol}: {e}")
            return None

    def get_exchange_info(self) -> Optional[Dict]:
        """
        Get exchange information including trading pairs.

        Returns:
            Exchange info or None if error
        """
        endpoint = f"{self.base_url}/exchangeInfo"

        try:
            response = self.session.get(endpoint, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching exchange info: {e}")
            return None

    def get_server_time(self) -> Optional[int]:
        """
        Get server time in milliseconds.
        Useful for synchronizing with exchange.

        Returns:
            Server time in milliseconds or None if error
        """
        endpoint = f"{self.base_url}/time"

        try:
            response = self.session.get(endpoint, timeout=10)
            response.raise_for_status()
            return response.json()["serverTime"]
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching server time: {e}")
            return None

    @staticmethod
    def _parse_klines(raw_klines: List[List]) -> List[Dict]:
        """
        Parse raw kline data from Binance into structured format.

        Binance returns:
        [
            open_time, open, high, low, close, volume,
            close_time, quote_asset_volume, number_of_trades,
            taker_buy_base_asset_volume, taker_buy_quote_asset_volume, ignore
        ]

        Args:
            raw_klines: Raw kline data from API

        Returns:
            Parsed klines with named fields
        """
        parsed = []
        for kline in raw_klines:
            parsed.append({
                "open_time": kline[0],
                "open": float(kline[1]),
                "high": float(kline[2]),
                "low": float(kline[3]),
                "close": float(kline[4]),
                "volume": float(kline[5]),
                "close_time": kline[6],
                "quote_asset_volume": float(kline[7]),
                "number_of_trades": int(kline[8]),
                "taker_buy_base_volume": float(kline[9]),
                "taker_buy_quote_volume": float(kline[10]),
            })
        return parsed

    def close(self):
        """Close session."""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
