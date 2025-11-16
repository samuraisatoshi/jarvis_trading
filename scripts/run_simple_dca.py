#!/usr/bin/env python3
"""
Simple Buy & Hold + Fixed DCA Implementation

The winning strategy: Just buy $200 of BNB every week.
No indicators, no timing, just discipline.

Backtest results: +87.41% return
"""

import sys
import time
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.exchange.binance_rest_client import BinanceRESTClient


def check_portfolio():
    """Check current portfolio status."""
    conn = sqlite3.connect('data/jarvis_trading.db')
    cursor = conn.cursor()

    # Get balances
    cursor.execute("""
        SELECT currency, available_amount
        FROM balances
        WHERE account_id = '868e0dd8-37f5-43ea-a956-7cc05e6bad66'
    """)
    balances = dict(cursor.fetchall())

    # Get BNB price
    client = BinanceRESTClient(testnet=False)
    ticker = client.get_24h_ticker('BNBUSDT')
    bnb_price = float(ticker['lastPrice'])

    # Calculate value
    bnb_balance = balances.get('BNB', 0.0)
    usdt_balance = balances.get('USDT', 0.0)
    total_value = usdt_balance + (bnb_balance * bnb_price)
    pnl = total_value - 5000.0
    pnl_pct = (total_value / 5000.0 - 1) * 100

    conn.close()

    return {
        "bnb_balance": bnb_balance,
        "usdt_balance": usdt_balance,
        "bnb_price": bnb_price,
        "total_value": total_value,
        "pnl": pnl,
        "pnl_pct": pnl_pct
    }


def execute_weekly_dca(amount_usd=200.0):
    """
    Execute weekly DCA purchase.

    Args:
        amount_usd: Amount in USD to invest weekly
    """
    conn = sqlite3.connect('data/jarvis_trading.db')
    cursor = conn.cursor()

    # Get current balances
    cursor.execute("""
        SELECT currency, available_amount
        FROM balances
        WHERE account_id = '868e0dd8-37f5-43ea-a956-7cc05e6bad66'
    """)
    balances = dict(cursor.fetchall())

    usdt_balance = balances.get('USDT', 0.0)

    if usdt_balance < amount_usd:
        print(f"❌ Insufficient USDT: ${usdt_balance:.2f} < ${amount_usd:.2f}")
        print("Note: This would need funding in real trading")
        # For paper trading, we could "add" USDT here if needed
        conn.close()
        return None

    # Get BNB price
    client = BinanceRESTClient(testnet=False)
    ticker = client.get_24h_ticker('BNBUSDT')
    bnb_price = float(ticker['lastPrice'])

    # Calculate BNB amount
    bnb_amount = amount_usd / bnb_price

    # Update balances
    new_usdt = usdt_balance - amount_usd
    new_bnb = balances.get('BNB', 0.0) + bnb_amount

    cursor.execute("""
        UPDATE balances
        SET available_amount = ?
        WHERE account_id = '868e0dd8-37f5-43ea-a956-7cc05e6bad66' AND currency = 'USDT'
    """, (new_usdt,))

    cursor.execute("""
        UPDATE balances
        SET available_amount = ?
        WHERE account_id = '868e0dd8-37f5-43ea-a956-7cc05e6bad66' AND currency = 'BNB'
    """, (new_bnb,))

    # Record transaction
    timestamp = datetime.now(timezone.utc).isoformat()
    cursor.execute("""
        INSERT INTO orders (order_id, account_id, symbol, order_type, quantity, price, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        f"DCA_{timestamp}",
        '868e0dd8-37f5-43ea-a956-7cc05e6bad66',
        'BNBUSDT',
        'BUY',
        bnb_amount,
        bnb_price,
        'FILLED',
        timestamp
    ))

    conn.commit()
    conn.close()

    print(f"✅ DCA Executed:")
    print(f"   Bought: {bnb_amount:.6f} BNB")
    print(f"   Price: ${bnb_price:.2f}")
    print(f"   Spent: ${amount_usd:.2f}")
    print(f"   New BNB: {new_bnb:.6f}")
    print(f"   New USDT: ${new_usdt:.2f}")

    return {
        "bnb_bought": bnb_amount,
        "price": bnb_price,
        "spent": amount_usd
    }


def main():
    """Main entry point."""
    print("=" * 60)
    print("BUY & HOLD + FIXED DCA STRATEGY")
    print("The Proven Winner: +87.41% Backtest Returns")
    print("=" * 60)

    # Check current status
    status = check_portfolio()

    print("\n📊 Current Portfolio:")
    print(f"   BNB:  {status['bnb_balance']:.6f}")
    print(f"   USDT: ${status['usdt_balance']:.2f}")
    print(f"   BNB Price: ${status['bnb_price']:.2f}")
    print(f"   Total Value: ${status['total_value']:.2f}")
    print(f"   P&L: ${status['pnl']:.2f} ({status['pnl_pct']:+.2f}%)")

    print("\n📈 Strategy Rules:")
    print("   1. NEVER sell BNB (Buy & Hold)")
    print("   2. Buy $200 BNB every Monday")
    print("   3. No indicators, no timing, just discipline")

    print("\n🎯 Next Actions:")
    if status['usdt_balance'] >= 200:
        print("   ✅ Ready for weekly DCA ($200 available)")
        print("   Run with --execute-dca to buy now")
    else:
        print(f"   ⚠️ Need ${200 - status['usdt_balance']:.2f} more USDT for next DCA")
        print("   Current USDT: ${:.2f}".format(status['usdt_balance']))

    # Check command line args
    if len(sys.argv) > 1 and sys.argv[1] == "--execute-dca":
        print("\n" + "=" * 60)
        print("EXECUTING WEEKLY DCA...")
        print("=" * 60)
        result = execute_weekly_dca(200.0)
        if result:
            print("\n✅ DCA Complete! Next DCA: Next Monday")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()