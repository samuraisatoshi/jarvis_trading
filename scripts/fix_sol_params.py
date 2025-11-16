#!/usr/bin/env python3
"""
Corrige os parâmetros de SOLUSDT na watchlist.
"""

import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.exchange.binance_rest_client import BinanceRESTClient


def main():
    """Atualiza parâmetros de SOLUSDT."""
    db_path = 'data/jarvis_trading.db'
    symbol = 'SOLUSDT'

    # Primeiro, baixar dados históricos
    print(f"📥 Baixando dados históricos de {symbol}...")
    client = BinanceRESTClient(testnet=False)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    timeframes = {
        '1h': 1000,
        '4h': 1000,
        '1d': 1000
    }

    for tf, limit in timeframes.items():
        print(f"  Baixando {limit} velas de {tf}...")

        try:
            klines = client.get_klines(symbol=symbol, interval=tf, limit=limit)

            # Salvar no banco
            for kline in klines:
                cursor.execute("""
                    INSERT OR REPLACE INTO market_data
                    (symbol, timeframe, timestamp, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    symbol, tf,
                    kline['open_time'],
                    float(kline['open']),
                    float(kline['high']),
                    float(kline['low']),
                    float(kline['close']),
                    float(kline['volume'])
                ))

            print(f"    ✅ {len(klines)} velas salvas")

        except Exception as e:
            print(f"    ❌ Erro: {e}")

    conn.commit()

    # Parâmetros otimizados para SOLUSDT baseados na análise anterior
    params = {
        '1h': {
            'ma_period': 20,
            'buy_threshold': -3.3,
            'sell_threshold': 2.0
        },
        '4h': {
            'ma_period': 100,
            'buy_threshold': -12.2,
            'sell_threshold': 10.0
        },
        '1d': {
            'ma_period': 200,
            'buy_threshold': -12.0,
            'sell_threshold': 16.0
        }
    }

    # Atualizar no banco
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

    conn.commit()
    conn.close()

    print(f"\n✅ {symbol} atualizado com sucesso!")
    print("\n📊 Parâmetros configurados:")
    print(f"  1H: Compra < -3.3%, Venda > 2.0% (MA20)")
    print(f"  4H: Compra < -12.2%, Venda > 10.0% (MA100)")
    print(f"  1D: Compra < -12.0%, Venda > 16.0% (MA200)")


if __name__ == "__main__":
    main()