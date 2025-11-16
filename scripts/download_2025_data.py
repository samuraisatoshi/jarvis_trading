#!/usr/bin/env python3
"""
Download 2025 market data from Binance for backtesting.

This script downloads complete 2025 data (01/01/2025 - 14/11/2025)
for multiple symbols and timeframes to enable comprehensive backtesting
with FinRL models.

Usage:
    python scripts/download_2025_data.py --symbols BTC,ETH,BNB --timeframes 1h,4h,1d
    python scripts/download_2025_data.py --dry-run  # Show what would be downloaded

Environment:
    BINANCE_API_KEY: Binance API key (optional for public data)
    BINANCE_API_SECRET: Binance API secret (optional for public data)
"""

import sys
import os
import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple
import pandas as pd
import time

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.infrastructure.exchange.binance_rest_client import BinanceRESTClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


class DataDownloader2025:
    """Download 2025 market data from Binance for backtesting."""

    def __init__(self, output_dir: str = None):
        """
        Initialize downloader.

        Args:
            output_dir: Output directory for CSV files (default: data/2025/)
        """
        self.client = BinanceRESTClient()
        self.output_dir = Path(output_dir or "data/2025")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Data period
        self.start_date = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        self.end_date = datetime(2025, 11, 14, 18, 44, 0, tzinfo=timezone.utc)

        # Statistics
        self.stats = {
            'total_symbols': 0,
            'total_timeframes': 0,
            'total_candles': 0,
            'total_bytes': 0,
            'start_time': None,
            'end_time': None,
            'errors': []
        }

    def get_timestamp_range_ms(self) -> Tuple[int, int]:
        """Get timestamp range in milliseconds."""
        start_ms = int(self.start_date.timestamp() * 1000)
        end_ms = int(self.end_date.timestamp() * 1000)
        return start_ms, end_ms

    def download_symbol_timeframe(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 1000
    ) -> Tuple[pd.DataFrame, int]:
        """
        Download data for single symbol/timeframe combination.

        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            timeframe: Timeframe (e.g., '1h', '4h', '1d')
            limit: Max klines per request (Binance default 1000)

        Returns:
            Tuple of (DataFrame, candle count)
        """
        start_ms, end_ms = self.get_timestamp_range_ms()

        logger.info(f"Downloading {symbol} {timeframe}...")

        all_klines = []
        current_ts = start_ms
        batch_count = 0

        try:
            while current_ts < end_ms:
                # Download batch
                klines = self.client.get_klines(
                    symbol=symbol,
                    interval=timeframe,
                    start_time=current_ts,
                    limit=limit
                )

                if not klines:
                    break

                all_klines.extend(klines)
                batch_count += 1

                # Move to next batch (from last kline close_time)
                if klines:
                    last_close_time = int(klines[-1]['close_time'])
                    if last_close_time >= end_ms - 1000:  # Reached end
                        break
                    current_ts = last_close_time + 1  # Start after this candle
                    logger.debug(f"  Batch {batch_count}: {len(klines)} candles (up to ts: {last_close_time})")

                # Rate limiting
                time.sleep(0.1)

            # Convert to DataFrame
            if not all_klines:
                logger.warning(f"  No data received for {symbol} {timeframe}")
                return None, 0

            # Convert from dict format to list format for DataFrame
            rows = []
            for kline in all_klines:
                rows.append([
                    kline['open_time'],
                    kline['open'],
                    kline['high'],
                    kline['low'],
                    kline['close'],
                    kline['volume'],
                    kline['close_time'],
                    kline['quote_asset_volume'],
                    kline['number_of_trades'],
                    kline['taker_buy_base_volume'],
                    kline['taker_buy_quote_volume'],
                    0
                ])

            df = pd.DataFrame(rows, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])

            # Convert types
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)

            for col in ['open', 'high', 'low', 'close', 'volume', 'quote_volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            # Drop unnecessary columns
            df = df[['open', 'high', 'low', 'close', 'volume', 'quote_volume', 'trades']]

            logger.info(
                f"  Downloaded {len(df)} candles ({df.index[0]} to {df.index[-1]})"
            )

            return df, len(df)

        except Exception as e:
            error_msg = f"Error downloading {symbol} {timeframe}: {str(e)}"
            logger.error(error_msg)
            self.stats['errors'].append(error_msg)
            return None, 0

    def save_dataframe(self, df: pd.DataFrame, symbol: str, timeframe: str) -> bool:
        """
        Save DataFrame to CSV file.

        Args:
            df: DataFrame to save
            symbol: Trading pair
            timeframe: Timeframe

        Returns:
            Success flag
        """
        try:
            # Format symbol (BTC_USDT for compatibility)
            safe_symbol = symbol.replace('USDT', '_USDT')

            filepath = self.output_dir / f"{safe_symbol}_{timeframe}_2025.csv"

            df.to_csv(filepath)
            file_size = filepath.stat().st_size

            logger.info(f"  Saved to {filepath.name} ({file_size:,} bytes)")
            self.stats['total_bytes'] += file_size

            return True

        except Exception as e:
            logger.error(f"Error saving {symbol} {timeframe}: {str(e)}")
            self.stats['errors'].append(str(e))
            return False

    def download_all(
        self,
        symbols: List[str] = None,
        timeframes: List[str] = None,
        dry_run: bool = False
    ) -> Dict:
        """
        Download all symbol/timeframe combinations.

        Args:
            symbols: List of symbols to download
            timeframes: List of timeframes to download
            dry_run: If True, only show what would be downloaded

        Returns:
            Statistics dictionary
        """
        if symbols is None:
            symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'AVAXUSDT']

        if timeframes is None:
            timeframes = ['1h', '4h', '1d']

        self.stats['total_symbols'] = len(symbols)
        self.stats['total_timeframes'] = len(timeframes)
        self.stats['start_time'] = datetime.now()

        logger.info("=" * 80)
        logger.info("2025 MARKET DATA DOWNLOADER")
        logger.info("=" * 80)
        logger.info(f"Period: {self.start_date.isoformat()} to {self.end_date.isoformat()}")
        logger.info(f"Symbols: {', '.join(symbols)}")
        logger.info(f"Timeframes: {', '.join(timeframes)}")
        logger.info(f"Output: {self.output_dir}")
        logger.info(f"Dry run: {dry_run}")
        logger.info("=" * 80)

        results = {}
        total_downloaded = 0

        for symbol in symbols:
            results[symbol] = {}

            for timeframe in timeframes:
                if dry_run:
                    logger.info(f"Would download: {symbol} {timeframe}")
                    results[symbol][timeframe] = {'status': 'dry_run', 'candles': 0}
                    continue

                df, count = self.download_symbol_timeframe(symbol, timeframe)

                if df is not None:
                    saved = self.save_dataframe(df, symbol, timeframe)

                    results[symbol][timeframe] = {
                        'status': 'success' if saved else 'save_failed',
                        'candles': count,
                        'date_range': f"{df.index[0]} to {df.index[-1]}"
                    }

                    self.stats['total_candles'] += count
                    total_downloaded += 1
                else:
                    results[symbol][timeframe] = {'status': 'download_failed', 'candles': 0}

        self.stats['end_time'] = datetime.now()

        return results

    def print_summary(self):
        """Print download summary."""
        logger.info("\n" + "=" * 80)
        logger.info("DOWNLOAD SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total symbols: {self.stats['total_symbols']}")
        logger.info(f"Total timeframes: {self.stats['total_timeframes']}")
        logger.info(f"Total candles: {self.stats['total_candles']:,}")
        logger.info(f"Total bytes: {self.stats['total_bytes']:,} ({self.stats['total_bytes']/1024/1024:.1f} MB)")

        if self.stats['start_time'] and self.stats['end_time']:
            duration = self.stats['end_time'] - self.stats['start_time']
            logger.info(f"Duration: {duration.total_seconds():.1f}s")

        if self.stats['errors']:
            logger.warning(f"Errors: {len(self.stats['errors'])}")
            for error in self.stats['errors'][:3]:
                logger.warning(f"  - {error}")

        logger.info("=" * 80)

    def save_metadata(self):
        """Save download metadata to JSON."""
        metadata = {
            'downloaded_at': datetime.now().isoformat(),
            'period_start': self.start_date.isoformat(),
            'period_end': self.end_date.isoformat(),
            'total_candles': self.stats['total_candles'],
            'total_bytes': self.stats['total_bytes'],
            'output_dir': str(self.output_dir)
        }

        metadata_file = self.output_dir / 'metadata.json'
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Metadata saved to {metadata_file.name}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Download 2025 market data from Binance for backtesting'
    )
    parser.add_argument(
        '--symbols',
        type=str,
        default='BTC,ETH,BNB',
        help='Comma-separated symbols (default: BTC,ETH,BNB)'
    )
    parser.add_argument(
        '--timeframes',
        type=str,
        default='1h,4h,1d',
        help='Comma-separated timeframes (default: 1h,4h,1d)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='data/2025',
        help='Output directory (default: data/2025)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be downloaded without downloading'
    )

    args = parser.parse_args()

    # Parse symbols and timeframes
    symbols = [s.strip().upper() for s in args.symbols.split(',')]
    timeframes = [t.strip() for t in args.timeframes.split(',')]

    # Add USDT suffix if not present
    symbols = [s if s.endswith('USDT') else f"{s}USDT" for s in symbols]

    # Create downloader
    downloader = DataDownloader2025(output_dir=args.output)

    try:
        # Download data
        results = downloader.download_all(
            symbols=symbols,
            timeframes=timeframes,
            dry_run=args.dry_run
        )

        # Print summary
        downloader.print_summary()

        # Save metadata
        if not args.dry_run:
            downloader.save_metadata()

        return 0

    except KeyboardInterrupt:
        logger.warning("Download interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
