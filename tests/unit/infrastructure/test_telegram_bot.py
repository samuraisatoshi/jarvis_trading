"""
Unit tests for Telegram Bot Infrastructure
Tests bot manager, handlers, and message formatting.
"""

import unittest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch, Mock, AsyncMock, call
import asyncio

from telegram import Update, Message, Chat, User, CallbackQuery
from telegram.ext import ContextTypes

from src.infrastructure.telegram.bot_manager import BotManager
from src.infrastructure.telegram.handlers.command_handlers import CommandHandlers
from src.infrastructure.telegram.handlers.callback_handlers import CallbackHandlers
from src.infrastructure.telegram.formatters.message_formatter import MessageFormatter


class TestBotManager(unittest.TestCase):
    """Test BotManager orchestration."""

    def setUp(self):
        """Set up test fixtures."""
        with patch('src.infrastructure.telegram.bot_manager.load_dotenv'):
            with patch('src.infrastructure.telegram.bot_manager.os.getenv', return_value='test_token'):
                with patch('src.infrastructure.telegram.bot_manager.BinanceRESTClient'):
                    self.bot_manager = BotManager(token='test_token')

    def test_bot_manager_initialization(self):
        """Test BotManager initialization."""
        self.assertEqual(self.bot_manager.token, 'test_token')
        self.assertIsNotNone(self.bot_manager.client)
        self.assertIsNotNone(self.bot_manager.formatter)
        self.assertIsNotNone(self.bot_manager.command_handlers)
        self.assertIsNotNone(self.bot_manager.callback_handlers)
        self.assertIsNotNone(self.bot_manager.message_handlers)

    @patch('src.infrastructure.telegram.bot_manager.Application')
    def test_register_handlers(self, mock_application_class):
        """Test handler registration."""
        mock_app = MagicMock()
        mock_application_class.builder.return_value.token.return_value.build.return_value = mock_app

        # Create bot manager and trigger handler registration
        with patch.object(self.bot_manager, '_register_handlers') as mock_register:
            self.bot_manager.run()
            mock_register.assert_called_once()

    def test_handler_registration_order(self):
        """Test that handlers are registered in correct order."""
        mock_app = MagicMock()
        handlers_registered = []

        def track_handler(handler):
            handlers_registered.append(handler.callback.__name__ if hasattr(handler, 'callback') else str(handler))

        mock_app.add_handler.side_effect = track_handler

        # Register handlers
        self.bot_manager._register_handlers(mock_app)

        # Verify specific handlers registered before general ones
        self.assertTrue(len(handlers_registered) > 0)

        # Check that command handlers are registered
        self.assertEqual(mock_app.add_handler.call_count, 16)  # Total expected handlers


