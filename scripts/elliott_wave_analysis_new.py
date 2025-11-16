#!/usr/bin/env python3
"""
Elliott Wave Analysis for BTC/USDT - Refactored Version

This script is now a thin wrapper around the modular src/elliott_wave package.
Maintains backward compatibility with same CLI interface and output format.

Performs comprehensive Elliott Wave analysis across multiple timeframes (4H, 1D).

This script is EXPLICIT in error handling - NO silent failures or mock data.
"""
import sys
import os
from pathlib import Path
from datetime import datetime
import pandas as pd
import logging

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.infrastructure.exchange.binance_rest_client import BinanceRESTClient
from src.elliott_wave import ElliottWaveAnalyzer, ElliottWaveVisualizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def fetch_candles(client: BinanceRESTClient, symbol: str,
                 timeframe: str, limit: int = 200) -> pd.DataFrame:
    """
    Fetch candlestick data from Binance.

    Args:
        client: Binance REST client
        symbol: Trading pair (e.g., 'BTCUSDT')
        timeframe: Candle timeframe (4h, 1d)
        limit: Number of candles to fetch

    Returns:
        DataFrame with OHLCV data

    Raises:
        RuntimeError: If data fetch fails
    """
    logger.info(f"Fetching {limit} candles for {symbol} {timeframe}")

    try:
        klines = client.get_klines(symbol, timeframe, limit=limit)

        if not klines:
            raise RuntimeError(
                f"No data returned from Binance for {symbol} {timeframe}"
            )

        df = pd.DataFrame(klines)
        df['timestamp'] = pd.to_datetime(df['open_time'], unit='ms')
        df.set_index('timestamp', inplace=True)

        logger.info(f"Fetched {len(df)} candles from {df.index[0]} to {df.index[-1]}")
        return df

    except Exception as e:
        logger.error(f"Failed to fetch candles: {e}", exc_info=True)
        raise RuntimeError(f"Data fetch failed: {e}") from e


def main():
    """Main execution function."""
    try:
        # Initialize Binance client (production)
        logger.info("Initializing Binance REST client...")
        client = BinanceRESTClient(testnet=False)

        # Test connection
        server_time = client.get_server_time()
        if not server_time:
            raise RuntimeError(
                "Failed to connect to Binance API. "
                "Check your internet connection."
            )

        logger.info(
            f"Connected to Binance. "
            f"Server time: {datetime.fromtimestamp(server_time/1000)}"
        )

        # Fetch data for both timeframes
        df_1d = fetch_candles(client, 'BTCUSDT', '1d', limit=200)
        df_4h = fetch_candles(client, 'BTCUSDT', '4h', limit=200)

        # Initialize analyzer
        logger.info("Initializing Elliott Wave analyzer...")
        analyzer = ElliottWaveAnalyzer()

        # Analyze both timeframes
        logger.info("Analyzing 1D timeframe...")
        analysis_1d = analyzer.analyze(df_1d, timeframe='1d')

        logger.info("Analyzing 4H timeframe...")
        analysis_4h = analyzer.analyze(df_4h, timeframe='4h')

        # Generate and print report
        visualizer = ElliottWaveVisualizer(symbol='BTCUSDT')
        visualizer.print_report(analysis_1d, analysis_4h)

        # Save report to file
        reports_dir = Path(__file__).parent.parent / 'reports'
        reports_dir.mkdir(exist_ok=True)

        report_file = reports_dir / (
            f'elliott_wave_btcusdt_'
            f'{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
        )

        visualizer.save_report(analysis_1d, analysis_4h, str(report_file))
        logger.info(f"Report saved to: {report_file}")

    except RuntimeError as e:
        logger.error(f"Analysis failed: {e}")
        print(f"\n❌ ERROR: {e}")
        print("\n📋 If connection failed, check:")
        print("  1. Internet connectivity")
        print("  2. Binance API is accessible from your location")
        print("  3. No firewall blocking the connection")
        sys.exit(1)

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\n❌ CRITICAL ERROR: {e}")
        print("\n📋 This is a bug. Please report with the full error trace above.")
        sys.exit(1)

    finally:
        if 'client' in locals():
            client.close()


if __name__ == '__main__':
    main()
