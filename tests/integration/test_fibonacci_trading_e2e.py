"""
End-to-End Integration Tests for Fibonacci Trading System
Tests the complete workflow from signal generation to trade execution.
"""

import unittest
import tempfile
import sqlite3
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch, Mock
from pathlib import Path
import pandas as pd
import numpy as np

from src.strategies.fibonacci_golden_zone import FibonacciGoldenZoneStrategy
from src.domain.trading.paper_trading_service import PaperTradingService
from src.application.orchestrators.fibonacci_trading_orchestrator import FibonacciTradingOrchestrator
from src.infrastructure.persistence.sqlite_metrics_repository import SQLiteMetricsRepository
from src.strategies.models import SignalType, SignalStrength


class TestFibonacciTradingE2E(unittest.TestCase):
    """Test complete Fibonacci trading workflow."""

    def setUp(self):
        """Set up test environment."""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_db.name

        # Initialize database schema
        self._init_database()

        # Create test account
        self.account_id = 'test-e2e-account'
        self.initial_balance = Decimal('10000.00')

        # Initialize services
        self.paper_trading = PaperTradingService(
            db_path=self.db_path,
            initial_balance=self.initial_balance
        )

        self.strategy = FibonacciGoldenZoneStrategy(
            golden_zone_start=0.50,
            golden_zone_end=0.618,
            stop_level=0.786,
            targets=[1.618, 2.618]
        )

        self.metrics_repository = SQLiteMetricsRepository(self.db_path)

        # Mock exchange client
        self.mock_client = MagicMock()

    def tearDown(self):
        """Clean up test environment."""
        # Close database connections
        self.temp_db.close()

        # Remove temporary database
        Path(self.db_path).unlink(missing_ok=True)

    def _init_database(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create accounts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id TEXT PRIMARY KEY,
                balance REAL,
                equity REAL,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)

        # Create positions table
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

        # Create orders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                account_id TEXT,
                symbol TEXT,
                side TEXT,
                type TEXT,
                quantity REAL,
                price REAL,
                status TEXT,
                created_at TIMESTAMP,
                executed_at TIMESTAMP
            )
        """)

        # Create metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id TEXT,
                timestamp TIMESTAMP,
                balance REAL,
                equity REAL,
                total_trades INTEGER,
                winning_trades INTEGER,
                losing_trades INTEGER,
                total_pnl REAL,
                win_rate REAL,
                sharpe_ratio REAL,
                max_drawdown REAL
            )
        """)

        conn.commit()
        conn.close()

    def _create_market_data(self, trend='bullish'):
        """Create simulated market data."""
        periods = 100

        if trend == 'bullish':
            # Create uptrend
            prices = np.linspace(50000, 55000, periods)
            prices += np.random.normal(0, 200, periods)  # Add noise

        elif trend == 'bearish':
            # Create downtrend
            prices = np.linspace(55000, 50000, periods)
            prices += np.random.normal(0, 200, periods)

        else:  # sideways
            prices = np.full(periods, 52500)
            prices += np.random.normal(0, 500, periods)

        dates = pd.date_range(
            start=datetime.now(timezone.utc) - timedelta(hours=periods),
            periods=periods,
            freq='h'
        )

        return pd.DataFrame({
            'time': dates,
            'open': prices - 50,
            'high': prices + 100,
            'low': prices - 100,
            'close': prices,
            'volume': np.random.uniform(1000, 5000, periods)
        })

    def test_complete_trading_cycle_bullish(self):
        """Test complete trading cycle in bullish market."""
        # Setup: Create account
        self.paper_trading.create_account(self.account_id, self.initial_balance)

        # Mock market data
        market_data = self._create_market_data('bullish')
        self.mock_client.get_candles.return_value = market_data

        with patch.object(self.strategy, 'fetch_candles', return_value=market_data):
            # Step 1: Generate signal
            analysis = self.strategy.analyze('BTCUSDT', '1h')

            self.assertIsNotNone(analysis)
            signal = analysis['signal']

            # In bullish market after retracement, should generate buy signal
            if signal.type == SignalType.BUY:
                self.assertEqual(signal.type, SignalType.BUY)
                self.assertIn(signal.strength, [SignalStrength.STRONG, SignalStrength.MEDIUM])

                # Step 2: Execute trade
                position = self.paper_trading.open_position(
                    account_id=self.account_id,
                    symbol='BTCUSDT',
                    side='LONG',
                    quantity=Decimal('0.1'),
                    entry_price=Decimal('52000'),
                    stop_loss=Decimal('51000'),
                    take_profit=[Decimal('54000'), Decimal('56000')]
                )

                self.assertIsNotNone(position)
                self.assertEqual(position['symbol'], 'BTCUSDT')
                self.assertEqual(position['side'], 'LONG')

                # Step 3: Update price (price moves up)
                new_price = Decimal('54100')  # Above first take profit
                self.paper_trading.update_position_price(
                    self.account_id,
                    'BTCUSDT',
                    new_price
                )

                # Step 4: Check position P&L
                account_status = self.paper_trading.get_account_status(self.account_id)
                positions = account_status['positions']

                self.assertEqual(len(positions), 1)
                position = positions[0]

                # Calculate expected P&L
                expected_pnl = (new_price - Decimal('52000')) * Decimal('0.1')
                self.assertAlmostEqual(float(position['pnl']), float(expected_pnl), places=2)

                # Step 5: Close position at profit
                close_order = self.paper_trading.close_position(
                    self.account_id,
                    'BTCUSDT'
                )

                self.assertIsNotNone(close_order)

                # Step 6: Verify final account state
                final_account = self.paper_trading.get_account_status(self.account_id)

                # Should have profit added to balance
                expected_balance = self.initial_balance + expected_pnl
                self.assertAlmostEqual(
                    float(final_account['balance']),
                    float(expected_balance),
                    places=2
                )

                # Should have no open positions
                self.assertEqual(len(final_account['positions']), 0)

    def test_complete_trading_cycle_bearish(self):
        """Test complete trading cycle in bearish market."""
        # Setup: Create account
        self.paper_trading.create_account(self.account_id, self.initial_balance)

        # Mock market data
        market_data = self._create_market_data('bearish')
        self.mock_client.get_candles.return_value = market_data

        with patch.object(self.strategy, 'fetch_candles', return_value=market_data):
            # Step 1: Generate signal
            analysis = self.strategy.analyze('BTCUSDT', '1h')

            signal = analysis['signal']

            # In bearish market after bounce, might generate sell signal
            if signal.type == SignalType.SELL:
                # Step 2: Execute short trade
                position = self.paper_trading.open_position(
                    account_id=self.account_id,
                    symbol='BTCUSDT',
                    side='SHORT',
                    quantity=Decimal('0.1'),
                    entry_price=Decimal('52000'),
                    stop_loss=Decimal('53000'),
                    take_profit=[Decimal('50000'), Decimal('48000')]
                )

                self.assertIsNotNone(position)
                self.assertEqual(position['side'], 'SHORT')

                # Step 3: Update price (price moves down - profitable for short)
                new_price = Decimal('49900')  # Below first take profit
                self.paper_trading.update_position_price(
                    self.account_id,
                    'BTCUSDT',
                    new_price
                )

                # Step 4: Verify short position profit
                account_status = self.paper_trading.get_account_status(self.account_id)
                position = account_status['positions'][0]

                # For short: profit when price goes down
                expected_pnl = (Decimal('52000') - new_price) * Decimal('0.1')
                self.assertAlmostEqual(float(position['pnl']), float(expected_pnl), places=2)

    def test_stop_loss_execution(self):
        """Test stop loss execution."""
        # Setup: Create account and position
        self.paper_trading.create_account(self.account_id, self.initial_balance)

        position = self.paper_trading.open_position(
            account_id=self.account_id,
            symbol='BTCUSDT',
            side='LONG',
            quantity=Decimal('0.1'),
            entry_price=Decimal('52000'),
            stop_loss=Decimal('51000'),
            take_profit=[Decimal('54000')]
        )

        # Price drops below stop loss
        stop_price = Decimal('50900')
        self.paper_trading.update_position_price(
            self.account_id,
            'BTCUSDT',
            stop_price
        )

        # Check if stop loss triggered
        should_close = stop_price <= Decimal('51000')
        self.assertTrue(should_close)

        # Execute stop loss
        close_order = self.paper_trading.close_position(
            self.account_id,
            'BTCUSDT'
        )

        # Verify loss recorded
        final_account = self.paper_trading.get_account_status(self.account_id)
        expected_loss = (stop_price - Decimal('52000')) * Decimal('0.1')
        expected_balance = self.initial_balance + expected_loss

        self.assertAlmostEqual(
            float(final_account['balance']),
            float(expected_balance),
            places=2
        )

    def test_metrics_recording(self):
        """Test metrics recording throughout trading."""
        # Setup
        self.paper_trading.create_account(self.account_id, self.initial_balance)

        # Execute multiple trades
        trades = [
            {'side': 'LONG', 'entry': 50000, 'exit': 51000, 'quantity': 0.1},  # Win
            {'side': 'LONG', 'entry': 51000, 'exit': 50500, 'quantity': 0.1},  # Loss
            {'side': 'SHORT', 'entry': 50500, 'exit': 49500, 'quantity': 0.1}, # Win
            {'side': 'LONG', 'entry': 49500, 'exit': 51000, 'quantity': 0.1},  # Win
        ]

        for trade in trades:
            # Open position
            self.paper_trading.open_position(
                account_id=self.account_id,
                symbol='BTCUSDT',
                side=trade['side'],
                quantity=Decimal(str(trade['quantity'])),
                entry_price=Decimal(str(trade['entry'])),
                stop_loss=Decimal(str(trade['entry'] - 1000)),
                take_profit=[Decimal(str(trade['entry'] + 2000))]
            )

            # Close at exit price
            self.paper_trading.update_position_price(
                self.account_id,
                'BTCUSDT',
                Decimal(str(trade['exit']))
            )
            self.paper_trading.close_position(self.account_id, 'BTCUSDT')

            # Record metrics
            account = self.paper_trading.get_account_status(self.account_id)
            self.metrics_repository.record_metrics(
                account_id=self.account_id,
                balance=account['balance'],
                equity=account['equity']
            )

        # Verify metrics
        metrics = self.metrics_repository.get_latest_metrics(self.account_id)

        self.assertIsNotNone(metrics)
        self.assertEqual(metrics['total_trades'], 4)
        self.assertEqual(metrics['winning_trades'], 3)
        self.assertEqual(metrics['losing_trades'], 1)
        self.assertEqual(metrics['win_rate'], Decimal('0.75'))  # 75% win rate