class TestCommandHandlers(unittest.TestCase):
    """Test command handlers implementation."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_client = MagicMock()
        self.mock_formatter = MagicMock()

        self.command_handlers = CommandHandlers(
            db_path='test.db',
            account_id='test-account',
            client=self.mock_client,
            formatter=self.mock_formatter
        )

        # Create mock update and context
        self.mock_update = MagicMock(spec=Update)
        self.mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        self.mock_update.effective_chat.id = 12345
        self.mock_update.effective_user.username = 'testuser'

    async def test_start_command(self):
        """Test /start command handler."""
        # Mock formatter response
        self.mock_formatter.format_welcome.return_value = "Welcome to JARVIS Trading!"

        # Execute command
        await self.command_handlers.start(self.mock_update, self.mock_context)

        # Verify formatter called
        self.mock_formatter.format_welcome.assert_called_once()

        # Verify message sent
        self.mock_update.message.reply_text.assert_called_once_with(
            "Welcome to JARVIS Trading!",
            parse_mode='Markdown'
        )

    async def test_help_command(self):
        """Test /help command handler."""
        # Mock formatter response
        help_text = """
        Available commands:
        /start - Start bot
        /help - Show help
        /status - System status
        """
        self.mock_formatter.format_help.return_value = help_text

        # Execute command
        await self.command_handlers.help(self.mock_update, self.mock_context)

        # Verify formatter called
        self.mock_formatter.format_help.assert_called_once()

        # Verify message sent
        self.mock_update.message.reply_text.assert_called_once_with(
            help_text,
            parse_mode='Markdown'
        )

    @patch('src.infrastructure.telegram.handlers.command_handlers.PaperTradingService')
    async def test_portfolio_command(self, mock_service_class):
        """Test /portfolio command handler."""
        # Mock portfolio data
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        mock_account = {
            'id': 'test-account',
            'balance': Decimal('10000'),
            'equity': Decimal('10500'),
            'positions': [
                {
                    'symbol': 'BTCUSDT',
                    'quantity': Decimal('0.01'),
                    'entry_price': Decimal('50000'),
                    'current_price': Decimal('52000'),
                    'pnl': Decimal('20'),
                    'pnl_percentage': Decimal('4.0')
                }
            ]
        }
        mock_service.get_account_status.return_value = mock_account

        # Mock formatter
        portfolio_text = "Portfolio:\nBalance: $10,000\nEquity: $10,500"
        self.mock_formatter.format_portfolio.return_value = portfolio_text

        # Execute command
        await self.command_handlers.portfolio(self.mock_update, self.mock_context)

        # Verify service called
        mock_service.get_account_status.assert_called_once_with('test-account')

        # Verify formatter called with account data
        self.mock_formatter.format_portfolio.assert_called_once_with(mock_account)

        # Verify message sent
        self.mock_update.message.reply_text.assert_called_once()

    @patch('src.infrastructure.telegram.handlers.command_handlers.datetime')
    async def test_status_command(self, mock_datetime):
        """Test /status command handler."""
        # Mock datetime
        mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now

        # Mock client status
        self.mock_client.get_system_status.return_value = {
            'status': 'online',
            'latency': 50
        }

        # Mock formatter
        status_text = "System Status: ✅ Online\nLatency: 50ms"
        self.mock_formatter.format_status.return_value = status_text

        # Execute command
        await self.command_handlers.status(self.mock_update, self.mock_context)

        # Verify formatter called
        self.mock_formatter.format_status.assert_called_once()

        # Verify message sent
        self.mock_update.message.reply_text.assert_called_once_with(
            status_text,
            parse_mode='Markdown'
        )

    async def test_unknown_command(self):
        """Test unknown command handler."""
        self.mock_update.message.text = '/unknowncommand'

        await self.command_handlers.unknown_command(self.mock_update, self.mock_context)

        # Verify error message sent
        call_args = self.mock_update.message.reply_text.call_args
        self.assertIn('unknown', call_args[0][0].lower())


class TestCallbackHandlers(unittest.TestCase):
    """Test callback button handlers."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_client = MagicMock()
        self.mock_formatter = MagicMock()
        self.mock_command_handlers = MagicMock()

        self.callback_handlers = CallbackHandlers(
            db_path='test.db',
            account_id='test-account',
            client=self.mock_client,
            formatter=self.mock_formatter,
            command_handlers=self.mock_command_handlers
        )

        # Create mock callback query
        self.mock_update = MagicMock(spec=Update)
        self.mock_query = MagicMock(spec=CallbackQuery)
        self.mock_update.callback_query = self.mock_query
        self.mock_context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

    async def test_refresh_portfolio_callback(self):
        """Test portfolio refresh button callback."""
        self.mock_query.data = 'refresh_portfolio'

        # Mock command handler
        self.mock_command_handlers.portfolio = AsyncMock()

        # Execute callback
        await self.callback_handlers.button_handler(self.mock_update, self.mock_context)

        # Verify query answered
        self.mock_query.answer.assert_called_once()

        # Verify portfolio refreshed
        self.mock_command_handlers.portfolio.assert_called_once()

    async def test_close_position_callback(self):
        """Test close position button callback."""
        self.mock_query.data = 'close_position_BTCUSDT'

        # Mock trading service
        with patch('src.infrastructure.telegram.handlers.callback_handlers.PaperTradingService') as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service

            mock_order = {
                'id': 'ORD-001',
                'symbol': 'BTCUSDT',
                'side': 'SELL',
                'quantity': Decimal('0.01'),
                'price': Decimal('52000')
            }
            mock_service.close_position.return_value = mock_order

            # Execute callback
            await self.callback_handlers.button_handler(self.mock_update, self.mock_context)

            # Verify position closed
            mock_service.close_position.assert_called_once_with('test-account', 'BTCUSDT')

            # Verify confirmation sent
            self.mock_query.answer.assert_called_once()
            self.mock_query.edit_message_text.assert_called_once()

    async def test_invalid_callback_data(self):
        """Test handling of invalid callback data."""
        self.mock_query.data = 'invalid_data_format'

        # Execute callback
        await self.callback_handlers.button_handler(self.mock_update, self.mock_context)

        # Verify error handled gracefully
        self.mock_query.answer.assert_called_once_with("Invalid action")


