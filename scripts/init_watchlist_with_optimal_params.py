#!/usr/bin/env python3
"""
Initialize watchlist with optimal parameters from our previous analysis.
"""

import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def main():
    """Initialize watchlist with pre-calculated optimal parameters."""
    db_path = 'data/jarvis_trading.db'

    # Optimal parameters discovered from our analysis
    watchlist_params = {
        'BNBUSDT': {
            '1h': {
                'ma_period': 20,
                'buy_threshold': -2.4,  # From 1H analysis
                'sell_threshold': 2.0
            },
            '4h': {
                'ma_period': 100,
                'buy_threshold': -3.2,  # From 4H analysis
                'sell_threshold': 10.3
            },
            '1d': {
                'ma_period': 200,
                'buy_threshold': -5.0,
                'sell_threshold': 15.0
            }
        },
        'BTCUSDT': {
            '1h': {
                'ma_period': 20,
                'buy_threshold': -1.8,
                'sell_threshold': 1.1
            },
            '4h': {
                'ma_period': 50,
                'buy_threshold': -3.5,
                'sell_threshold': 3.7
            },
            '1d': {
                'ma_period': 200,
                'buy_threshold': -4.0,
                'sell_threshold': 8.0
            }
        },
        'ETHUSDT': {
            '1h': {
                'ma_period': 20,
                'buy_threshold': -2.4,
                'sell_threshold': 1.9
            },
            '4h': {
                'ma_period': 100,
                'buy_threshold': -9.8,
                'sell_threshold': 8.5
            },
            '1d': {
                'ma_period': 200,
                'buy_threshold': -7.0,
                'sell_threshold': 12.0
            }
        }
    }

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("Initializing watchlist with optimal parameters...")
    print("=" * 60)

    for symbol, params in watchlist_params.items():
        print(f"\n{symbol}:")

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

    # Verify the data was saved
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM watchlist WHERE is_active = 1")
    count = cursor.fetchone()[0]
    conn.close()

    print("\n" + "=" * 60)
    print(f"✅ Watchlist initialized with {count} active symbols!")


if __name__ == "__main__":
    main()