#!/usr/bin/env python3
"""
Telegram Status Bot - Interactive Trading Monitor

Provides interactive commands via Telegram to monitor and control trading system.

Commands:
    /status - System status and health
    /balance - Account balance and position
    /trades - Recent trade history
    /performance - Performance metrics
    /health - Full health check
    /pause - Pause trading (circuit breaker)
    /resume - Resume trading
    /report - Generate detailed report

Usage:
    # Start interactive bot
    python scripts/telegram_status_bot.py

    # Send single command
    python scripts/telegram_status_bot.py --command /status
"""

import sys
import os
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from dotenv import load_dotenv
from loguru import logger
import json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment
load_dotenv(project_root / ".env")

from src.infrastructure.database import DatabaseManager
from src.infrastructure.persistence.sqlite_account_repository import (
    SQLiteAccountRepository,
)
from src.infrastructure.persistence.sqlite_transaction_repository import (
    SQLiteTransactionRepository,
)
from src.infrastructure.persistence.sqlite_performance_repository import (
    SQLitePerformanceRepository,
)
from src.infrastructure.exchange.binance_rest_client import BinanceRESTClient
from src.infrastructure.notifications.telegram_notifier import TelegramNotifier
from src.domain.account.value_objects.currency import Currency
from src.domain.account.value_objects.money import Money

import requests


