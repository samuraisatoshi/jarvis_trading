#!/usr/bin/env python3
"""
Fibonacci Golden Zone Trading Strategy - Thin Wrapper.

This is a backward-compatible wrapper around the refactored strategy implementation
in src/strategies/fibonacci_golden_zone.py. All core logic has been moved to the
src/ package for better organization and reusability.

For new code, import directly from src:
    >>> from src.strategies import FibonacciGoldenZoneStrategy

This wrapper maintains backward compatibility for existing scripts that import:
    >>> from fibonacci_golden_zone_strategy import FibonacciGoldenZoneStrategy

REFACTORING NOTE:
- Original: 574 lines in scripts/
- New: ~50 lines wrapper + ~500 lines in src/strategies/
- Benefits: Reusable, testable, follows SOLID principles
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import from refactored location
from src.strategies.fibonacci_golden_zone import FibonacciGoldenZoneStrategy

# Re-export for backward compatibility
__all__ = ['FibonacciGoldenZoneStrategy']


if __name__ == '__main__':
    """
    Simple CLI test for the strategy.

    For comprehensive backtesting, use:
        python scripts/backtest_fibonacci_2025.py
    """
    import pandas as pd
    from src.infrastructure.exchange.binance_rest_client import BinanceRESTClient

    print("Fibonacci Golden Zone Strategy - Quick Test")
    print("=" * 50)

    # Initialize strategy
    strategy = FibonacciGoldenZoneStrategy()

    # Fetch some recent data
    print("\nFetching BTC/USDT 4h data...")
    client = BinanceRESTClient(testnet=False)
    klines = client.get_klines(symbol='BTCUSDT', interval='4h', limit=250)

    # Convert to DataFrame
    df = pd.DataFrame(klines)
    df['timestamp'] = pd.to_datetime(df['open_time'], unit='ms')
    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    df.set_index('timestamp', inplace=True)

    print(f"Fetched {len(df)} candles")
    print(f"Date range: {df.index[0]} to {df.index[-1]}")

    # Generate signal
    print("\nGenerating signal...")
    signal = strategy.generate_signal(df)

    # Display result
    print("\n" + "=" * 50)
    print(f"ACTION: {signal['action']}")
    print(f"REASON: {signal['reason']}")
    print(f"TREND: {signal['trend']}")
    print(f"CURRENT PRICE: ${signal['current_price']:.2f}")

    if signal['action'] in ['BUY', 'SELL']:
        print(f"\nTRADE PARAMETERS:")
        print(f"  Entry: ${signal['entry']:.2f}")
        print(f"  Stop Loss: ${signal['stop_loss']:.2f}")
        print(f"  Take Profit 1: ${signal['take_profit_1']:.2f}")
        print(f"  Take Profit 2: ${signal['take_profit_2']:.2f}")
        print(f"  Confirmations: {', '.join(signal['confirmations'])}")

    print("=" * 50)
    print("\nFor full backtesting, use: python scripts/backtest_fibonacci_2025.py")
