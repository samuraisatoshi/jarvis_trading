"""
Test script for Market Data service with scheduled jobs.

Demonstrates:
1. Fetching current prices
2. Showing next candle close times
3. Starting scheduled jobs that execute at official candle closes
"""
import asyncio
import sys
import logging
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.exchange.binance_rest_client import BinanceRESTClient
from src.domain.market_data.services.candle_scheduler import CandleScheduler
from src.application.services.market_data_service import MarketDataService


async def sample_candle_processor(symbol: str, candle: dict, timeframe: str):
    """
    Sample callback that processes candles when they close.

    Args:
        symbol: Trading pair
        candle: Completed candle data
        timeframe: Timeframe that closed
    """
    logger.info(
        f"  CANDLE PROCESSED: {symbol} {timeframe} - "
        f"O:{candle['open']:.2f} H:{candle['high']:.2f} "
        f"L:{candle['low']:.2f} C:{candle['close']:.2f} "
        f"V:{candle['volume']:.2f}"
    )


async def main():
    """Main test function."""
    logger.info("=" * 70)
    logger.info("MARKET DATA SERVICE TEST - REST API with Scheduled Jobs")
    logger.info("=" * 70)

    # Initialize components
    logger.info("\n1. Initializing components...")
    binance = BinanceRESTClient(testnet=False)
    scheduler = CandleScheduler()
    market_service = MarketDataService(
        binance,
        scheduler,
        symbols=["BTCUSDT", "ETHUSDT", "BNBUSDT"],
        active_timeframes=["5m", "15m", "1h", "4h", "1d"],
    )

    try:
        # Test 1: Get current prices
        logger.info("\n2. Fetching current prices...")
        prices = await market_service.fetch_current_prices()
        for symbol, price in prices.items():
            logger.info(f"  {symbol}: ${price:,.2f}")

        # Test 2: Show next candle close times
        logger.info("\n3. Candle close schedule (UTC):")
        market_service.show_job_schedule()

        # Test 3: Get 24h statistics
        logger.info("\n4. 24h Statistics:")
        for symbol in market_service.symbols:
            ticker = binance.get_24h_ticker(symbol)
            if ticker:
                logger.info(f"  {symbol}: High: ${ticker['highPrice']}, Low: ${ticker['lowPrice']}, Change: {ticker['priceChangePercent']}%")

        # Test 4: Fetch historical candles
        logger.info("\n5. Fetching historical candles...")
        for symbol in ["BTCUSDT", "ETHUSDT"]:
            candles = await market_service.fetch_historical_candles(symbol, "1h", limit=3)
            if candles:
                logger.info(f"  {symbol} (last 3 hours):")
                for i, candle in enumerate(candles[-3:], 1):
                    logger.info(
                        f"    [{i}] O:{candle['open']:.2f} H:{candle['high']:.2f} "
                        f"L:{candle['low']:.2f} C:{candle['close']:.2f}"
                    )

        # Test 5: Register callbacks
        logger.info("\n6. Registering candle processors...")
        market_service.register_candle_callback("5m", sample_candle_processor)
        market_service.register_candle_callback("1h", sample_candle_processor)
        logger.info("  Callbacks registered for 5m and 1h timeframes")

        # Test 6: Start scheduled jobs
        logger.info("\n7. Starting scheduled jobs...")
        logger.info("  IMPORTANT: Jobs will execute at official candle closes (UTC)")
        logger.info("  Press Ctrl+C to stop\n")

        await market_service.start_all_jobs()

        # Keep running
        logger.info("Waiting for candle closes...\n")
        await asyncio.sleep(3600)  # Run for 1 hour

    except KeyboardInterrupt:
        logger.info("\n\nTest stopped by user")
    except Exception as e:
        logger.error(f"Error in test: {e}", exc_info=True)
    finally:
        logger.info("\nCleaning up...")
        await market_service.cleanup()
        logger.info("Done!")


if __name__ == "__main__":
    asyncio.run(main())
