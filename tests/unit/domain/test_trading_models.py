"""
Unit tests for Domain Trading Models
Tests core trading domain entities and value objects.
"""

import unittest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

from src.domain.models.trading_models import (
    Order, Position, Trade, MarketSignal,
    OrderType, OrderStatus, SignalType, SignalStrength
)


class TestOrder(unittest.TestCase):
    """Test Order domain entity."""

    def setUp(self):
        """Set up test fixtures."""
        self.valid_order_data = {
            'id': 'ORD-123',
            'symbol': 'BTCUSDT',
            'side': 'BUY',
            'type': OrderType.MARKET,
            'quantity': Decimal('0.01'),
            'price': Decimal('50000.00'),
            'status': OrderStatus.NEW,
            'timestamp': datetime.now(timezone.utc)
        }

    def test_order_creation_with_valid_data(self):
        """Test Order creation with valid data."""
        order = Order(**self.valid_order_data)

        self.assertEqual(order.id, 'ORD-123')
        self.assertEqual(order.symbol, 'BTCUSDT')
        self.assertEqual(order.side, 'BUY')
        self.assertEqual(order.type, OrderType.MARKET)
        self.assertEqual(order.quantity, Decimal('0.01'))
        self.assertEqual(order.price, Decimal('50000.00'))
        self.assertEqual(order.status, OrderStatus.NEW)
        self.assertIsInstance(order.timestamp, datetime)

    def test_order_value_calculation(self):
        """Test Order value calculation."""
        order = Order(**self.valid_order_data)
        expected_value = Decimal('0.01') * Decimal('50000.00')

        self.assertEqual(order.get_value(), expected_value)

    def test_order_status_transitions(self):
        """Test valid order status transitions."""
        order = Order(**self.valid_order_data)

        # Test valid transitions
        order.update_status(OrderStatus.FILLED)
        self.assertEqual(order.status, OrderStatus.FILLED)

        # Test invalid transition (filled -> new)
        with self.assertRaises(ValueError):
            order.update_status(OrderStatus.NEW)

    def test_order_immutability_of_critical_fields(self):
        """Test that critical fields cannot be changed after creation."""
        order = Order(**self.valid_order_data)

        # Symbol should not be changeable
        with self.assertRaises(AttributeError):
            order.symbol = 'ETHUSDT'

        # Side should not be changeable
        with self.assertRaises(AttributeError):
            order.side = 'SELL'


class TestPosition(unittest.TestCase):
    """Test Position domain entity."""

    def setUp(self):
        """Set up test fixtures."""
        self.valid_position_data = {
            'symbol': 'BTCUSDT',
            'quantity': Decimal('0.01'),
            'entry_price': Decimal('50000.00'),
            'current_price': Decimal('51000.00'),
            'side': 'LONG',
            'leverage': 1,
            'timestamp': datetime.now(timezone.utc)
        }

    def test_position_creation(self):
        """Test Position creation with valid data."""
        position = Position(**self.valid_position_data)

        self.assertEqual(position.symbol, 'BTCUSDT')
        self.assertEqual(position.quantity, Decimal('0.01'))
        self.assertEqual(position.entry_price, Decimal('50000.00'))
        self.assertEqual(position.current_price, Decimal('51000.00'))
        self.assertEqual(position.side, 'LONG')
        self.assertEqual(position.leverage, 1)

    def test_position_pnl_calculation_long(self):
        """Test P&L calculation for long position."""
        position = Position(**self.valid_position_data)

        # Expected P&L = (current - entry) * quantity
        # (51000 - 50000) * 0.01 = 10
        expected_pnl = Decimal('10.00')
        expected_pnl_percentage = Decimal('2.00')  # 2%

        self.assertEqual(position.get_pnl(), expected_pnl)
        self.assertEqual(position.get_pnl_percentage(), expected_pnl_percentage)

    def test_position_pnl_calculation_short(self):
        """Test P&L calculation for short position."""
        position_data = self.valid_position_data.copy()
        position_data['side'] = 'SHORT'
        position = Position(**position_data)

        # Expected P&L = (entry - current) * quantity
        # (50000 - 51000) * 0.01 = -10
        expected_pnl = Decimal('-10.00')
        expected_pnl_percentage = Decimal('-2.00')  # -2%

        self.assertEqual(position.get_pnl(), expected_pnl)
        self.assertEqual(position.get_pnl_percentage(), expected_pnl_percentage)

    def test_position_update_price(self):
        """Test updating position current price."""
        position = Position(**self.valid_position_data)

        new_price = Decimal('52000.00')
        position.update_price(new_price)

        self.assertEqual(position.current_price, new_price)

        # Verify new P&L calculation
        expected_pnl = Decimal('20.00')  # (52000 - 50000) * 0.01
        self.assertEqual(position.get_pnl(), expected_pnl)

    def test_position_with_leverage(self):
        """Test position with leverage."""
        position_data = self.valid_position_data.copy()
        position_data['leverage'] = 10
        position = Position(**position_data)

        # P&L should be multiplied by leverage
        base_pnl = Decimal('10.00')
        expected_pnl = base_pnl * 10

        self.assertEqual(position.get_pnl(), expected_pnl)