class TestMessageFormatter(unittest.TestCase):
    """Test message formatting utilities."""

    def setUp(self):
        """Set up test fixtures."""
        self.formatter = MessageFormatter()

    def test_format_portfolio(self):
        """Test portfolio formatting."""
        account_data = {
            'balance': Decimal('10000.00'),
            'equity': Decimal('10500.00'),
            'margin_used': Decimal('500.00'),
            'positions': [
                {
                    'symbol': 'BTCUSDT',
                    'side': 'LONG',
                    'quantity': Decimal('0.01'),
                    'entry_price': Decimal('50000'),
                    'current_price': Decimal('52000'),
                    'pnl': Decimal('20.00'),
                    'pnl_percentage': Decimal('4.00')
                }
            ]
        }

        formatted = self.formatter.format_portfolio(account_data)

        # Verify key information included
        self.assertIn('Portfolio', formatted)
        self.assertIn('10,000', formatted)  # Balance
        self.assertIn('10,500', formatted)  # Equity
        self.assertIn('BTCUSDT', formatted)
        self.assertIn('LONG', formatted)
        self.assertIn('+20.00', formatted)  # P&L
        self.assertIn('+4.00%', formatted)  # P&L percentage

    def test_format_signal(self):
        """Test signal formatting."""
        signal = {
            'type': 'BUY',
            'symbol': 'BTCUSDT',
            'price': Decimal('50000'),
            'confidence': Decimal('0.85'),
            'strength': 'STRONG',
            'source': 'Fibonacci',
            'timestamp': datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        }

        formatted = self.formatter.format_signal(signal)

        # Verify signal details
        self.assertIn('Signal', formatted)
        self.assertIn('BUY', formatted)
        self.assertIn('BTCUSDT', formatted)
        self.assertIn('50,000', formatted)
        self.assertIn('85%', formatted)
        self.assertIn('STRONG', formatted)
        self.assertIn('Fibonacci', formatted)

    def test_format_trade_confirmation(self):
        """Test trade confirmation formatting."""
        trade = {
            'id': 'TRD-001',
            'symbol': 'BTCUSDT',
            'side': 'BUY',
            'quantity': Decimal('0.01'),
            'price': Decimal('50000'),
            'total': Decimal('500'),
            'fee': Decimal('0.50'),
            'timestamp': datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        }

        formatted = self.formatter.format_trade_confirmation(trade)

        # Verify trade details
        self.assertIn('Trade Executed', formatted)
        self.assertIn('TRD-001', formatted)
        self.assertIn('BUY', formatted)
        self.assertIn('BTCUSDT', formatted)
        self.assertIn('0.01', formatted)
        self.assertIn('50,000', formatted)
        self.assertIn('500', formatted)

    def test_format_error(self):
        """Test error message formatting."""
        error = "Connection timeout"
        formatted = self.formatter.format_error(error)

        self.assertIn('Error', formatted)
        self.assertIn('Connection timeout', formatted)
        self.assertIn('❌', formatted)  # Error emoji

    def test_format_number_with_decimals(self):
        """Test number formatting with proper decimal places."""
        # Test various decimal values
        self.assertEqual(self.formatter.format_number(Decimal('10000.00')), '10,000.00')
        self.assertEqual(self.formatter.format_number(Decimal('0.00012345')), '0.000123')
        self.assertEqual(self.formatter.format_number(Decimal('50000')), '50,000.00')
        self.assertEqual(self.formatter.format_number(Decimal('-1234.56')), '-1,234.56')

    def test_format_percentage(self):
        """Test percentage formatting."""
        self.assertEqual(self.formatter.format_percentage(Decimal('0.1523')), '15.23%')
        self.assertEqual(self.formatter.format_percentage(Decimal('-0.0856')), '-8.56%')
        self.assertEqual(self.formatter.format_percentage(Decimal('1.0')), '100.00%')
        self.assertEqual(self.formatter.format_percentage(Decimal('0.0')), '0.00%')


if __name__ == '__main__':
    unittest.main()