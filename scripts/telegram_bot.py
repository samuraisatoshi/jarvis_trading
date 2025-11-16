#!/usr/bin/env python3
"""
Telegram Trading Bot - Refactored Version
Cleaner architecture with dependency injection and modular design.

This is the new entrypoint using the refactored module structure.
Original: scripts/telegram_bot_hybrid.py.backup
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.telegram import create_bot


def main():
    """Main entry point."""
    try:
        bot = create_bot()
        bot.run()
    except KeyboardInterrupt:
        print("\nBot stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