class TestTrade(unittest.TestCase):
    """Test Trade domain entity."""

    def setUp(self):
        """Set up test fixtures."""
        self.valid_trade_data = {
            'id': 'TRD-456',
            'symbol': 'BTCUSDT',
            'side': 'BUY',
            'quantity': Decimal('0.01'),
            'price': Decimal('50000.00'),
            'fee': Decimal('0.5'),
            'fee_asset': 'USDT',
            'timestamp': datetime.now(timezone.utc),
            'order_id': 'ORD-123'
        }

    def test_trade_creation(self):
        """Test Trade creation with valid data."""
        trade = Trade(**self.valid_trade_data)

        self.assertEqual(trade.id, 'TRD-456')
        self.assertEqual(trade.symbol, 'BTCUSDT')
        self.assertEqual(trade.side, 'BUY')
        self.assertEqual(trade.quantity, Decimal('0.01'))
        self.assertEqual(trade.price, Decimal('50000.00'))
        self.assertEqual(trade.fee, Decimal('0.5'))
        self.assertEqual(trade.fee_asset, 'USDT')
        self.assertEqual(trade.order_id, 'ORD-123')

    def test_trade_total_cost_calculation(self):
        """Test total cost calculation including fees."""
        trade = Trade(**self.valid_trade_data)

        # Total cost = (quantity * price) + fee
        # (0.01 * 50000) + 0.5 = 500.5
        expected_total = Decimal('500.50')

        self.assertEqual(trade.get_total_cost(), expected_total)

    def test_trade_net_value_calculation(self):
        """Test net value calculation after fees."""
        trade = Trade(**self.valid_trade_data)

        # Net value = (quantity * price) - fee
        # (0.01 * 50000) - 0.5 = 499.5
        expected_net = Decimal('499.50')

        self.assertEqual(trade.get_net_value(), expected_net)


class TestMarketSignal(unittest.TestCase):
    """Test MarketSignal domain entity."""

    def setUp(self):
        """Set up test fixtures."""
        self.valid_signal_data = {
            'symbol': 'BTCUSDT',
            'type': SignalType.BUY,
            'strength': SignalStrength.STRONG,
            'price': Decimal('50000.00'),
            'confidence': Decimal('0.85'),
            'source': 'FibonacciStrategy',
            'timestamp': datetime.now(timezone.utc),
            'metadata': {'levels': [0.618, 0.5, 0.382]}
        }

    def test_signal_creation(self):
        """Test MarketSignal creation with valid data."""
        signal = MarketSignal(**self.valid_signal_data)

        self.assertEqual(signal.symbol, 'BTCUSDT')
        self.assertEqual(signal.type, SignalType.BUY)
        self.assertEqual(signal.strength, SignalStrength.STRONG)
        self.assertEqual(signal.price, Decimal('50000.00'))
        self.assertEqual(signal.confidence, Decimal('0.85'))
        self.assertEqual(signal.source, 'FibonacciStrategy')
        self.assertIsInstance(signal.timestamp, datetime)
        self.assertEqual(signal.metadata['levels'], [0.618, 0.5, 0.382])

    def test_signal_confidence_validation(self):
        """Test signal confidence validation (0-1 range)."""
        signal_data = self.valid_signal_data.copy()

        # Test invalid confidence > 1
        signal_data['confidence'] = Decimal('1.5')
        with self.assertRaises(ValueError):
            MarketSignal(**signal_data)

        # Test invalid confidence < 0
        signal_data['confidence'] = Decimal('-0.1')
        with self.assertRaises(ValueError):
            MarketSignal(**signal_data)

        # Test valid edge cases
        signal_data['confidence'] = Decimal('0.0')
        signal = MarketSignal(**signal_data)
        self.assertEqual(signal.confidence, Decimal('0.0'))

        signal_data['confidence'] = Decimal('1.0')
        signal = MarketSignal(**signal_data)
        self.assertEqual(signal.confidence, Decimal('1.0'))

    def test_signal_is_actionable(self):
        """Test if signal is actionable based on strength and confidence."""
        signal = MarketSignal(**self.valid_signal_data)

        # Strong signal with high confidence should be actionable
        self.assertTrue(signal.is_actionable())

        # Weak signal should not be actionable
        signal_data = self.valid_signal_data.copy()
        signal_data['strength'] = SignalStrength.WEAK
        signal_data['confidence'] = Decimal('0.3')
        weak_signal = MarketSignal(**signal_data)
        self.assertFalse(weak_signal.is_actionable())

    def test_signal_expiry(self):
        """Test signal expiry based on age."""
        from datetime import timedelta

        signal_data = self.valid_signal_data.copy()

        # Fresh signal should not be expired
        signal = MarketSignal(**signal_data)
        self.assertFalse(signal.is_expired(max_age_minutes=5))

        # Old signal should be expired
        old_timestamp = datetime.now(timezone.utc) - timedelta(minutes=10)
        signal_data['timestamp'] = old_timestamp
        old_signal = MarketSignal(**signal_data)
        self.assertTrue(old_signal.is_expired(max_age_minutes=5))


if __name__ == '__main__':
    unittest.main()