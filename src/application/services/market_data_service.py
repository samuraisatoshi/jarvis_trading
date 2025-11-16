"""
Market data service for fetching and processing candle data.

Coordinates REST API calls with candle scheduler to fetch data at exact close times.
"""
from datetime import datetime
from typing import Dict, List, Callable, Optional
import asyncio
import logging

from src.infrastructure.exchange.binance_rest_client import BinanceRESTClient
from src.domain.market_data.services.candle_scheduler import CandleScheduler

logger = logging.getLogger(__name__)


class MarketDataService:
    """
    Market data service that fetches candles at official close times.

    Integrates REST client with candle scheduler to ensure data is fetched
    exactly when candles close, not at arbitrary time intervals.
    """

    def __init__(
        self,
        binance_client: BinanceRESTClient,
        scheduler: CandleScheduler,
        symbols: Optional[List[str]] = None,
        active_timeframes: Optional[List[str]] = None,
    ):
        """
        Initialize market data service.

        Args:
            binance_client: Binance REST client instance
            scheduler: Candle scheduler instance
            symbols: Trading pairs to monitor (default: major pairs)
            active_timeframes: Timeframes to track (default: all common)
        """
        self.binance = binance_client
        self.scheduler = scheduler
        self.symbols = symbols or ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
        self.active_timeframes = active_timeframes or ["5m", "15m", "1h", "4h", "1d"]
        self.candle_callbacks: Dict[str, List[Callable]] = {}

    def register_candle_callback(self, timeframe: str, callback: Callable):
        """
        Register a callback to execute when candle closes.

        Args:
            timeframe: Candle timeframe (1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w)
            callback: Async callable(symbol, candle, timeframe) to execute
        """
        if timeframe not in self.candle_callbacks:
            self.candle_callbacks[timeframe] = []

        self.candle_callbacks[timeframe].append(callback)
        logger.info(f"Registered callback for {timeframe}: {callback.__name__}")

    async def on_candle_close(self, timeframe: str):
        """
        Called when a candle closes.

        Fetches latest completed candles for all symbols and processes them.

        Args:
            timeframe: Timeframe that just closed
        """
        now = datetime.utcnow()
        logger.info(f"=== CANDLE CLOSED: {timeframe} at {now.isoformat()} UTC ===")

        # Fetch latest candles for all symbols
        candles = {}
        for symbol in self.symbols:
            try:
                klines = self.binance.get_klines(symbol, timeframe, limit=2)
                if klines:
                    # Get the completed candle (second to last, since last is incomplete)
                    completed_candle = klines[-2] if len(klines) > 1 else klines[-1]
                    candles[symbol] = completed_candle
                    logger.debug(f"  {symbol}: O:{completed_candle['open']} H:{completed_candle['high']} L:{completed_candle['low']} C:{completed_candle['close']} V:{completed_candle['volume']}")
                else:
                    logger.warning(f"  {symbol}: Failed to fetch candles")
            except Exception as e:
                logger.error(f"  {symbol}: Error fetching candles: {e}")

        # Execute registered callbacks
        if timeframe in self.candle_callbacks:
            for symbol, candle in candles.items():
                for callback in self.candle_callbacks[timeframe]:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(symbol, candle, timeframe)
                        else:
                            callback(symbol, candle, timeframe)
                    except Exception as e:
                        logger.error(f"Error in callback for {symbol} {timeframe}: {e}", exc_info=True)

    async def fetch_current_prices(self) -> Dict[str, float]:
        """
        Fetch current prices for all monitored symbols.

        Returns:
            Dictionary of symbol -> price
        """
        prices = {}
        for symbol in self.symbols:
            try:
                price = self.binance.get_ticker_price(symbol)
                if price is not None:
                    prices[symbol] = price
                    logger.debug(f"{symbol}: ${price:,.2f}")
            except Exception as e:
                logger.error(f"Error fetching price for {symbol}: {e}")

        return prices

    def show_job_schedule(self):
        """Display schedule of next candle closes."""
        logger.info("=== CANDLE CLOSE SCHEDULE (UTC) ===")
        for timeframe in self.active_timeframes:
            next_close = self.scheduler.get_next_candle_time(timeframe)
            wait_seconds = self.scheduler.get_wait_seconds(timeframe)
            logger.info(f"{timeframe:>4}: closes at {next_close.strftime('%H:%M:%S')} (in {wait_seconds:>6.0f}s)")

    async def start_all_jobs(self):
        """Start market data collection for all active timeframes."""
        logger.info(f"Starting market data collection for {len(self.active_timeframes)} timeframes")
        self.show_job_schedule()

        for timeframe in self.active_timeframes:
            self.scheduler.start_job(timeframe, self.on_candle_close)

    def stop_all_jobs(self):
        """Stop all market data collection jobs."""
        logger.info("Stopping all market data jobs")
        self.scheduler.stop_all_jobs()

    def get_active_jobs(self) -> List[Dict]:
        """Get status of all active jobs."""
        statuses = []
        for timeframe in self.scheduler.get_active_jobs():
            status = self.scheduler.get_job_status(timeframe)
            if status:
                statuses.append(status)
        return statuses

    async def fetch_historical_candles(
        self, symbol: str, timeframe: str, limit: int = 100
    ) -> List[Dict]:
        """
        Fetch historical candle data.

        Args:
            symbol: Trading pair
            timeframe: Candle timeframe
            limit: Number of candles to fetch

        Returns:
            List of candles
        """
        try:
            return self.binance.get_klines(symbol, timeframe, limit=limit)
        except Exception as e:
            logger.error(f"Error fetching historical candles for {symbol}: {e}")
            return []

    async def cleanup(self):
        """Cleanup resources."""
        self.stop_all_jobs()
        await self.scheduler.cleanup()
        self.binance.close()
        logger.info("Market data service cleaned up")
