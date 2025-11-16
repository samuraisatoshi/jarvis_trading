#!/usr/bin/env python3
"""Quick portfolio status check."""

import sqlite3
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.exchange.binance_rest_client import BinanceRESTClient

def main():
    # Connect to database
    conn = sqlite3.connect('data/jarvis_trading.db')
    cursor = conn.cursor()

    # Check current balances
    cursor.execute("""
        SELECT currency, available_amount
        FROM balances
        WHERE account_id = '868e0dd8-37f5-43ea-a956-7cc05e6bad66'
    """)
    balances = cursor.fetchall()

    print("=" * 60)
    print("PORTFOLIO STATUS")
    print("=" * 60)
    print("\nCurrent Balances:")

    bnb_balance = 0
    usdt_balance = 0

    for currency, amount in balances:
        print(f"  {currency}: {amount:.6f}")
        if currency == 'BNB':
            bnb_balance = amount
        elif currency == 'USDT':
            usdt_balance = amount

    # Get latest BNB price
    client = BinanceRESTClient(testnet=False)
    ticker = client.get_24h_ticker('BNBUSDT')
    bnb_price = float(ticker['lastPrice'])

    # Calculate total value
    total_usd = usdt_balance + (bnb_balance * bnb_price)
    initial_capital = 5000.0
    pnl = total_usd - initial_capital
    pnl_pct = (total_usd / initial_capital - 1) * 100

    print(f"\nMarket Data:")
    print(f"  BNB Price: ${bnb_price:.2f}")

    print(f"\nPortfolio Performance:")
    print(f"  Initial Capital: ${initial_capital:.2f}")
    print(f"  Current Value:   ${total_usd:.2f}")
    print(f"  P&L:            ${pnl:.2f} ({pnl_pct:+.2f}%)")

    # Check last trades
    cursor.execute("""
        SELECT order_type, quantity, price, created_at
        FROM orders
        WHERE account_id = '868e0dd8-37f5-43ea-a956-7cc05e6bad66'
        ORDER BY created_at DESC
        LIMIT 5
    """)

    trades = cursor.fetchall()
    if trades:
        print(f"\nLast 5 Orders:")
        for trade in trades:
            order_type, qty, price, created_at = trade
            print(f"  {created_at[:19]} | {order_type:4} | {qty:.4f} BNB @ ${price:.2f}")

    conn.close()
    print("=" * 60)

if __name__ == "__main__":
    main()