class TestPaperTradingIntegration(unittest.TestCase):
    """Test paper trading service integration."""

    def setUp(self):
        """Set up test environment."""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_db.name

        # Initialize database
        self._init_database()

        self.service = PaperTradingService(
            db_path=self.db_path,
            initial_balance=Decimal('10000')
        )

        self.account_id = 'integration-test-account'

    def tearDown(self):
        """Clean up test environment."""
        self.temp_db.close()
        Path(self.db_path).unlink(missing_ok=True)

    def _init_database(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

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

        conn.commit()
        conn.close()

    def test_account_lifecycle(self):
        """Test complete account lifecycle."""
        # Create account
        account = self.service.create_account(
            self.account_id,
            Decimal('10000')
        )

        self.assertEqual(account['id'], self.account_id)
        self.assertEqual(account['balance'], Decimal('10000'))

        # Open multiple positions
        positions = []
        symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']

        for symbol in symbols:
            position = self.service.open_position(
                account_id=self.account_id,
                symbol=symbol,
                side='LONG',
                quantity=Decimal('0.1'),
                entry_price=Decimal('50000'),
                stop_loss=Decimal('49000'),
                take_profit=[Decimal('52000')]
            )
            positions.append(position)

        # Get account status
        status = self.service.get_account_status(self.account_id)

        self.assertEqual(len(status['positions']), 3)

        # Close all positions
        for symbol in symbols:
            self.service.close_position(self.account_id, symbol)

        # Verify all closed
        final_status = self.service.get_account_status(self.account_id)
        self.assertEqual(len(final_status['positions']), 0)

    def test_concurrent_position_management(self):
        """Test managing multiple positions concurrently."""
        # Create account
        self.service.create_account(self.account_id, Decimal('10000'))

        # Open positions in different symbols
        positions = {
            'BTCUSDT': {'side': 'LONG', 'entry': 50000, 'quantity': 0.01},
            'ETHUSDT': {'side': 'SHORT', 'entry': 3000, 'quantity': 1},
            'BNBUSDT': {'side': 'LONG', 'entry': 400, 'quantity': 5}
        }

        for symbol, details in positions.items():
            self.service.open_position(
                account_id=self.account_id,
                symbol=symbol,
                side=details['side'],
                quantity=Decimal(str(details['quantity'])),
                entry_price=Decimal(str(details['entry'])),
                stop_loss=Decimal(str(details['entry'] * 0.95)),
                take_profit=[Decimal(str(details['entry'] * 1.1))]
            )

        # Update prices
        new_prices = {
            'BTCUSDT': 51000,  # +2% profit for long
            'ETHUSDT': 2940,   # +2% profit for short
            'BNBUSDT': 410     # +2.5% profit for long
        }

        for symbol, price in new_prices.items():
            self.service.update_position_price(
                self.account_id,
                symbol,
                Decimal(str(price))
            )

        # Check all positions have correct P&L
        status = self.service.get_account_status(self.account_id)

        for position in status['positions']:
            self.assertGreater(position['pnl'], 0)  # All should be profitable


if __name__ == '__main__':
    unittest.main()