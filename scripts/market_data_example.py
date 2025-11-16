"""
Practical example of using Market Data service with a trading strategy.

Shows:
1. Initializing market data service
2. Registering strategy callbacks
3. Processing candles at official close times
4. Generating signals from candle data
"""
import asyncio
import sys
import logging
from datetime import datetime
from pathlib import Path
from collections import deque

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.exchange.binance_rest_client import BinanceRESTClient
from src.domain.market_data.services.candle_scheduler import CandleScheduler
from src.application.services.market_data_service import MarketDataService


class SimpleMovingAverageStrategy:
    """
    Simple strategy that uses candle closes to calculate moving averages.

    Example: Alert when price crosses SMA(5)
    """

    def __init__(self, lookback: int = 5):
        """
        Initialize strategy.

        Args:
            lookback: Number of candles for SMA calculation
        """
        self.lookback = lookback
        self.candle_history = deque(maxlen=lookback + 1)
        self.signals = []

    def add_candle(self, candle: dict):
        """Add candle to history."""
        self.candle_history.append(candle["close"])

    def calculate_sma(self) -> float:
        """Calculate simple moving average."""
        if len(self.candle_history) < self.lookback:
            return None

        return sum(self.candle_history) / self.lookback

    async def analyze(self, symbol: str, candle: dict, timeframe: str):
        """
        Analyze candle and generate signal if SMA crossed.

        Args:
            symbol: Trading pair
            candle: Candle data
            timeframe: Timeframe of candle
        """
        # Add candle to history
        self.add_candle(candle)

        # Need minimum candles
        if len(self.candle_history) < self.lookback:
            logger.debug(f"[{symbol} {timeframe}] Need {self.lookback} candles ({len(self.candle_history)}/5)")
            return

        # Calculate SMA
        sma = self.calculate_sma()
        current_close = candle["close"]

        # Previous candle close
        prev_close = list(self.candle_history)[-2] if len(self.candle_history) > 1 else current_close

        # Check for crossing
        if prev_close <= sma and current_close > sma:
            signal = {
                "symbol": symbol,
                "timeframe": timeframe,
                "type": "BULLISH_CROSS",
                "price": current_close,
                "sma": sma,
                "timestamp": datetime.utcnow().isoformat(),
            }
            self.signals.append(signal)
            logger.info(
                f"✅ SIGNAL: {symbol} {timeframe} - Price crossed above SMA(5) "
                f"| Close: {current_close:.2f} | SMA: {sma:.2f}"
            )

        elif prev_close >= sma and current_close < sma:
            signal = {
                "symbol": symbol,
                "timeframe": timeframe,
                "type": "BEARISH_CROSS",
                "price": current_close,
                "sma": sma,
                "timestamp": datetime.utcnow().isoformat(),
            }
            self.signals.append(signal)
            logger.info(
                f"❌ SIGNAL: {symbol} {timeframe} - Price crossed below SMA(5) "
                f"| Close: {current_close:.2f} | SMA: {sma:.2f}"
            )
        else:
            sma_dist = ((current_close - sma) / sma) * 100
            logger.info(
                f"📊 {symbol} {timeframe}: Price={current_close:.2f} | SMA={sma:.2f} | Dist: {sma_dist:+.2f}%"
            )


class StrategyManager:
    """Manages multiple strategy instances for different symbols/timeframes."""

    def __init__(self):
        """Initialize manager."""
        self.strategies = {}
        self.all_signals = []

    def create_strategy(self, symbol: str, timeframe: str, lookback: int = 5) -> SimpleMovingAverageStrategy:
        """Create strategy for symbol/timeframe."""
        key = f"{symbol}_{timeframe}"
        strategy = SimpleMovingAverageStrategy(lookback=lookback)
        self.strategies[key] = strategy
        logger.info(f"Created strategy for {symbol} {timeframe}")
        return strategy

    async def on_candle_close(self, symbol: str, candle: dict, timeframe: str):
        """Called when candle closes."""
        key = f"{symbol}_{timeframe}"

        if key not in self.strategies:
            # Create strategy on first candle
            self.create_strategy(symbol, timeframe)

        strategy = self.strategies[key]
        await strategy.analyze(symbol, candle, timeframe)

        # Track signals
        if strategy.signals and len(strategy.signals) > len(self.all_signals):
            self.all_signals = strategy.signals.copy()

    def get_signals(self):
        """Get all generated signals."""
        return self.all_signals

    def print_summary(self):
        """Print strategy summary."""
        logger.info("\n" + "=" * 70)
        logger.info("STRATEGY SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Active strategies: {len(self.strategies)}")

        for key, strategy in self.strategies.items():
            logger.info(f"  {key}: {len(strategy.candle_history)} candles, {len(strategy.signals)} signals")

        if self.all_signals:
            logger.info(f"\nTotal signals generated: {len(self.all_signals)}")
            for signal in self.all_signals[-5:]:  # Show last 5
                logger.info(
                    f"  [{signal['timestamp']}] {signal['symbol']} {signal['timeframe']} - "
                    f"{signal['type']} @ {signal['price']:.2f}"
                )


async def main():
    """Main example."""
    logger.info("=" * 70)
    logger.info("MARKET DATA + STRATEGY EXAMPLE")
    logger.info("=" * 70)

    # Initialize market data
    logger.info("\nInitializing market data service...")
    binance = BinanceRESTClient(testnet=False)
    scheduler = CandleScheduler()
    market_data = MarketDataService(
        binance,
        scheduler,
        symbols=["BTCUSDT", "ETHUSDT"],
        active_timeframes=["1h"],  # Use 1h for faster testing
    )

    # Initialize strategy manager
    strategy_manager = StrategyManager()

    # Create strategies for each symbol/timeframe
    logger.info("\nCreating strategies...")
    for symbol in ["BTCUSDT", "ETHUSDT"]:
        strategy_manager.create_strategy(symbol, "1h", lookback=5)

    # Register callbacks
    logger.info("\nRegistering callbacks...")
    market_data.register_candle_callback("1h", strategy_manager.on_candle_close)

    try:
        # Show schedule
        logger.info("\nCandle close schedule:")
        market_data.show_job_schedule()

        # Fetch historical data first to seed the strategy
        logger.info("\nFetching historical candles to seed strategies...")
        for symbol in ["BTCUSDT", "ETHUSDT"]:
            candles = await market_data.fetch_historical_candles(symbol, "1h", limit=6)
            if candles:
                logger.info(f"  {symbol}: Got {len(candles)} candles")
                # Process historical candles to populate strategy history
                # (don't treat these as signals)

        # Start market data collection
        logger.info("\nStarting market data jobs...")
        logger.info("Waiting for next 1h candle close...")
        logger.info("(May take up to 1 hour for first signal)\n")

        await market_data.start_all_jobs()

        # Run for 15 minutes or until Ctrl+C
        for i in range(15):
            await asyncio.sleep(60)

            # Show active jobs status
            jobs = market_data.get_active_jobs()
            if jobs:
                logger.info(f"[Status Update] Active jobs: {len(jobs)}")
                for job in jobs:
                    logger.info(
                        f"  {job['timeframe']}: Next close in {job['wait_seconds']:.0f}s "
                        f"@ {job['next_close']}"
                    )

            # Print strategy summary
            strategy_manager.print_summary()

    except KeyboardInterrupt:
        logger.info("\n\nStopped by user")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
    finally:
        logger.info("\nCleaning up...")
        await market_data.cleanup()

        # Final summary
        strategy_manager.print_summary()
        logger.info("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
