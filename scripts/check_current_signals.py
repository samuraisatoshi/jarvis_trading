#!/usr/bin/env python3
"""
Check current market conditions and signal status.
"""

import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.exchange.binance_rest_client import BinanceRESTClient


def get_current_prices():
    """Get current prices for all watchlist symbols."""
    client = BinanceRESTClient(testnet=False)
    symbols = ['BNBUSDT', 'BTCUSDT', 'ETHUSDT', 'SOLUSDT']
    prices = {}

    for symbol in symbols:
        try:
            ticker = client.get_ticker(symbol)
            prices[symbol] = float(ticker['lastPrice'])
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            # Try getting from klines as fallback
            try:
                klines = client.get_klines(symbol, '1m', limit=1)
                if klines:
                    prices[symbol] = float(klines[0]['close'])
                else:
                    prices[symbol] = 0
            except:
                prices[symbol] = 0

    return prices


def get_ma_values(symbol, timeframe, period):
    """Get current MA value from recent candles."""
    client = BinanceRESTClient(testnet=False)

    try:
        # Get enough candles to calculate MA
        klines = client.get_klines(symbol, timeframe, limit=period + 1)
        closes = [float(k['close']) for k in klines[:-1]]  # Exclude current unfinished candle

        if len(closes) >= period:
            ma = sum(closes[-period:]) / period
            return ma
    except:
        pass

    return None


def main():
    """Check current signal status."""
    db_path = 'data/jarvis_trading.db'

    # Get current prices
    prices = get_current_prices()

    # Load watchlist parameters
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT symbol, params_1h, params_4h, params_1d
        FROM watchlist
        WHERE is_active = 1
    """)

    print("\n" + "=" * 80)
    print("CURRENT MARKET STATUS - " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 80)

    for row in cursor.fetchall():
        symbol = row[0]
        params_1h = json.loads(row[1]) if row[1] else {}
        params_4h = json.loads(row[2]) if row[2] else {}
        params_1d = json.loads(row[3]) if row[3] else {}

        current_price = prices.get(symbol, 0)

        print(f"\n{symbol}: ${current_price:.2f}")
        print("-" * 40)

        # Check each timeframe
        for tf, params in [('1h', params_1h), ('4h', params_4h), ('1d', params_1d)]:
            if not params:
                continue

            ma_period = params['ma_period']
            buy_threshold = params['buy_threshold']
            sell_threshold = params['sell_threshold']

            # Get MA value
            ma_value = get_ma_values(symbol, tf, ma_period)

            if ma_value:
                distance_pct = ((current_price - ma_value) / ma_value) * 100

                # Check signal
                signal = ""
                if distance_pct < buy_threshold:
                    signal = "🟢 BUY SIGNAL!"
                elif distance_pct > sell_threshold:
                    signal = "🔴 SELL SIGNAL!"
                else:
                    # How close to signals
                    to_buy = abs(distance_pct - buy_threshold)
                    to_sell = abs(distance_pct - sell_threshold)
                    if to_buy < to_sell:
                        signal = f"📊 {to_buy:.1f}% to BUY"
                    else:
                        signal = f"📊 {to_sell:.1f}% to SELL"

                print(f"  {tf.upper():>3}: MA{ma_period} = ${ma_value:.2f}")
                print(f"       Distance: {distance_pct:+.2f}%")
                print(f"       Thresholds: Buy < {buy_threshold:.1f}% | Sell > {sell_threshold:.1f}%")
                print(f"       Status: {signal}")

    conn.close()

    # Check account balance
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT currency, available_amount
        FROM balances
        WHERE account_id = '868e0dd8-37f5-43ea-a956-7cc05e6bad66'
    """)

    print("\n" + "=" * 80)
    print("ACCOUNT BALANCE")
    print("=" * 80)

    for row in cursor.fetchall():
        currency, amount = row
        if amount > 0.001:
            print(f"{currency}: {amount:.4f}")

    conn.close()


if __name__ == "__main__":
    main()