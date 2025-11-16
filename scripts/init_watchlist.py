#!/usr/bin/env python3
"""
Initialize watchlist with calculated parameters from existing market data.
"""

import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def calculate_optimal_params(symbol: str, db_path: str) -> dict:
    """Calculate optimal parameters for each timeframe."""
    params = {}
    conn = sqlite3.connect(db_path)

    for tf in ['1h', '4h', '1d']:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT timestamp, close
            FROM market_data
            WHERE symbol = ? AND timeframe = ?
            ORDER BY timestamp
        """, (symbol, tf))

        data = cursor.fetchall()
        if len(data) < 200:
            continue

        df = pd.DataFrame(data, columns=['timestamp', 'close'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)

        # Calcular MAs based on timeframe
        if tf == '1h':
            ma_period = 20
        elif tf == '4h':
            ma_period = 100
        else:  # 1d
            ma_period = 200

        df['ma'] = df['close'].rolling(window=ma_period).mean()
        df['dist'] = (df['close'] - df['ma']) / df['ma'] * 100

        # Identificar reversões
        df['is_bottom'] = (
            df['close'] == df['close'].rolling(window=12, center=True).min()
        )
        df['is_top'] = (
            df['close'] == df['close'].rolling(window=12, center=True).max()
        )

        # Distâncias nos pontos de reversão
        bottoms = df[df['is_bottom']]['dist'].values
        tops = df[df['is_top']]['dist'].values

        if len(bottoms) > 5 and len(tops) > 5:
            params[tf] = {
                'ma_period': ma_period,
                'buy_threshold': float(np.percentile(bottoms, 25)),
                'sell_threshold': float(np.percentile(tops, 75)),
                'bottoms_count': len(bottoms),
                'tops_count': len(tops)
            }

    conn.close()
    return params


def main():
    """Initialize watchlist with optimal parameters."""
    db_path = 'data/jarvis_trading.db'
    symbols = ['BNBUSDT', 'BTCUSDT', 'ETHUSDT']

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("Initializing watchlist with optimal parameters...")
    print("=" * 60)

    for symbol in symbols:
        print(f"\n{symbol}:")

        # Calculate optimal params from existing market data
        params = calculate_optimal_params(symbol, db_path)

        # Insert into watchlist
        cursor.execute("""
            INSERT OR REPLACE INTO watchlist (
                symbol, added_at, params_1h, params_4h, params_1d,
                last_updated, is_active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            symbol,
            datetime.now(timezone.utc).isoformat(),
            json.dumps(params.get('1h', {})),
            json.dumps(params.get('4h', {})),
            json.dumps(params.get('1d', {})),
            datetime.now(timezone.utc).isoformat(),
            1
        ))

        # Display parameters
        for tf in ['1h', '4h', '1d']:
            if tf in params:
                p = params[tf]
                print(f"  {tf.upper()}: Buy {p['buy_threshold']:.1f}%, Sell {p['sell_threshold']:.1f}% (MA{p['ma_period']})")

    conn.commit()
    conn.close()

    print("\n" + "=" * 60)
    print("✅ Watchlist initialized successfully!")


if __name__ == "__main__":
    main()