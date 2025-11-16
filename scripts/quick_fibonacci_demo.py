#!/usr/bin/env python3
"""
Quick Fibonacci Strategy Demo

Demonstrates the Fibonacci Golden Zone strategy with live market data
and shows how to integrate it into your own trading system.

Usage:
    python scripts/quick_fibonacci_demo.py
    python scripts/quick_fibonacci_demo.py --symbol BTC_USDT
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.exchange.binance_rest_client import BinanceRESTClient
import pandas as pd

sys.path.insert(0, str(project_root / 'scripts'))
from fibonacci_golden_zone_strategy import FibonacciGoldenZoneStrategy


def fetch_data(symbol='BNB_USDT', timeframe='1d', limit=300):
    """Fetch market data from Binance."""
    client = BinanceRESTClient(testnet=False)
    binance_symbol = symbol.replace("_", "")

    klines = client.get_klines(symbol=binance_symbol, interval=timeframe, limit=limit)

    df = pd.DataFrame(klines)
    df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms")
    df = df[["timestamp", "open", "high", "low", "close", "volume"]]
    df.set_index("timestamp", inplace=True)

    return df


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Quick Fibonacci strategy demo")
    parser.add_argument("--symbol", type=str, default="BNB_USDT", help="Trading pair")
    parser.add_argument("--timeframe", type=str, default="1d", help="Timeframe")

    args = parser.parse_args()

    print("\n" + "="*80)
    print(f"FIBONACCI GOLDEN ZONE STRATEGY - LIVE DEMO")
    print(f"Symbol: {args.symbol} | Timeframe: {args.timeframe}")
    print("="*80 + "\n")

    # 1. Fetch data
    print(f"Fetching market data for {args.symbol}...")
    df = fetch_data(args.symbol, args.timeframe)
    print(f"✅ Fetched {len(df)} candles from {df.index[0].date()} to {df.index[-1].date()}\n")

    # 2. Initialize strategy
    strategy = FibonacciGoldenZoneStrategy()

    # 3. Get signal
    print("Analyzing market with Fibonacci Golden Zone strategy...")
    signal = strategy.generate_signal(df)

    # 4. Display results
    print("\n" + "="*80)
    print("ANALYSIS RESULTS")
    print("="*80 + "\n")

    print(f"📊 Market Trend: {signal['trend']}")
    print(f"🎯 Trading Signal: {signal['action']}")
    print(f"💡 Reason: {signal['reason']}")
    print(f"💰 Current Price: ${signal['current_price']:,.2f}\n")

    if 'fib_levels' in signal:
        fib = signal['fib_levels']
        print("📐 Fibonacci Levels:")
        print(f"  Swing High: ${fib['high']:,.2f}")
        print(f"  Swing Low:  ${fib['low']:,.2f}")
        print(f"  Golden Zone: ${fib['0.618']:,.2f} - ${fib['0.500']:,.2f}")
        print(f"  23.6% Level: ${fib['0.236']:,.2f}")
        print(f"  38.2% Level: ${fib['0.382']:,.2f}")
        print(f"  78.6% Level: ${fib['0.786']:,.2f}\n")

    if signal['action'] in ['BUY', 'SELL']:
        print(f"🚀 TRADE SETUP:")
        print(f"  Entry Price:    ${signal['entry']:,.2f}")
        print(f"  Stop Loss:      ${signal['stop_loss']:,.2f} (Risk: {abs((signal['entry'] - signal['stop_loss'])/signal['entry']*100):.2f}%)")
        print(f"  Take Profit 1:  ${signal['take_profit_1']:,.2f} (Reward: {abs((signal['take_profit_1'] - signal['entry'])/signal['entry']*100):.2f}%)")
        print(f"  Take Profit 2:  ${signal['take_profit_2']:,.2f} (Reward: {abs((signal['take_profit_2'] - signal['entry'])/signal['entry']*100):.2f}%)")

        if 'confirmations' in signal:
            print(f"\n✅ Confirmations ({len(signal['confirmations'])}):")
            for conf in signal['confirmations']:
                print(f"   • {conf.replace('_', ' ').title()}")

        # Calculate risk:reward
        risk = abs(signal['entry'] - signal['stop_loss'])
        reward = abs(signal['take_profit_1'] - signal['entry'])
        rr_ratio = reward / risk if risk > 0 else 0
        print(f"\n📈 Risk:Reward Ratio: 1:{rr_ratio:.2f}")

    elif signal['action'] == 'HOLD':
        print("⏸️  HOLD: No trade signal at this time")
        if 'golden_zone' in signal:
            print(f"   Golden Zone is: {signal['golden_zone']}")
            print(f"   Current price needs to retrace to Golden Zone for entry")

    print("\n" + "="*80)
    print("\nNext Steps:")
    print("  1. Visualize: python scripts/plot_fibonacci_levels.py --symbol", args.symbol)
    print("  2. Backtest:  python scripts/backtest_fibonacci_2025.py --symbol", args.symbol)
    print("  3. Paper trade: python scripts/run_fibonacci_strategy.py --dry-run")
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()
