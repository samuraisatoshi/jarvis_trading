#!/usr/bin/env python3
"""
Monitor First Execution - Real-time monitoring for paper trading first execution
"""

import time
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sqlite3
import json

class FirstExecutionMonitor:
    def __init__(self):
        self.db_path = Path("data/jarvis_trading.db")
        self.log_path = Path("logs/paper_trading_BNB_USDT_1d.log")
        self.next_execution = datetime(2025, 11, 15, 0, 0, 0, tzinfo=timezone.utc)

    def get_countdown(self):
        """Calculate time until execution"""
        now = datetime.now(timezone.utc)
        delta = self.next_execution - now

        if delta.total_seconds() < 0:
            return "EXECUTING NOW!"

        hours = int(delta.total_seconds() // 3600)
        minutes = int((delta.total_seconds() % 3600) // 60)
        seconds = int(delta.total_seconds() % 60)

        return f"{hours}h {minutes}m {seconds}s"

    def get_account_balance(self):
        """Get current account balance"""
        if not self.db_path.exists():
            return {"USDT": 5000.0, "BNB": 0.0}

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT currency, available_amount
                FROM balances
                WHERE account_id = '868e0dd8-37f5-43ea-a956-7cc05e6bad66'
            """)

            balances = {}
            for currency, amount in cursor.fetchall():
                balances[currency] = amount

            conn.close()
            return balances
        except:
            return {"USDT": 5000.0, "BNB": 0.0}

    def check_new_trades(self):
        """Check for new trades in database"""
        if not self.db_path.exists():
            return None

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Check last 5 minutes for new orders
            five_min_ago = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()

            cursor.execute("""
                SELECT order_id, order_type, quantity, price, status, created_at
                FROM orders
                WHERE account_id = '868e0dd8-37f5-43ea-a956-7cc05e6bad66'
                AND created_at > ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (five_min_ago,))

            result = cursor.fetchone()
            conn.close()

            if result:
                return {
                    "order_id": result[0],
                    "type": result[1],
                    "quantity": result[2],
                    "price": result[3],
                    "status": result[4],
                    "created_at": result[5]
                }
            return None
        except:
            return None

    def get_latest_log_lines(self, n=5):
        """Get latest lines from log file"""
        if not self.log_path.exists():
            return []

        try:
            with open(self.log_path, 'r') as f:
                lines = f.readlines()
                return lines[-n:] if len(lines) >= n else lines
        except:
            return []

    def display_status(self):
        """Display current monitoring status"""
        print("\033[2J\033[H")  # Clear screen
        print("=" * 80)
        print("🎯 MONITORING FIRST EXECUTION - BNB/USDT PAPER TRADING")
        print("=" * 80)
        print()

        # Countdown
        countdown = self.get_countdown()
        if "EXECUTING" in countdown:
            print(f"⚡ STATUS: {countdown}")
            print("🔄 Checking for model execution...")
        else:
            print(f"⏰ Time until execution: {countdown}")
            print(f"📅 Scheduled for: {self.next_execution.strftime('%Y-%m-%d %H:%M:%S UTC')}")

        print()

        # Account Balance
        balances = self.get_account_balance()
        print("💰 ACCOUNT BALANCE:")
        print(f"   USDT: ${balances.get('USDT', 0):,.2f}")
        print(f"   BNB:  {balances.get('BNB', 0):.6f}")

        print()

        # Check for new trades
        new_trade = self.check_new_trades()
        if new_trade:
            print("🚨 NEW TRADE DETECTED!")
            print(f"   Type: {new_trade['type']}")
            print(f"   Quantity: {new_trade['quantity']}")
            print(f"   Price: ${new_trade['price']}")
            print(f"   Status: {new_trade['status']}")
            print(f"   Time: {new_trade['created_at']}")
        else:
            print("📊 TRADES: No trades executed yet")

        print()

        # Latest log entries
        print("📝 LATEST LOG ENTRIES:")
        log_lines = self.get_latest_log_lines()
        for line in log_lines:
            # Extract key info from log lines
            if "Model prediction" in line or "Trade executed" in line or "ERROR" in line:
                print(f"   > {line.strip()[:100]}")

        print()
        print("=" * 80)
        print("Press Ctrl+C to stop monitoring")

    def monitor(self):
        """Main monitoring loop"""
        try:
            while True:
                self.display_status()

                # Check if we're past execution time
                now = datetime.now(timezone.utc)
                if now >= self.next_execution:
                    # Continue monitoring for 5 minutes after execution time
                    if now > self.next_execution + timedelta(minutes=5):
                        print("\n✅ Monitoring complete. First execution window has passed.")
                        break

                # Refresh every 5 seconds
                time.sleep(5)
        except KeyboardInterrupt:
            print("\n\n⏸️  Monitoring stopped by user")
            sys.exit(0)

def main():
    print("🚀 Starting First Execution Monitor...")
    print("This will monitor the paper trading system until the first execution completes.")
    print()

    monitor = FirstExecutionMonitor()
    monitor.monitor()

if __name__ == "__main__":
    main()