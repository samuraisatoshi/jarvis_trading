#!/usr/bin/env python3
"""
Quick test script for Fibonacci Golden Zone Strategy

Tests the strategy with current market data and validates all components.

Usage:
    python scripts/test_fibonacci_strategy.py
    python scripts/test_fibonacci_strategy.py --symbol BTC_USDT
    python scripts/test_fibonacci_strategy.py --verbose
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.exchange.binance_rest_client import BinanceRESTClient

sys.path.insert(0, str(project_root / 'scripts'))
from fibonacci_golden_zone_strategy import FibonacciGoldenZoneStrategy


def create_test_data(trend='UPTREND'):
    """Create synthetic test data."""
    dates = pd.date_range(start='2025-01-01', periods=250, freq='D')

    if trend == 'UPTREND':
        # Create uptrend with pullback
        base_price = 100
        prices = np.linspace(base_price, base_price * 1.5, 250)
        # Add pullback at end
        prices[-30:] = np.linspace(prices[-30], prices[-30] * 0.92, 30)

    elif trend == 'DOWNTREND':
        # Create downtrend with rally
        base_price = 150
        prices = np.linspace(base_price, base_price * 0.7, 250)
        # Add rally at end
        prices[-30:] = np.linspace(prices[-30], prices[-30] * 1.08, 30)

    else:  # LATERAL
        # Create sideways market
        base_price = 100
        prices = base_price + np.random.normal(0, 2, 250)

    # Add noise
    prices = prices + np.random.normal(0, 1, 250)

    # Create OHLC
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': prices * 1.01,
        'low': prices * 0.99,
        'close': prices,
        'volume': np.random.uniform(1000, 5000, 250)
    })
    df.set_index('timestamp', inplace=True)

    return df


def test_trend_identification():
    """Test trend identification."""
    print("\n=== Test: Trend Identification ===")

    strategy = FibonacciGoldenZoneStrategy()

    # Test UPTREND
    df_up = create_test_data('UPTREND')
    trend_up = strategy.identify_trend(df_up)
    print(f"Uptrend data -> Detected: {trend_up} ✅" if trend_up == 'UPTREND' else f"Uptrend data -> Detected: {trend_up} ❌")

    # Test DOWNTREND
    df_down = create_test_data('DOWNTREND')
    trend_down = strategy.identify_trend(df_down)
    print(f"Downtrend data -> Detected: {trend_down} ✅" if trend_down == 'DOWNTREND' else f"Downtrend data -> Detected: {trend_down} ❌")

    # Test LATERAL
    df_lateral = create_test_data('LATERAL')
    trend_lateral = strategy.identify_trend(df_lateral)
    print(f"Lateral data -> Detected: {trend_lateral} ✅" if trend_lateral == 'LATERAL' else f"Lateral data -> Detected: {trend_lateral} ❌")


def test_fibonacci_calculations():
    """Test Fibonacci level calculations."""
    print("\n=== Test: Fibonacci Calculations ===")

    strategy = FibonacciGoldenZoneStrategy()

    # Test uptrend levels
    high = 100
    low = 50
    levels = strategy.calculate_fibonacci_levels(high, low, is_uptrend=True)

    print(f"High: ${high}, Low: ${low}")
    print(f"  0.236 level: ${levels['0.236']:.2f} (expected ~$88.20)")
    print(f"  0.500 level: ${levels['0.500']:.2f} (expected $75.00)")
    print(f"  0.618 level: ${levels['0.618']:.2f} (expected ~$69.10)")
    print(f"  Golden Zone: ${levels['0.618']:.2f} - ${levels['0.500']:.2f}")

    # Validate calculations
    assert abs(levels['0.500'] - 75.0) < 0.01, "0.500 level incorrect"
    assert abs(levels['0.618'] - 69.1) < 0.5, "0.618 level incorrect"
    print("✅ Fibonacci calculations correct")


def test_golden_zone_detection():
    """Test Golden Zone detection."""
    print("\n=== Test: Golden Zone Detection ===")

    strategy = FibonacciGoldenZoneStrategy()

    fib_levels = strategy.calculate_fibonacci_levels(100, 50, is_uptrend=True)

    # Test prices in/out of Golden Zone
    test_prices = [
        (80.0, False, "Above Golden Zone"),
        (72.5, True, "Inside Golden Zone"),
        (68.0, False, "Below Golden Zone"),
    ]

    for price, expected_in_zone, description in test_prices:
        in_zone = strategy.is_in_golden_zone(price, fib_levels, 'UPTREND')
        result = "✅" if in_zone == expected_in_zone else "❌"
        print(f"{description}: ${price:.2f} -> In zone: {in_zone} {result}")


def test_with_real_data(symbol='BNB_USDT', verbose=False):
    """Test with real market data."""
    print(f"\n=== Test: Real Market Data ({symbol}) ===")

    try:
        # Fetch real data
        client = BinanceRESTClient(testnet=False)
        binance_symbol = symbol.replace("_", "")

        print(f"Fetching data for {binance_symbol}...")
        klines = client.get_klines(symbol=binance_symbol, interval='1d', limit=300)

        if not klines:
            print("❌ No data received")
            return

        df = pd.DataFrame(klines)
        df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms")
        df = df[["timestamp", "open", "high", "low", "close", "volume"]]
        df.set_index("timestamp", inplace=True)

        print(f"Fetched {len(df)} candles from {df.index[0].date()} to {df.index[-1].date()}")

        # Run strategy
        strategy = FibonacciGoldenZoneStrategy()
        signal = strategy.generate_signal(df)

        print(f"\nStrategy Analysis:")
        print(f"  Trend: {signal['trend']}")
        print(f"  Action: {signal['action']}")
        print(f"  Reason: {signal['reason']}")
        print(f"  Current Price: ${signal['current_price']:,.2f}")

        if 'fib_levels' in signal:
            print(f"\nFibonacci Levels:")
            print(f"  High: ${signal['fib_levels']['high']:,.2f}")
            print(f"  Low: ${signal['fib_levels']['low']:,.2f}")
            print(f"  Golden Zone: ${signal['fib_levels']['0.618']:,.2f} - ${signal['fib_levels']['0.500']:,.2f}")

            if signal['action'] in ['BUY', 'SELL']:
                print(f"\nTrade Setup:")
                print(f"  Entry: ${signal['entry']:,.2f}")
                print(f"  Stop Loss: ${signal['stop_loss']:,.2f}")
                print(f"  Take Profit 1: ${signal['take_profit_1']:,.2f}")
                print(f"  Take Profit 2: ${signal['take_profit_2']:,.2f}")
                print(f"  Confirmations: {', '.join(signal['confirmations'])}")

        if verbose and 'confirmations' in signal:
            print(f"\nConfirmation Signals: {', '.join(signal['confirmations']) if signal['confirmations'] else 'None'}")

        print("\n✅ Real data test completed")

    except Exception as e:
        print(f"❌ Error testing real data: {e}")
        import traceback
        traceback.print_exc()


def run_all_tests(symbol='BNB_USDT', verbose=False):
    """Run all tests."""
    print("="*80)
    print("FIBONACCI GOLDEN ZONE STRATEGY - TEST SUITE")
    print("="*80)

    test_trend_identification()
    test_fibonacci_calculations()
    test_golden_zone_detection()
    test_with_real_data(symbol, verbose)

    print("\n" + "="*80)
    print("TEST SUITE COMPLETED")
    print("="*80 + "\n")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Test Fibonacci Golden Zone strategy")
    parser.add_argument(
        "--symbol",
        type=str,
        default="BNB_USDT",
        help="Trading pair for real data test"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output"
    )

    args = parser.parse_args()

    run_all_tests(args.symbol, args.verbose)


if __name__ == "__main__":
    main()
