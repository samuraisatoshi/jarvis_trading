"""
Unit tests for Application Orchestrators
Tests workflow orchestration and coordination logic.
"""

import unittest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch, Mock, call
import asyncio

from src.application.orchestrators.fibonacci_trading_orchestrator import (
    FibonacciTradingOrchestrator
)
from src.application.orchestrators.paper_trading_orchestrator import (
    PaperTradingOrchestrator
)
from src.strategies.models import Signal, SignalType, SignalStrength
from src.domain.models.trading_models import Order, OrderStatus, OrderType


class TestFibonacciTradingOrchestrator(unittest.TestCase):
    """Test FibonacciTradingOrchestrator implementation."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock dependencies
        self.mock_strategy = MagicMock()
        self.mock_trading_service = MagicMock()
        self.mock_risk_manager = MagicMock()
        self.mock_notification_service = MagicMock()
        self.mock_logger = MagicMock()

        self.orchestrator = FibonacciTradingOrchestrator(
            strategy=self.mock_strategy,
            trading_service=self.mock_trading_service,
            risk_manager=self.mock_risk_manager,
            notification_service=self.mock_notification_service,
            logger=self.mock_logger,
            account_id='test-account-123',
            symbol='BTCUSDT',
            timeframe='1h'
        )

    def test_orchestrator_initialization(self):
        """Test orchestrator initialization with dependencies."""
        self.assertEqual(self.orchestrator.account_id, 'test-account-123')
        self.assertEqual(self.orchestrator.symbol, 'BTCUSDT')
        self.assertEqual(self.orchestrator.timeframe, '1h')
        self.assertIsNotNone(self.orchestrator.strategy)
        self.assertIsNotNone(self.orchestrator.trading_service)
        self.assertIsNotNone(self.orchestrator.risk_manager)
        self.assertIsNotNone(self.orchestrator.notification_service)

    def test_execute_workflow_with_buy_signal(self):
        """Test complete workflow execution with buy signal."""
        # Setup mock signal
        mock_signal = Signal(
            type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            symbol='BTCUSDT',
            price=Decimal('50000'),
            confidence=Decimal('0.85'),
            timestamp=datetime.now(timezone.utc),
            metadata={'source': 'fibonacci'}
        )

        # Configure mocks
        self.mock_strategy.analyze.return_value = {
            'signal': mock_signal,
            'current_price': Decimal('50000'),
            'fibonacci_levels': MagicMock(),
            'trend': 'BULLISH'
        }

        self.mock_risk_manager.validate_trade.return_value = True
        self.mock_risk_manager.calculate_position_size.return_value = Decimal('0.01')

        mock_order = Order(
            id='ORD-001',
            symbol='BTCUSDT',
            side='BUY',
            type=OrderType.MARKET,
            quantity=Decimal('0.01'),
            price=Decimal('50000'),
            status=OrderStatus.FILLED,
            timestamp=datetime.now(timezone.utc)
        )
        self.mock_trading_service.place_order.return_value = mock_order

        # Execute workflow
        result = self.orchestrator.execute()

        # Verify calls
        self.mock_strategy.analyze.assert_called_once_with(
            symbol='BTCUSDT',
            timeframe='1h'
        )
        self.mock_risk_manager.validate_trade.assert_called_once()
        self.mock_trading_service.place_order.assert_called_once()
        self.mock_notification_service.send_notification.assert_called()

        # Verify result
        self.assertTrue(result['success'])
        self.assertEqual(result['signal'], mock_signal)
        self.assertEqual(result['order'], mock_order)

    def test_execute_workflow_with_neutral_signal(self):
        """Test workflow with neutral signal (no action)."""
        # Setup mock neutral signal
        mock_signal = Signal(
            type=SignalType.NEUTRAL,
            strength=SignalStrength.WEAK,
            symbol='BTCUSDT',
            price=Decimal('50000'),
            confidence=Decimal('0.3'),
            timestamp=datetime.now(timezone.utc),
            metadata={'source': 'fibonacci'}
        )

        # Configure mocks
        self.mock_strategy.analyze.return_value = {
            'signal': mock_signal,
            'current_price': Decimal('50000'),
            'fibonacci_levels': MagicMock(),
            'trend': 'NEUTRAL'
        }

        # Execute workflow
        result = self.orchestrator.execute()

        # Verify no order was placed
        self.mock_trading_service.place_order.assert_not_called()

        # Verify result
        self.assertTrue(result['success'])
        self.assertEqual(result['signal'], mock_signal)
        self.assertIsNone(result.get('order'))

    def test_execute_workflow_risk_validation_failure(self):
        """Test workflow when risk validation fails."""
        # Setup mock signal
        mock_signal = Signal(
            type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            symbol='BTCUSDT',
            price=Decimal('50000'),
            confidence=Decimal('0.85'),
            timestamp=datetime.now(timezone.utc),
            metadata={'source': 'fibonacci'}
        )

        # Configure mocks
        self.mock_strategy.analyze.return_value = {
            'signal': mock_signal,
            'current_price': Decimal('50000'),
            'fibonacci_levels': MagicMock(),
            'trend': 'BULLISH'
        }

        # Risk validation fails
        self.mock_risk_manager.validate_trade.return_value = False

        # Execute workflow
        result = self.orchestrator.execute()

        # Verify no order was placed
        self.mock_trading_service.place_order.assert_not_called()

        # Verify notification was sent about risk rejection
        self.mock_notification_service.send_notification.assert_called()

        # Verify result
        self.assertFalse(result['success'])
        self.assertIn('risk validation failed', result.get('error', '').lower())

    def test_execute_workflow_with_retry_on_failure(self):
        """Test workflow retry mechanism on transient failures."""
        # Setup mock signal
        mock_signal = Signal(
            type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            symbol='BTCUSDT',
            price=Decimal('50000'),
            confidence=Decimal('0.85'),
            timestamp=datetime.now(timezone.utc),
            metadata={'source': 'fibonacci'}
        )

        # Configure mocks
        self.mock_strategy.analyze.return_value = {
            'signal': mock_signal,
            'current_price': Decimal('50000'),
            'fibonacci_levels': MagicMock(),
            'trend': 'BULLISH'
        }

        self.mock_risk_manager.validate_trade.return_value = True
        self.mock_risk_manager.calculate_position_size.return_value = Decimal('0.01')

        # First call fails, second succeeds
        mock_order = Order(
            id='ORD-002',
            symbol='BTCUSDT',
            side='BUY',
            type=OrderType.MARKET,
            quantity=Decimal('0.01'),
            price=Decimal('50000'),
            status=OrderStatus.FILLED,
            timestamp=datetime.now(timezone.utc)
        )
        self.mock_trading_service.place_order.side_effect = [
            Exception("Network error"),
            mock_order
        ]

        # Execute workflow with retry
        with patch.object(self.orchestrator, 'max_retries', 3):
            with patch.object(self.orchestrator, 'retry_delay', 0):
                result = self.orchestrator.execute()

        # Verify retry happened
        self.assertEqual(self.mock_trading_service.place_order.call_count, 2)

        # Verify success after retry
        self.assertTrue(result['success'])
        self.assertEqual(result['order'], mock_order)

    def test_position_management_stop_loss_triggered(self):
        """Test position management when stop loss is triggered."""
        # Setup existing position
        self.orchestrator.current_position = {
            'symbol': 'BTCUSDT',
            'side': 'LONG',
            'entry_price': Decimal('50000'),
            'quantity': Decimal('0.01'),
            'stop_loss': Decimal('49000'),
            'take_profit': [Decimal('52000'), Decimal('54000')]
        }

        # Current price below stop loss
        current_price = Decimal('48900')

        # Test stop loss check
        should_close = self.orchestrator.check_stop_loss(current_price)
        self.assertTrue(should_close)

        # Execute close position
        mock_close_order = Order(
            id='ORD-003',
            symbol='BTCUSDT',
            side='SELL',
            type=OrderType.MARKET,
            quantity=Decimal('0.01'),
            price=current_price,
            status=OrderStatus.FILLED,
            timestamp=datetime.now(timezone.utc)
        )
        self.mock_trading_service.close_position.return_value = mock_close_order

        result = self.orchestrator.close_position('stop_loss')

        # Verify close was executed
        self.mock_trading_service.close_position.assert_called_once()
        self.mock_notification_service.send_notification.assert_called()

        # Verify position cleared
        self.assertIsNone(self.orchestrator.current_position)

    def test_position_management_take_profit_triggered(self):
        """Test position management when take profit is triggered."""
        # Setup existing position
        self.orchestrator.current_position = {
            'symbol': 'BTCUSDT',
            'side': 'LONG',
            'entry_price': Decimal('50000'),
            'quantity': Decimal('0.01'),
            'stop_loss': Decimal('49000'),
            'take_profit': [Decimal('52000'), Decimal('54000')]
        }

        # Current price at first take profit
        current_price = Decimal('52100')

        # Test take profit check
        tp_hit = self.orchestrator.check_take_profit(current_price)
        self.assertTrue(tp_hit)

        # Execute partial close (50% at first target)
        mock_partial_order = Order(
            id='ORD-004',
            symbol='BTCUSDT',
            side='SELL',
            type=OrderType.MARKET,
            quantity=Decimal('0.005'),  # 50% of position
            price=current_price,
            status=OrderStatus.FILLED,
            timestamp=datetime.now(timezone.utc)
        )
        self.mock_trading_service.close_position.return_value = mock_partial_order

        result = self.orchestrator.close_position_partial(0.5)

        # Verify partial close
        self.mock_trading_service.close_position.assert_called()

        # Verify position updated
        self.assertEqual(self.orchestrator.current_position['quantity'], Decimal('0.005'))


class TestPaperTradingOrchestrator(unittest.TestCase):
    """Test PaperTradingOrchestrator implementation."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_paper_trading_service = MagicMock()
        self.mock_strategy = MagicMock()
        self.mock_metrics_service = MagicMock()
        self.mock_logger = MagicMock()

        self.orchestrator = PaperTradingOrchestrator(
            paper_trading_service=self.mock_paper_trading_service,
            strategy=self.mock_strategy,
            metrics_service=self.mock_metrics_service,
            logger=self.mock_logger,
            account_id='paper-account-456',
            initial_balance=Decimal('10000')
        )

    def test_paper_trading_initialization(self):
        """Test paper trading orchestrator initialization."""
        self.assertEqual(self.orchestrator.account_id, 'paper-account-456')
        self.assertEqual(self.orchestrator.initial_balance, Decimal('10000'))
        self.assertIsNotNone(self.orchestrator.paper_trading_service)
        self.assertIsNotNone(self.orchestrator.strategy)

    def test_execute_paper_trade(self):
        """Test executing paper trade."""
        # Setup mock signal
        mock_signal = Signal(
            type=SignalType.BUY,
            strength=SignalStrength.STRONG,
            symbol='BTCUSDT',
            price=Decimal('50000'),
            confidence=Decimal('0.85'),
            timestamp=datetime.now(timezone.utc),
            metadata={'source': 'test'}
        )

        self.mock_strategy.generate_signal.return_value = mock_signal

        # Mock paper trade execution
        mock_trade = {
            'id': 'PAPER-001',
            'symbol': 'BTCUSDT',
            'side': 'BUY',
            'quantity': Decimal('0.01'),
            'price': Decimal('50000'),
            'timestamp': datetime.now(timezone.utc)
        }
        self.mock_paper_trading_service.execute_trade.return_value = mock_trade

        # Execute
        result = self.orchestrator.execute_trade('BTCUSDT')

        # Verify
        self.mock_strategy.generate_signal.assert_called_once()
        self.mock_paper_trading_service.execute_trade.assert_called_once()
        self.mock_metrics_service.record_trade.assert_called_once()

        self.assertTrue(result['success'])
        self.assertEqual(result['trade'], mock_trade)

    def test_update_metrics(self):
        """Test metrics update."""
        # Mock account status
        mock_account = {
            'balance': Decimal('10500'),
            'equity': Decimal('10700'),
            'positions': [
                {
                    'symbol': 'BTCUSDT',
                    'quantity': Decimal('0.01'),
                    'entry_price': Decimal('50000'),
                    'current_price': Decimal('52000'),
                    'pnl': Decimal('20')
                }
            ]
        }
        self.mock_paper_trading_service.get_account_status.return_value = mock_account

        # Update metrics
        self.orchestrator.update_metrics()

        # Verify metrics recorded
        self.mock_metrics_service.update_balance.assert_called_with(Decimal('10500'))
        self.mock_metrics_service.update_equity.assert_called_with(Decimal('10700'))
        self.mock_metrics_service.update_positions.assert_called_with(mock_account['positions'])

    def test_performance_reporting(self):
        """Test performance report generation."""
        # Mock metrics
        mock_performance = {
            'total_return': Decimal('0.15'),  # 15%
            'win_rate': Decimal('0.65'),      # 65%
            'sharpe_ratio': Decimal('1.8'),
            'max_drawdown': Decimal('-0.12'),  # -12%
            'total_trades': 50,
            'winning_trades': 33,
            'losing_trades': 17
        }
        self.mock_metrics_service.calculate_performance.return_value = mock_performance

        # Generate report
        report = self.orchestrator.generate_performance_report()

        # Verify report contains key metrics
        self.assertIn('total_return', report)
        self.assertIn('win_rate', report)
        self.assertIn('sharpe_ratio', report)
        self.assertIn('max_drawdown', report)
        self.assertEqual(report['total_return'], Decimal('0.15'))
        self.assertEqual(report['win_rate'], Decimal('0.65'))

    def test_continuous_trading_loop(self):
        """Test continuous trading loop execution."""
        # Mock multiple signals
        signals = [
            Signal(type=SignalType.BUY, strength=SignalStrength.STRONG,
                  symbol='BTCUSDT', price=Decimal('50000'),
                  confidence=Decimal('0.8'), timestamp=datetime.now(timezone.utc)),
            Signal(type=SignalType.NEUTRAL, strength=SignalStrength.WEAK,
                  symbol='BTCUSDT', price=Decimal('50500'),
                  confidence=Decimal('0.3'), timestamp=datetime.now(timezone.utc)),
            Signal(type=SignalType.SELL, strength=SignalStrength.STRONG,
                  symbol='BTCUSDT', price=Decimal('51000'),
                  confidence=Decimal('0.85'), timestamp=datetime.now(timezone.utc))
        ]

        self.mock_strategy.generate_signal.side_effect = signals

        # Set loop to run 3 iterations
        with patch.object(self.orchestrator, 'should_continue', side_effect=[True, True, True, False]):
            self.orchestrator.run_trading_loop(symbol='BTCUSDT', interval=0)

        # Verify 3 signals were processed
        self.assertEqual(self.mock_strategy.generate_signal.call_count, 3)

        # Verify only actionable signals resulted in trades (BUY and SELL)
        self.assertEqual(self.mock_paper_trading_service.execute_trade.call_count, 2)


if __name__ == '__main__':
    unittest.main()