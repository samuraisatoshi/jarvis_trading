"""
Unit tests for Fibonacci Golden Zone Strategy
Tests the core fibonacci trading strategy implementation.
"""

import unittest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch, Mock
import pandas as pd
import numpy as np

from src.strategies.fibonacci_golden_zone import FibonacciGoldenZoneStrategy
from src.strategies.models import (
    Signal, SignalType, SignalStrength,
    FibonacciLevels, TrendDirection
)


class TestFibonacciGoldenZoneStrategy(unittest.TestCase):
    """Test FibonacciGoldenZoneStrategy implementation."""

    def setUp(self):
        """Set up test fixtures."""
        self.strategy = FibonacciGoldenZoneStrategy(
            golden_zone_start=0.50,
            golden_zone_end=0.618,
            stop_level=0.786,
            targets=[1.618, 2.618],
            lookback_periods=50,
            min_trend_strength=0.3
        )

        # Create sample candle data
        self.sample_candles = self._create_sample_candles()

    def _create_sample_candles(self):
        """Create sample candle data for testing."""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='h')

        # Create uptrend data
        prices = np.linspace(50000, 55000, 100)
        # Add some noise
        prices += np.random.normal(0, 100, 100)

        return pd.DataFrame({
            'time': dates,
            'open': prices - 50,
            'high': prices + 100,
            'low': prices - 100,
            'close': prices,
            'volume': np.random.uniform(1000, 5000, 100)
        })

    def test_strategy_initialization(self):
        """Test strategy initialization with valid parameters."""
        self.assertEqual(self.strategy.golden_zone_start, 0.50)
        self.assertEqual(self.strategy.golden_zone_end, 0.618)
        self.assertEqual(self.strategy.stop_level, 0.786)
        self.assertEqual(self.strategy.targets, [1.618, 2.618])
        self.assertEqual(self.strategy.lookback_periods, 50)
        self.assertEqual(self.strategy.min_trend_strength, 0.3)

    def test_calculate_fibonacci_levels(self):
        """Test Fibonacci levels calculation."""
        high = Decimal('55000')
        low = Decimal('50000')

        levels = self.strategy.calculate_fibonacci_levels(high, low)

        self.assertIsInstance(levels, FibonacciLevels)
        self.assertEqual(levels.high, high)
        self.assertEqual(levels.low, low)

        # Test retracement levels
        self.assertEqual(levels.retracement_0, high)  # 0% = high
        self.assertEqual(levels.retracement_100, low)  # 100% = low

        # 38.2% retracement
        expected_382 = high - (high - low) * Decimal('0.382')
        self.assertAlmostEqual(float(levels.retracement_382), float(expected_382), places=2)

        # 50% retracement
        expected_50 = high - (high - low) * Decimal('0.5')
        self.assertAlmostEqual(float(levels.retracement_50), float(expected_50), places=2)

        # 61.8% retracement
        expected_618 = high - (high - low) * Decimal('0.618')
        self.assertAlmostEqual(float(levels.retracement_618), float(expected_618), places=2)

    def test_identify_trend_uptrend(self):
        """Test trend identification for uptrend."""
        # Create clear uptrend data
        uptrend_candles = self.sample_candles.copy()
        uptrend_candles['close'] = np.linspace(50000, 55000, 100)

        trend = self.strategy.identify_trend(uptrend_candles)

        self.assertEqual(trend, TrendDirection.BULLISH)

    def test_identify_trend_downtrend(self):
        """Test trend identification for downtrend."""
        # Create clear downtrend data
        downtrend_candles = self.sample_candles.copy()
        downtrend_candles['close'] = np.linspace(55000, 50000, 100)

        trend = self.strategy.identify_trend(downtrend_candles)

        self.assertEqual(trend, TrendDirection.BEARISH)

    def test_identify_trend_sideways(self):
        """Test trend identification for sideways market."""
        # Create sideways data
        sideways_candles = self.sample_candles.copy()
        sideways_candles['close'] = 52500 + np.random.normal(0, 100, 100)

        trend = self.strategy.identify_trend(sideways_candles)

        self.assertEqual(trend, TrendDirection.NEUTRAL)

    def test_is_in_golden_zone(self):
        """Test golden zone detection."""
        levels = FibonacciLevels(
            high=Decimal('55000'),
            low=Decimal('50000'),
            retracement_0=Decimal('55000'),
            retracement_236=Decimal('53820'),
            retracement_382=Decimal('53090'),
            retracement_50=Decimal('52500'),
            retracement_618=Decimal('51910'),
            retracement_786=Decimal('51070'),
            retracement_100=Decimal('50000'),
            extension_1618=Decimal('58090'),
            extension_2618=Decimal('63090')
        )

        # Price in golden zone (between 50% and 61.8%)
        self.assertTrue(self.strategy.is_in_golden_zone(Decimal('52200'), levels))

        # Price above golden zone
        self.assertFalse(self.strategy.is_in_golden_zone(Decimal('53000'), levels))

        # Price below golden zone
        self.assertFalse(self.strategy.is_in_golden_zone(Decimal('51000'), levels))

    def test_generate_signal_buy(self):
        """Test buy signal generation."""
        with patch.object(self.strategy, 'identify_trend', return_value=TrendDirection.BULLISH):
            with patch.object(self.strategy, 'is_in_golden_zone', return_value=True):

                signal = self.strategy.generate_signal(
                    self.sample_candles,
                    current_price=Decimal('52200')
                )

                self.assertIsNotNone(signal)
                self.assertEqual(signal.type, SignalType.BUY)
                self.assertEqual(signal.strength, SignalStrength.STRONG)
                self.assertGreater(signal.confidence, 0.7)

    def test_generate_signal_sell(self):
        """Test sell signal generation."""
        # Modify candles for downtrend
        downtrend_candles = self.sample_candles.copy()
        downtrend_candles['close'] = np.linspace(55000, 50000, 100)

        with patch.object(self.strategy, 'identify_trend', return_value=TrendDirection.BEARISH):
            with patch.object(self.strategy, 'is_in_golden_zone', return_value=True):

                signal = self.strategy.generate_signal(
                    downtrend_candles,
                    current_price=Decimal('52800')
                )

                self.assertIsNotNone(signal)
                self.assertEqual(signal.type, SignalType.SELL)
                self.assertEqual(signal.strength, SignalStrength.STRONG)
                self.assertGreater(signal.confidence, 0.7)

    def test_generate_signal_neutral(self):
        """Test neutral signal when conditions not met."""
        with patch.object(self.strategy, 'identify_trend', return_value=TrendDirection.NEUTRAL):

            signal = self.strategy.generate_signal(
                self.sample_candles,
                current_price=Decimal('52500')
            )

            self.assertIsNotNone(signal)
            self.assertEqual(signal.type, SignalType.NEUTRAL)
            self.assertEqual(signal.strength, SignalStrength.WEAK)
            self.assertLess(signal.confidence, 0.5)

    def test_calculate_position_size(self):
        """Test position size calculation."""
        account_balance = Decimal('10000')
        risk_per_trade = Decimal('0.02')  # 2% risk
        entry_price = Decimal('50000')
        stop_price = Decimal('49000')

        position_size = self.strategy.calculate_position_size(
            account_balance=account_balance,
            risk_per_trade=risk_per_trade,
            entry_price=entry_price,
            stop_price=stop_price
        )

        # Risk amount = 10000 * 0.02 = 200
        # Risk per unit = 50000 - 49000 = 1000
        # Position size = 200 / 1000 = 0.2
        expected_size = Decimal('0.2')

        self.assertEqual(position_size, expected_size)

    def test_calculate_position_size_with_max_position(self):
        """Test position size with maximum position limit."""
        account_balance = Decimal('100000')
        risk_per_trade = Decimal('0.02')
        entry_price = Decimal('50000')
        stop_price = Decimal('49900')  # Small stop loss

        position_size = self.strategy.calculate_position_size(
            account_balance=account_balance,
            risk_per_trade=risk_per_trade,
            entry_price=entry_price,
            stop_price=stop_price,
            max_position_size=Decimal('1.0')
        )

        # Should be capped at max_position_size
        self.assertLessEqual(position_size, Decimal('1.0'))

    def test_calculate_stop_loss_long(self):
        """Test stop loss calculation for long position."""
        entry_price = Decimal('52200')

        levels = FibonacciLevels(
            high=Decimal('55000'),
            low=Decimal('50000'),
            retracement_0=Decimal('55000'),
            retracement_236=Decimal('53820'),
            retracement_382=Decimal('53090'),
            retracement_50=Decimal('52500'),
            retracement_618=Decimal('51910'),
            retracement_786=Decimal('51070'),  # Stop level
            retracement_100=Decimal('50000'),
            extension_1618=Decimal('58090'),
            extension_2618=Decimal('63090')
        )

        stop_loss = self.strategy.calculate_stop_loss(
            entry_price=entry_price,
            signal_type=SignalType.BUY,
            fibonacci_levels=levels
        )

        # For long, stop should be at 78.6% retracement
        self.assertEqual(stop_loss, levels.retracement_786)

    def test_calculate_stop_loss_short(self):
        """Test stop loss calculation for short position."""
        entry_price = Decimal('52800')

        levels = FibonacciLevels(
            high=Decimal('55000'),
            low=Decimal('50000'),
            retracement_0=Decimal('55000'),
            retracement_236=Decimal('53820'),  # Stop level for short
            retracement_382=Decimal('53090'),
            retracement_50=Decimal('52500'),
            retracement_618=Decimal('51910'),
            retracement_786=Decimal('51070'),
            retracement_100=Decimal('50000'),
            extension_1618=Decimal('58090'),
            extension_2618=Decimal('63090')
        )

        stop_loss = self.strategy.calculate_stop_loss(
            entry_price=entry_price,
            signal_type=SignalType.SELL,
            fibonacci_levels=levels
        )

        # For short, stop should be at 23.6% retracement
        self.assertEqual(stop_loss, levels.retracement_236)

    def test_calculate_take_profit_levels(self):
        """Test take profit levels calculation."""
        entry_price = Decimal('52200')

        levels = FibonacciLevels(
            high=Decimal('55000'),
            low=Decimal('50000'),
            retracement_0=Decimal('55000'),
            retracement_236=Decimal('53820'),
            retracement_382=Decimal('53090'),
            retracement_50=Decimal('52500'),
            retracement_618=Decimal('51910'),
            retracement_786=Decimal('51070'),
            retracement_100=Decimal('50000'),
            extension_1618=Decimal('58090'),  # Target 1
            extension_2618=Decimal('63090')   # Target 2
        )

        take_profits = self.strategy.calculate_take_profit_levels(
            entry_price=entry_price,
            signal_type=SignalType.BUY,
            fibonacci_levels=levels
        )

        # Should have two targets based on strategy configuration
        self.assertEqual(len(take_profits), 2)
        self.assertEqual(take_profits[0], levels.extension_1618)
        self.assertEqual(take_profits[1], levels.extension_2618)

    def test_analyze_complete_flow(self):
        """Test complete analysis flow."""
        with patch.object(self.strategy, 'fetch_candles', return_value=self.sample_candles):

            analysis = self.strategy.analyze(
                symbol='BTCUSDT',
                timeframe='1h'
            )

            self.assertIsNotNone(analysis)
            self.assertIn('signal', analysis)
            self.assertIn('fibonacci_levels', analysis)
            self.assertIn('trend', analysis)
            self.assertIn('current_price', analysis)
            self.assertIn('timestamp', analysis)

            # Check signal is valid
            signal = analysis['signal']
            self.assertIsInstance(signal, Signal)
            self.assertIn(signal.type, [SignalType.BUY, SignalType.SELL, SignalType.NEUTRAL])

    def test_backtest_metrics(self):
        """Test backtesting metrics calculation."""
        # Create mock trade results
        trades = [
            {'pnl': Decimal('100'), 'return': Decimal('0.02')},
            {'pnl': Decimal('-50'), 'return': Decimal('-0.01')},
            {'pnl': Decimal('200'), 'return': Decimal('0.04')},
            {'pnl': Decimal('-30'), 'return': Decimal('-0.006')},
            {'pnl': Decimal('150'), 'return': Decimal('0.03')}
        ]

        metrics = self.strategy.calculate_backtest_metrics(trades)

        self.assertIn('total_trades', metrics)
        self.assertIn('winning_trades', metrics)
        self.assertIn('losing_trades', metrics)
        self.assertIn('win_rate', metrics)
        self.assertIn('total_pnl', metrics)
        self.assertIn('average_pnl', metrics)
        self.assertIn('sharpe_ratio', metrics)
        self.assertIn('max_drawdown', metrics)

        # Verify calculations
        self.assertEqual(metrics['total_trades'], 5)
        self.assertEqual(metrics['winning_trades'], 3)
        self.assertEqual(metrics['losing_trades'], 2)
        self.assertEqual(metrics['win_rate'], Decimal('0.6'))  # 60%
        self.assertEqual(metrics['total_pnl'], Decimal('370'))


if __name__ == '__main__':
    unittest.main()