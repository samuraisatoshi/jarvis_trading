#!/usr/bin/env python3
"""
Telegram Bot Setup Script

Interactive script to configure Telegram bot for trading notifications.

This script helps you:
1. Create a new Telegram bot via BotFather
2. Get your bot token
3. Find your chat ID
4. Test the connection
5. Save configuration to .env file

Usage:
    python scripts/setup_telegram.py

    # Test existing configuration
    python scripts/setup_telegram.py --test
"""

import sys
import os
from pathlib import Path
from typing import Optional
import argparse

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.notifications.telegram_notifier import TelegramNotifier
from loguru import logger


class TelegramSetup:
    """Interactive Telegram bot setup."""

    def __init__(self):
        self.env_path = project_root / ".env"
        self.env_example_path = project_root / ".env.example"

    def print_instructions(self):
        """Print setup instructions."""
        print("\n" + "=" * 80)
        print("🤖 TELEGRAM BOT SETUP - TRADING NOTIFICATIONS")
        print("=" * 80 + "\n")

        print("📋 STEP 1: Create a Telegram Bot")
        print("-" * 40)
        print("1. Open Telegram and search for @BotFather")
        print("2. Send /newbot to BotFather")
        print("3. Follow instructions to name your bot")
        print("4. BotFather will give you a TOKEN - copy it!\n")

        print("📋 STEP 2: Get Your Chat ID")
        print("-" * 40)
        print("1. Send a message to your new bot (any message)")
        print("2. Open this URL in browser (replace YOUR_TOKEN):")
        print("   https://api.telegram.org/botYOUR_TOKEN/getUpdates")
        print("3. Find 'chat':{'id': YOUR_CHAT_ID} in the response")
        print("4. Copy the chat ID number\n")

        print("📋 STEP 3: Run This Script")
        print("-" * 40)
        print("   python scripts/setup_telegram.py\n")

    def load_existing_env(self) -> dict:
        """Load existing .env configuration."""
        config = {}

        if not self.env_path.exists():
            return config

        with open(self.env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    config[key.strip()] = value.strip()

        return config

    def save_to_env(self, bot_token: str, chat_id: str, authorized_chat_ids: str):
        """Save Telegram configuration to .env file."""
        # Load existing config
        config = self.load_existing_env()

        # Update Telegram keys
        config["TELEGRAM_BOT_TOKEN"] = bot_token
        config["TELEGRAM_CHAT_ID"] = chat_id
        config["TELEGRAM_AUTHORIZED_CHAT_IDS"] = authorized_chat_ids

        # Write back to .env
        with open(self.env_path, "w") as f:
            f.write("# Telegram Bot Configuration\n")
            f.write(f"TELEGRAM_BOT_TOKEN={bot_token}\n")
            f.write(f"TELEGRAM_CHAT_ID={chat_id}\n")
            f.write(f"TELEGRAM_AUTHORIZED_CHAT_IDS={authorized_chat_ids}\n\n")

            # Write other existing config
            for key, value in config.items():
                if not key.startswith("TELEGRAM_"):
                    f.write(f"{key}={value}\n")

        print(f"✅ Configuration saved to {self.env_path}")

    def test_bot(self, bot_token: str, chat_id: str) -> bool:
        """Test Telegram bot connection."""
        try:
            print("\n🔧 Testing Telegram bot...")

            notifier = TelegramNotifier(
                bot_token=bot_token, chat_id=chat_id, parse_mode="HTML"
            )

            # Test connection
            if not notifier.test_connection():
                print("❌ Failed to connect to Telegram bot")
                return False

            # Send test message
            test_message = (
                "🎉 <b>Setup Successful!</b>\n\n"
                "Your Telegram bot is configured and ready to send trading notifications.\n\n"
                "✅ Connection tested\n"
                "✅ Messages working\n\n"
                "You're all set! 🚀"
            )

            if notifier.send_message(test_message):
                print("✅ Test message sent successfully!")
                print(f"   Check your Telegram chat: {chat_id}")
                return True
            else:
                print("❌ Failed to send test message")
                return False

        except Exception as e:
            print(f"❌ Error testing bot: {e}")
            return False

    def interactive_setup(self):
        """Run interactive setup."""
        self.print_instructions()

        print("=" * 80)
        print("📝 CONFIGURATION")
        print("=" * 80 + "\n")

        # Get bot token
        bot_token = input("Enter your Bot Token (from BotFather): ").strip()
        if not bot_token:
            print("❌ Bot token is required")
            return False

        # Get chat ID
        chat_id = input("Enter your Chat ID (numeric): ").strip()
        if not chat_id:
            print("❌ Chat ID is required")
            return False

        # Authorized chat IDs (comma-separated)
        print("\n(Optional) Enter additional authorized chat IDs")
        print("If you want to allow multiple users, enter their chat IDs separated by commas")
        print("Leave blank to only allow the main chat ID")
        additional_chats = input("Additional chat IDs (optional): ").strip()

        if additional_chats:
            authorized_chat_ids = f"{chat_id},{additional_chats}"
        else:
            authorized_chat_ids = chat_id

        print("\n" + "=" * 80)
        print("📋 CONFIGURATION SUMMARY")
        print("=" * 80)
        print(f"Bot Token: {bot_token[:10]}...{bot_token[-10:]}")
        print(f"Chat ID: {chat_id}")
        print(f"Authorized Chat IDs: {authorized_chat_ids}")
        print("=" * 80 + "\n")

        confirm = input("Save this configuration? (y/n): ").strip().lower()
        if confirm != "y":
            print("❌ Setup cancelled")
            return False

        # Test before saving
        if not self.test_bot(bot_token, chat_id):
            print("\n⚠️ Bot test failed. Save anyway? (y/n): ", end="")
            if input().strip().lower() != "y":
                print("❌ Setup cancelled")
                return False

        # Save to .env
        self.save_to_env(bot_token, chat_id, authorized_chat_ids)

        print("\n" + "=" * 80)
        print("✅ SETUP COMPLETE!")
        print("=" * 80)
        print("\nYour Telegram bot is now configured.")
        print("\nNext steps:")
        print("1. Run paper trading with Telegram notifications:")
        print("   python scripts/trading_with_telegram.py --daemon")
        print("\n2. Check bot status:")
        print("   python scripts/telegram_status_bot.py")
        print("\n3. Monitor trading:")
        print("   python scripts/monitor_paper_trading.py")
        print("=" * 80 + "\n")

        return True

    def test_existing_config(self):
        """Test existing Telegram configuration."""
        config = self.load_existing_env()

        bot_token = config.get("TELEGRAM_BOT_TOKEN")
        chat_id = config.get("TELEGRAM_CHAT_ID")

        if not bot_token or not chat_id:
            print("❌ Telegram configuration not found in .env")
            print("   Run: python scripts/setup_telegram.py")
            return False

        print("Testing existing Telegram configuration...")
        return self.test_bot(bot_token, chat_id)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Telegram bot setup")
    parser.add_argument(
        "--test", action="store_true", help="Test existing configuration"
    )

    args = parser.parse_args()

    setup = TelegramSetup()

    if args.test:
        success = setup.test_existing_config()
    else:
        success = setup.interactive_setup()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