class TelegramStatusBot:
    """
    Interactive Telegram bot for trading system status and control.

    Supports commands:
    - /status - Current system status
    - /balance - Account balance
    - /trades - Recent trades
    - /performance - Performance metrics
    - /health - Health check
    - /pause - Pause trading
    - /resume - Resume trading
    - /report - Full report
    """

    def __init__(
        self,
        account_id: str,
        symbol: str,
        db_path: str,
        bot_token: str,
        chat_id: str,
    ):
        """Initialize status bot."""
        self.account_id = account_id
        self.symbol = symbol
        self.bot_token = bot_token
        self.chat_id = chat_id

        # Initialize services
        self.db = DatabaseManager(db_path)
        self.db.initialize()

        self.account_repo = SQLiteAccountRepository(self.db)
        self.transaction_repo = SQLiteTransactionRepository(self.db)
        self.performance_repo = SQLitePerformanceRepository(self.db)
        self.binance_client = BinanceRESTClient(testnet=False)

        self.telegram = TelegramNotifier(
            bot_token=bot_token, chat_id=chat_id, parse_mode="HTML"
        )

        # Bot state
        self.last_update_id = 0
        self.trading_paused = False

        logger.info(
            f"Telegram Status Bot initialized:\n"
            f"  Account: {account_id}\n"
            f"  Symbol: {symbol}\n"
            f"  Chat ID: {chat_id}"
        )

    def _format_currency(self, amount: float, symbol: str = "USDT") -> str:
        """Format currency amount."""
        if symbol == "USDT":
            return f"${amount:,.2f}"
        else:
            return f"{amount:.6f} {symbol}"

    def handle_status(self) -> str:
        """Handle /status command."""
        try:
            # Get account
            account = self.account_repo.find_by_id(self.account_id)
            if not account:
                return "❌ Account not found"

            # Get balances
            usdt_balance = float(
                account.balance.available.get(
                    Currency.USDT, Money(0, Currency.USDT)
                ).amount
            )

            asset_symbol = self.symbol.split("_")[0]
            asset_currency = Currency.from_string(asset_symbol)
            asset_balance = float(
                account.balance.available.get(
                    asset_currency, Money(0, asset_currency)
                ).amount
            )

            # Get current price
            binance_symbol = self.symbol.replace("_", "")
            current_price = self.binance_client.get_ticker_price(binance_symbol) or 0.0

            position_value = asset_balance * current_price
            total_value = usdt_balance + position_value

            # Check if daemon is running
            pid_file = project_root / "paper_trading.pid"
            daemon_status = "🟢 Running" if pid_file.exists() else "🔴 Stopped"

            # Build message
            message = (
                f"📊 <b>SYSTEM STATUS</b>\n\n"
                f"<b>Daemon:</b> {daemon_status}\n"
                f"<b>Trading:</b> {'⏸️ Paused' if self.trading_paused else '✅ Active'}\n"
                f"<b>Symbol:</b> {self.symbol}\n"
                f"<b>Price:</b> ${current_price:,.2f}\n\n"
                f"<b>💰 Balance:</b>\n"
                f"• USDT: ${usdt_balance:,.2f}\n"
                f"• {asset_symbol}: {asset_balance:.6f}\n"
                f"• Position: ${position_value:,.2f}\n"
                f"• <b>Total: ${total_value:,.2f}</b>\n\n"
                f"⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
            )

            return message

        except Exception as e:
            logger.error(f"Error in handle_status: {e}")
            return f"❌ Error: {str(e)}"

    def handle_balance(self) -> str:
        """Handle /balance command."""
        try:
            account = self.account_repo.find_by_id(self.account_id)
            if not account:
                return "❌ Account not found"

            # Get all balances
            balances = []
            for currency, money in account.balance.available.items():
                if float(money.amount) > 0:
                    balances.append(f"• {currency.value}: {float(money.amount):.6f}")

            # Get current price and total value
            asset_symbol = self.symbol.split("_")[0]
            asset_currency = Currency.from_string(asset_symbol)

            usdt_balance = float(
                account.balance.available.get(
                    Currency.USDT, Money(0, Currency.USDT)
                ).amount
            )
            asset_balance = float(
                account.balance.available.get(
                    asset_currency, Money(0, asset_currency)
                ).amount
            )

            binance_symbol = self.symbol.replace("_", "")
            current_price = self.binance_client.get_ticker_price(binance_symbol) or 0.0
            position_value = asset_balance * current_price
            total_value = usdt_balance + position_value

            message = (
                f"💰 <b>ACCOUNT BALANCE</b>\n\n"
                f"<b>Available Balances:</b>\n"
                + "\n".join(balances)
                + f"\n\n"
                f"<b>Current Position:</b>\n"
                f"• Price: ${current_price:,.2f}\n"
                f"• Value: ${position_value:,.2f}\n\n"
                f"<b>Total Portfolio Value:</b>\n"
                f"💵 ${total_value:,.2f}\n\n"
                f"⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
            )

            return message

        except Exception as e:
            logger.error(f"Error in handle_balance: {e}")
            return f"❌ Error: {str(e)}"

    def handle_trades(self, limit: int = 10) -> str:
        """Handle /trades command."""
        try:
            # Get recent transactions
            transactions = self.transaction_repo.get_by_account(
                self.account_id, limit=limit
            )

            if not transactions:
                return "📝 No trades found"

            # Build message
            message = f"📝 <b>RECENT TRADES</b> (Last {limit})\n\n"

            for tx in transactions:
                timestamp = tx.timestamp.strftime("%Y-%m-%d %H:%M")
                tx_type = tx.transaction_type.value
                amount = float(tx.amount.amount)
                currency = tx.amount.currency.value

                emoji = "🟢" if tx_type in ["BUY", "DEPOSIT"] else "🔴"

                message += (
                    f"{emoji} <b>{tx_type}</b>\n"
                    f"  Amount: {amount:.6f} {currency}\n"
                    f"  Time: {timestamp}\n"
                    f"  Note: {tx.description[:50]}\n\n"
                )

            message += f"⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"

            return message

        except Exception as e:
            logger.error(f"Error in handle_trades: {e}")
            return f"❌ Error: {str(e)}"

    def handle_performance(self) -> str:
        """Handle /performance command."""
        try:
            # Get performance metrics from last 7 days
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=7)

            metrics = self.performance_repo.get_by_date_range(
                self.account_id, start_date, end_date
            )

            if not metrics:
                return "📊 No performance data available"

            # Calculate aggregated metrics
            total_trades = len(metrics)
            wins = sum(1 for m in metrics if m.profit_loss > 0)
            losses = total_trades - wins
            win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

            total_pnl = sum(m.profit_loss for m in metrics)
            total_pnl_pct = sum(m.profit_loss_pct for m in metrics)

            message = (
                f"📊 <b>PERFORMANCE METRICS</b>\n"
                f"📅 Last 7 days\n\n"
                f"<b>Trading Activity:</b>\n"
                f"• Trades: {total_trades}\n"
                f"• Wins: {wins} ✅\n"
                f"• Losses: {losses} ❌\n"
                f"• Win Rate: {win_rate:.1f}%\n\n"
                f"<b>Profit & Loss:</b>\n"
                f"• Total P&L: ${total_pnl:+,.2f}\n"
                f"• Total P&L%: {total_pnl_pct:+.2f}%\n\n"
            )

            # Get best and worst trades
            if metrics:
                best_trade = max(metrics, key=lambda m: m.profit_loss)
                worst_trade = min(metrics, key=lambda m: m.profit_loss)

                message += (
                    f"<b>Best Trade:</b>\n"
                    f"• ${best_trade.profit_loss:+,.2f} ({best_trade.profit_loss_pct:+.2f}%)\n"
                    f"• {best_trade.timestamp.strftime('%Y-%m-%d')}\n\n"
                    f"<b>Worst Trade:</b>\n"
                    f"• ${worst_trade.profit_loss:+,.2f} ({worst_trade.profit_loss_pct:+.2f}%)\n"
                    f"• {worst_trade.timestamp.strftime('%Y-%m-%d')}\n\n"
                )

            message += f"⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"

            return message

        except Exception as e:
            logger.error(f"Error in handle_performance: {e}")
            return f"❌ Error: {str(e)}"

    def handle_health(self) -> str:
        """Handle /health command."""
        try:
            # Check API connection
            try:
                self.binance_client.get_ticker_price("BNBUSDT")
                api_status = "✅ Connected"
            except:
                api_status = "❌ Error"

            # Check database
            try:
                account = self.account_repo.find_by_id(self.account_id)
                db_status = "✅ OK" if account else "⚠️ Account not found"
            except:
                db_status = "❌ Error"

            # Check daemon
            pid_file = project_root / "paper_trading.pid"
            daemon_status = "✅ Running" if pid_file.exists() else "❌ Stopped"

            # Check log file
            log_file = project_root / "logs" / f"telegram_trading_{self.symbol}_1d.log"
            if log_file.exists():
                log_size = log_file.stat().st_size / 1024 / 1024  # MB
                log_modified = datetime.fromtimestamp(log_file.stat().st_mtime)
                log_status = f"✅ {log_size:.2f}MB (modified {log_modified.strftime('%Y-%m-%d %H:%M')})"
            else:
                log_status = "⚠️ Log file not found"

            message = (
                f"🏥 <b>HEALTH CHECK</b>\n\n"
                f"<b>System Components:</b>\n"
                f"• Binance API: {api_status}\n"
                f"• Database: {db_status}\n"
                f"• Daemon: {daemon_status}\n"
                f"• Log File: {log_status}\n\n"
                f"<b>Trading Status:</b>\n"
                f"• Mode: {'⏸️ Paused' if self.trading_paused else '✅ Active'}\n"
                f"• Symbol: {self.symbol}\n"
                f"• Account: {self.account_id[:8]}...\n\n"
                f"⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
            )

            return message

        except Exception as e:
            logger.error(f"Error in handle_health: {e}")
            return f"❌ Error: {str(e)}"

    def handle_pause(self) -> str:
        """Handle /pause command."""
        if self.trading_paused:
            return "⏸️ Trading is already paused"

        self.trading_paused = True
        logger.warning("Trading paused via Telegram command")

        return (
            f"⏸️ <b>TRADING PAUSED</b>\n\n"
            f"Trading has been paused manually.\n"
            f"No new trades will be executed.\n\n"
            f"Use /resume to resume trading.\n\n"
            f"⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )

    def handle_resume(self) -> str:
        """Handle /resume command."""
        if not self.trading_paused:
            return "✅ Trading is already active"

        self.trading_paused = False
        logger.info("Trading resumed via Telegram command")

        return (
            f"✅ <b>TRADING RESUMED</b>\n\n"
            f"Trading has been resumed.\n"
            f"System will execute trades normally.\n\n"
            f"⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )

    def handle_report(self) -> str:
        """Handle /report command - full detailed report."""
        try:
            # Combine all information
            status = self.handle_status()
            balance = self.handle_balance()
            performance = self.handle_performance()
            health = self.handle_health()

            message = (
                f"📋 <b>COMPREHENSIVE TRADING REPORT</b>\n"
                f"{'=' * 40}\n\n"
                f"{status}\n\n"
                f"{'=' * 40}\n\n"
                f"{balance}\n\n"
                f"{'=' * 40}\n\n"
                f"{performance}\n\n"
                f"{'=' * 40}\n\n"
                f"{health}"
            )

            return message

        except Exception as e:
            logger.error(f"Error in handle_report: {e}")
            return f"❌ Error: {str(e)}"

    def handle_help(self) -> str:
        """Handle /help command."""
        return (
            f"🤖 <b>TELEGRAM BOT COMMANDS</b>\n\n"
            f"<b>Status & Monitoring:</b>\n"
            f"/status - Current system status\n"
            f"/balance - Account balance\n"
            f"/trades - Recent trade history\n"
            f"/performance - Performance metrics\n"
            f"/health - Full health check\n"
            f"/report - Comprehensive report\n\n"
            f"<b>Control:</b>\n"
            f"/pause - Pause trading\n"
            f"/resume - Resume trading\n\n"
            f"/help - Show this help\n\n"
            f"⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )

    def process_command(self, command: str) -> str:
        """Process bot command."""
        command = command.strip().lower()

        if command == "/status":
            return self.handle_status()
        elif command == "/balance":
            return self.handle_balance()
        elif command == "/trades":
            return self.handle_trades()
        elif command == "/performance":
            return self.handle_performance()
        elif command == "/health":
            return self.handle_health()
        elif command == "/pause":
            return self.handle_pause()
        elif command == "/resume":
            return self.handle_resume()
        elif command == "/report":
            return self.handle_report()
        elif command == "/help":
            return self.handle_help()
        else:
            return (
                f"❓ Unknown command: {command}\n\n"
                f"Use /help to see available commands."
            )

    def get_updates(self) -> List[Dict]:
        """Get updates from Telegram."""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
            params = {"offset": self.last_update_id + 1, "timeout": 30}

            response = requests.get(url, params=params, timeout=35)
            response.raise_for_status()

            result = response.json()
            if result.get("ok"):
                return result.get("result", [])
            else:
                logger.error(f"Telegram API error: {result}")
                return []

        except Exception as e:
            logger.error(f"Error getting updates: {e}")
            return []

    async def run(self):
        """Run interactive bot (long polling)."""
        logger.info("Starting Telegram status bot (interactive mode)")
        logger.info("Send commands to your bot on Telegram")

        while True:
            try:
                updates = self.get_updates()

                for update in updates:
                    self.last_update_id = update.get("update_id", self.last_update_id)

                    message = update.get("message", {})
                    text = message.get("text", "")
                    from_chat_id = str(message.get("chat", {}).get("id", ""))

                    # Only process commands
                    if text.startswith("/"):
                        logger.info(f"Received command: {text} from {from_chat_id}")

                        response = self.process_command(text)
                        self.telegram.send_message(response, chat_id=from_chat_id)

                await asyncio.sleep(1)

            except KeyboardInterrupt:
                logger.info("Stopping bot...")
                break
            except Exception as e:
                logger.error(f"Error in bot loop: {e}")
                await asyncio.sleep(5)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Telegram status bot")
    parser.add_argument(
        "--account-id",
        type=str,
        default="868e0dd8-37f5-43ea-a956-7cc05e6bad66",
        help="Paper trading account ID",
    )
    parser.add_argument(
        "--symbol", type=str, default="BNB_USDT", help="Trading pair"
    )
    parser.add_argument(
        "--db",
        type=str,
        default=str(project_root / "data" / "jarvis_trading.db"),
        help="Database path",
    )
    parser.add_argument("--command", type=str, help="Send single command and exit")

    args = parser.parse_args()

    # Get Telegram config from env
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        print("❌ Telegram configuration not found in .env")
        print("   Run: python scripts/setup_telegram.py")
        sys.exit(1)

    # Create bot
    bot = TelegramStatusBot(
        account_id=args.account_id,
        symbol=args.symbol,
        db_path=args.db,
        bot_token=bot_token,
        chat_id=chat_id,
    )

    # Single command or interactive mode
    if args.command:
        response = bot.process_command(args.command)
        print(response)
        bot.telegram.send_message(response)
    else:
        asyncio.run(bot.run())


if __name__ == "__main__":
    main()
