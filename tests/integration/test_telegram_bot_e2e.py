"""
End-to-End Integration Tests for Telegram Bot
Tests the complete bot interaction flow with trading system.
"""

import unittest
import tempfile
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch, AsyncMock, Mock
from pathlib import Path
import sqlite3

from telegram import Update, Message, Chat, User, Bot
from telegram.ext import Application, ContextTypes

from src.infrastructure.telegram.bot_manager import BotManager
from src.infrastructure.telegram.handlers.command_handlers import CommandHandlers
from src.infrastructure.telegram.formatters.message_formatter import MessageFormatter
from src.domain.trading.paper_trading_service import PaperTradingService


class TestTelegramBotE2E(unittest.TestCase):
    """Test complete Telegram bot integration."""

    def setUp(self):
        """Set up test environment."""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_db.name

        # Initialize database
        self._init_database()

        # Mock Telegram components
        self.mock_bot = MagicMock(spec=Bot)
        self.mock_update = MagicMock(spec=Update)
        self.mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

        # Setup mock message
        self.mock_message = MagicMock(spec=Message)
        self.mock_chat = MagicMock(spec=Chat)
        self.mock_user = MagicMock(spec=User)

        self.mock_chat.id = 123456789
        self.mock_user.username = 'testuser'
        self.mock_user.id = 987654321

        self.mock_message.chat = self.mock_chat
        self.mock_message.from_user = self.mock_user
        self.mock_update.effective_chat = self.mock_chat
        self.mock_update.effective_user = self.mock_user
        self.mock_update.message = self.mock_message

        # Mock reply methods as async
        self.mock_message.reply_text = AsyncMock()
        self.mock_message.reply_photo = AsyncMock()

        # Initialize services
        self.paper_trading = PaperTradingService(
            db_path=self.db_path,
            initial_balance=Decimal('10000')
        )

        # Create test account
        self.account_id = 'bot-test-account'
        self.paper_trading.create_account(self.account_id, Decimal('10000'))

        # Initialize bot components
        self.mock_client = MagicMock()
        self.formatter = MessageFormatter()

        self.command_handlers = CommandHandlers(
            db_path=self.db_path,
            account_id=self.account_id,
            client=self.mock_client,
            formatter=self.formatter
        )

    def tearDown(self):
        """Clean up test environment."""
        self.temp_db.close()
        Path(self.db_path).unlink(missing_ok=True)

    def _init_database(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create necessary tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id TEXT PRIMARY KEY,
                balance REAL,
                equity REAL,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id TEXT,
                symbol TEXT,
                side TEXT,
                quantity REAL,
                entry_price REAL,
                current_price REAL,
                stop_loss REAL,
                take_profit TEXT,
                status TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id TEXT,
                symbol TEXT,
                added_at TIMESTAMP,
                UNIQUE(account_id, symbol)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                type TEXT,
                strength TEXT,
                confidence REAL,
                price REAL,
                source TEXT,
                timestamp TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    async def test_start_command_flow(self):
        """Test /start command flow."""
        # Execute start command
        await self.command_handlers.start(self.mock_update, self.mock_context)

        # Verify welcome message sent
        self.mock_message.reply_text.assert_called_once()
        call_args = self.mock_message.reply_text.call_args
        message_text = call_args[0][0]

        # Check message contains expected elements
        self.assertIn('Welcome', message_text)
        self.assertIn('JARVIS', message_text)

    async def test_portfolio_command_flow(self):
        """Test /portfolio command with positions."""
        # Setup: Add some positions
        self.paper_trading.open_position(
            account_id=self.account_id,
            symbol='BTCUSDT',
            side='LONG',
            quantity=Decimal('0.01'),
            entry_price=Decimal('50000'),
            stop_loss=Decimal('49000'),
            take_profit=[Decimal('52000')]
        )

        self.paper_trading.update_position_price(
            self.account_id,
            'BTCUSDT',
            Decimal('51000')
        )

        # Execute portfolio command
        await self.command_handlers.portfolio(self.mock_update, self.mock_context)

        # Verify portfolio message sent
        self.mock_message.reply_text.assert_called()
        call_args = self.mock_message.reply_text.call_args
        message_text = call_args[0][0]

        # Check message contains portfolio details
        self.assertIn('Portfolio', message_text)
        self.assertIn('Balance', message_text)
        self.assertIn('BTCUSDT', message_text)
        self.assertIn('LONG', message_text)

    async def test_watchlist_command_flow(self):
        """Test /watchlist command flow."""
        # Add symbols to watchlist
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
        for symbol in symbols:
            cursor.execute(
                "INSERT INTO watchlist (account_id, symbol, added_at) VALUES (?, ?, ?)",
                (self.account_id, symbol, datetime.now(timezone.utc))
            )

        conn.commit()
        conn.close()

        # Mock market data
        self.mock_client.get_ticker.side_effect = [
            {'symbol': 'BTCUSDT', 'lastPrice': '50000', 'priceChangePercent': '2.5'},
            {'symbol': 'ETHUSDT', 'lastPrice': '3000', 'priceChangePercent': '-1.2'},
            {'symbol': 'BNBUSDT', 'lastPrice': '400', 'priceChangePercent': '0.8'}
        ]

        # Execute watchlist command
        await self.command_handlers.watchlist(self.mock_update, self.mock_context)

        # Verify watchlist message sent
        self.mock_message.reply_text.assert_called()
        call_args = self.mock_message.reply_text.call_args
        message_text = call_args[0][0]

        # Check message contains watchlist items
        self.assertIn('Watchlist', message_text)
        for symbol in symbols:
            self.assertIn(symbol, message_text)

    async def test_signals_command_flow(self):
        """Test /signals command flow."""
        # Add test signals to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        signals_data = [
            ('BTCUSDT', 'BUY', 'STRONG', 0.85, 50000, 'Fibonacci'),
            ('ETHUSDT', 'SELL', 'MEDIUM', 0.65, 3000, 'RSI'),
            ('BNBUSDT', 'NEUTRAL', 'WEAK', 0.35, 400, 'MA_Crossover')
        ]

        for signal in signals_data:
            cursor.execute(
                """INSERT INTO signals
                   (symbol, type, strength, confidence, price, source, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (*signal, datetime.now(timezone.utc))
            )

        conn.commit()
        conn.close()

        # Execute signals command
        await self.command_handlers.signals(self.mock_update, self.mock_context)

        # Verify signals message sent
        self.mock_message.reply_text.assert_called()
        call_args = self.mock_message.reply_text.call_args
        message_text = call_args[0][0]

        # Check message contains signals
        self.assertIn('Signals', message_text)
        self.assertIn('BUY', message_text)
        self.assertIn('SELL', message_text)
        self.assertIn('Fibonacci', message_text)

    async def test_complete_trading_flow_via_commands(self):
        """Test complete trading flow through bot commands."""
        # Step 1: Check initial status
        await self.command_handlers.status(self.mock_update, self.mock_context)

        status_calls = self.mock_message.reply_text.call_count
        self.assertGreater(status_calls, 0)

        # Step 2: View empty portfolio
        await self.command_handlers.portfolio(self.mock_update, self.mock_context)

        # Step 3: Simulate buy command (manual trade)
        self.mock_message.text = '/buy BTCUSDT 0.01'

        # Mock price for buy
        self.mock_client.get_ticker.return_value = {
            'symbol': 'BTCUSDT',
            'lastPrice': '50000'
        }

        # Create buy handler
        from src.infrastructure.telegram.handlers.message_handlers import MessageHandlers
        message_handlers = MessageHandlers(
            db_path=self.db_path,
            account_id=self.account_id,
            client=self.mock_client,
            formatter=self.formatter
        )

        await message_handlers.buy_market(self.mock_update, self.mock_context)

        # Verify trade confirmation sent
        last_call = self.mock_message.reply_text.call_args_list[-1]
        trade_message = last_call[0][0]
        self.assertIn('Trade', trade_message)

        # Step 4: Check portfolio with position
        await self.command_handlers.portfolio(self.mock_update, self.mock_context)

        portfolio_call = self.mock_message.reply_text.call_args_list[-1]
        portfolio_message = portfolio_call[0][0]

        self.assertIn('BTCUSDT', portfolio_message)
        self.assertIn('0.01', portfolio_message)

        # Step 5: Simulate price change and check P&L
        self.paper_trading.update_position_price(
            self.account_id,
            'BTCUSDT',
            Decimal('51000')
        )

        await self.command_handlers.portfolio(self.mock_update, self.mock_context)

        updated_portfolio = self.mock_message.reply_text.call_args_list[-1][0][0]
        self.assertIn('+', updated_portfolio)  # Should show profit

    async def test_error_handling_flow(self):
        """Test error handling in bot commands."""
        # Test with invalid account (database error simulation)
        self.command_handlers.account_id = 'non-existent-account'

        # Try to get portfolio - should handle error gracefully
        await self.command_handlers.portfolio(self.mock_update, self.mock_context)

        # Verify error message sent
        self.mock_message.reply_text.assert_called()
        last_call = self.mock_message.reply_text.call_args
        error_message = last_call[0][0]

        # Should contain error indication
        self.assertTrue(
            'error' in error_message.lower() or
            'no account' in error_message.lower() or
            'not found' in error_message.lower()
        )

    def test_bot_initialization_and_configuration(self):
        """Test bot manager initialization and configuration."""
        with patch('src.infrastructure.telegram.bot_manager.load_dotenv'):
            with patch('src.infrastructure.telegram.bot_manager.os.getenv', return_value='test_token'):
                with patch('src.infrastructure.telegram.bot_manager.BinanceRESTClient'):

                    bot_manager = BotManager(token='test_token')

                    # Verify components initialized
                    self.assertIsNotNone(bot_manager.token)
                    self.assertIsNotNone(bot_manager.client)
                    self.assertIsNotNone(bot_manager.formatter)
                    self.assertIsNotNone(bot_manager.command_handlers)
                    self.assertIsNotNone(bot_manager.callback_handlers)
                    self.assertIsNotNone(bot_manager.message_handlers)

                    # Verify default configuration
                    self.assertEqual(bot_manager.db_path, 'data/jarvis_trading.db')
                    self.assertEqual(bot_manager.account_id, '868e0dd8-37f5-43ea-a956-7cc05e6bad66')


class TestBotMessageFormatting(unittest.TestCase):
    """Test bot message formatting for different scenarios."""

    def setUp(self):
        """Set up test environment."""
        self.formatter = MessageFormatter()

    def test_large_portfolio_formatting(self):
        """Test formatting of large portfolio with multiple positions."""
        account_data = {
            'balance': Decimal('100000'),
            'equity': Decimal('125000'),
            'margin_used': Decimal('25000'),
            'positions': [
                {
                    'symbol': f'COIN{i}USDT',
                    'side': 'LONG' if i % 2 == 0 else 'SHORT',
                    'quantity': Decimal(str(0.1 * i)),
                    'entry_price': Decimal(str(1000 * i)),
                    'current_price': Decimal(str(1000 * i * 1.1)),
                    'pnl': Decimal(str(100 * i)),
                    'pnl_percentage': Decimal(str(10))
                }
                for i in range(1, 11)  # 10 positions
            ]
        }

        formatted = self.formatter.format_portfolio(account_data)

        # Check all positions included
        for i in range(1, 11):
            self.assertIn(f'COIN{i}USDT', formatted)

        # Check totals
        self.assertIn('100,000', formatted)  # Balance
        self.assertIn('125,000', formatted)  # Equity

    def test_signal_alert_formatting(self):
        """Test formatting of trading signal alerts."""
        signals = [
            {
                'type': 'BUY',
                'symbol': 'BTCUSDT',
                'price': Decimal('50000'),
                'confidence': Decimal('0.92'),
                'strength': 'STRONG',
                'source': 'Fibonacci',
                'metadata': {
                    'golden_zone': True,
                    'trend': 'BULLISH'
                }
            },
            {
                'type': 'SELL',
                'symbol': 'ETHUSDT',
                'price': Decimal('3000'),
                'confidence': Decimal('0.75'),
                'strength': 'MEDIUM',
                'source': 'RSI',
                'metadata': {
                    'rsi_value': 78,
                    'overbought': True
                }
            }
        ]

        for signal in signals:
            formatted = self.formatter.format_signal(signal)

            # Check essential elements
            self.assertIn(signal['type'], formatted)
            self.assertIn(signal['symbol'], formatted)
            self.assertIn(signal['strength'], formatted)
            self.assertIn(f"{signal['confidence'] * 100:.0f}%", formatted)

    def test_error_message_formatting(self):
        """Test formatting of various error messages."""
        errors = [
            "Connection timeout",
            "Insufficient balance",
            "Position not found",
            "Invalid symbol",
            "API rate limit exceeded"
        ]

        for error in errors:
            formatted = self.formatter.format_error(error)

            # Check error formatting
            self.assertIn('Error', formatted)
            self.assertIn(error, formatted)
            self.assertIn('❌', formatted)  # Error emoji


# Run async tests helper
def async_test(coro):
    """Decorator to run async tests."""
    def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro(*args, **kwargs))
    return wrapper


# Apply decorator to async test methods
for test_class in [TestTelegramBotE2E]:
    for attr_name in dir(test_class):
        attr = getattr(test_class, attr_name)
        if callable(attr) and attr_name.startswith('test_') and asyncio.iscoroutinefunction(attr):
            setattr(test_class, attr_name, async_test(attr))


if __name__ == '__main__':
    unittest.main()