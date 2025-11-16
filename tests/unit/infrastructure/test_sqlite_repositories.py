"""Tests for SQLite repositories."""

import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from src.domain.account.entities.account import Account
from src.domain.account.entities.balance import Balance
from src.domain.account.entities.transaction import Transaction, TransactionType
from src.domain.account.value_objects.currency import Currency
from src.domain.account.value_objects.money import Money
from src.domain.analytics.repositories.performance_repository import PerformanceMetrics
from src.domain.paper_trading.repositories.order_repository import (
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
)
from src.infrastructure.database import DatabaseManager
from src.infrastructure.persistence import (
    SQLiteAccountRepository,
    SQLiteOrderRepository,
    SQLitePerformanceRepository,
    SQLiteTransactionRepository,
)


@pytest.fixture
def temp_db():
    """Create temporary database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        manager = DatabaseManager(db_path)
        manager.initialize()
        yield manager
        manager.close()


@pytest.fixture
def account_repo(temp_db):
    """Create account repository."""
    return SQLiteAccountRepository(temp_db)


@pytest.fixture
def transaction_repo(temp_db):
    """Create transaction repository."""
    return SQLiteTransactionRepository(temp_db)


@pytest.fixture
def order_repo(temp_db):
    """Create order repository."""
    return SQLiteOrderRepository(temp_db)


@pytest.fixture
def performance_repo(temp_db):
    """Create performance repository."""
    return SQLitePerformanceRepository(temp_db)


@pytest.fixture
def sample_account():
    """Create sample account."""
    account = Account(
        account_id="acc_001",
        name="Test Account",
        balance=Balance(),
        is_active=True,
    )

    # Add some balance
    money = Money(currency=Currency.USDT, available_amount=10000.0)
    account.balance.add_available(money)

    return account


class TestSQLiteAccountRepository:
    """Tests for SQLiteAccountRepository."""

    def test_save_and_find(self, account_repo, sample_account):
        """Test saving and finding account."""
        account_repo.save(sample_account)

        found = account_repo.find_by_id(sample_account.account_id)
        assert found is not None
        assert found.account_id == sample_account.account_id
        assert found.name == sample_account.name

    def test_find_by_name(self, account_repo, sample_account):
        """Test finding account by name."""
        account_repo.save(sample_account)

        found = account_repo.find_by_name(sample_account.name)
        assert found is not None
        assert found.account_id == sample_account.account_id

    def test_find_all(self, account_repo, sample_account):
        """Test finding all accounts."""
        # Save multiple accounts
        account_repo.save(sample_account)

        account2 = Account(
            account_id="acc_002",
            name="Second Account",
            balance=Balance(),
        )
        account_repo.save(account2)

        all_accounts = account_repo.find_all()
        assert len(all_accounts) == 2

    def test_find_all_active(self, account_repo, sample_account):
        """Test finding active accounts."""
        account_repo.save(sample_account)

        account2 = Account(
            account_id="acc_002",
            name="Closed Account",
            is_active=False,
        )
        account_repo.save(account2)

        active = account_repo.find_all_active()
        assert len(active) == 1
        assert active[0].account_id == sample_account.account_id

    def test_exists(self, account_repo, sample_account):
        """Test checking account existence."""
        assert not account_repo.exists(sample_account.account_id)

        account_repo.save(sample_account)
        assert account_repo.exists(sample_account.account_id)

    def test_delete(self, account_repo, sample_account):
        """Test deleting account."""
        account_repo.save(sample_account)
        assert account_repo.exists(sample_account.account_id)

        deleted = account_repo.delete(sample_account.account_id)
        assert deleted
        assert not account_repo.exists(sample_account.account_id)

    def test_update_account(self, account_repo, sample_account):
        """Test updating account."""
        account_repo.save(sample_account)

        # Update account
        sample_account.name = "Updated Name"
        sample_account.leverage = 2.0
        account_repo.save(sample_account)

        found = account_repo.find_by_id(sample_account.account_id)
        assert found.name == "Updated Name"
        assert found.leverage == 2.0


class TestSQLiteTransactionRepository:
    """Tests for SQLiteTransactionRepository."""

    def test_save_and_find(self, transaction_repo):
        """Test saving and finding transaction."""
        money = Money(currency=Currency.USDT, available_amount=100.0)

        tx = Transaction(
            transaction_type=TransactionType.DEPOSIT,
            amount=money,
            description="Test deposit",
        )

        transaction_repo.save(tx, "acc_001")

        found = transaction_repo.find_by_id(tx.id)
        assert found is not None
        assert found.transaction_type == TransactionType.DEPOSIT

    def test_find_by_account(self, transaction_repo):
        """Test finding transactions by account."""
        for i in range(5):
            money = Money(currency=Currency.USDT, available_amount=100.0 * i)
            tx = Transaction(
                transaction_type=TransactionType.DEPOSIT if i % 2 == 0 else TransactionType.WITHDRAWAL,
                amount=money,
                description=f"Transaction {i}",
            )
            transaction_repo.save(tx, "acc_001")

        txs = transaction_repo.find_by_account("acc_001")
        assert len(txs) == 5

    def test_find_by_type(self, transaction_repo):
        """Test finding transactions by type."""
        # Create deposits
        for i in range(3):
            money = Money(currency=Currency.USDT, available_amount=100.0)
            tx = Transaction(
                transaction_type=TransactionType.DEPOSIT,
                amount=money,
            )
            transaction_repo.save(tx, "acc_001")

        # Create withdrawals
        for i in range(2):
            money = Money(currency=Currency.USDT, available_amount=50.0)
            tx = Transaction(
                transaction_type=TransactionType.WITHDRAWAL,
                amount=money,
            )
            transaction_repo.save(tx, "acc_001")

        deposits = transaction_repo.find_by_type("acc_001", TransactionType.DEPOSIT)
        assert len(deposits) == 3

        withdrawals = transaction_repo.find_by_type("acc_001", TransactionType.WITHDRAWAL)
        assert len(withdrawals) == 2

    def test_get_sum_by_type(self, transaction_repo):
        """Test calculating sum by type."""
        # Add deposits
        for amount in [100, 200, 300]:
            money = Money(currency=Currency.USDT, available_amount=amount)
            tx = Transaction(
                transaction_type=TransactionType.DEPOSIT,
                amount=money,
            )
            transaction_repo.save(tx, "acc_001")

        total = transaction_repo.get_sum_by_type(
            "acc_001", TransactionType.DEPOSIT, Currency.USDT
        )
        assert total == 600.0

    def test_get_transaction_count(self, transaction_repo):
        """Test getting transaction count."""
        for i in range(10):
            money = Money(currency=Currency.USDT, available_amount=100.0)
            tx = Transaction(
                transaction_type=TransactionType.DEPOSIT,
                amount=money,
            )
            transaction_repo.save(tx, "acc_001")

        count = transaction_repo.get_transaction_count("acc_001")
        assert count == 10

    def test_delete_by_account(self, transaction_repo):
        """Test deleting all transactions for account."""
        for i in range(5):
            money = Money(currency=Currency.USDT, available_amount=100.0)
            tx = Transaction(
                transaction_type=TransactionType.DEPOSIT,
                amount=money,
            )
            transaction_repo.save(tx, "acc_001")

        deleted = transaction_repo.delete_by_account("acc_001")
        assert deleted == 5

        count = transaction_repo.get_transaction_count("acc_001")
        assert count == 0


class TestSQLiteOrderRepository:
    """Tests for SQLiteOrderRepository."""

    def test_save_and_find(self, order_repo):
        """Test saving and finding order."""
        order = Order(
            order_id="ord_001",
            account_id="acc_001",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=1.5,
            price=45000.0,
        )

        order_repo.save(order)

        found = order_repo.find_by_id(order.order_id)
        assert found is not None
        assert found.symbol == "BTCUSDT"

    def test_find_by_account(self, order_repo):
        """Test finding orders by account."""
        for i in range(3):
            order = Order(
                order_id=f"ord_00{i}",
                account_id="acc_001",
                symbol="BTCUSDT",
                side=OrderSide.BUY if i % 2 == 0 else OrderSide.SELL,
                order_type=OrderType.MARKET,
                quantity=1.0,
            )
            order_repo.save(order)

        orders = order_repo.find_by_account("acc_001")
        assert len(orders) == 3

    def test_find_by_status(self, order_repo):
        """Test finding orders by status."""
        order1 = Order(
            order_id="ord_001",
            account_id="acc_001",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=1.0,
        )
        order_repo.save(order1)

        order2 = Order(
            order_id="ord_002",
            account_id="acc_001",
            symbol="ETHUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=10.0,
        )
        order2.execute(2000.0)
        order_repo.save(order2)

        pending = order_repo.find_by_status("acc_001", OrderStatus.PENDING)
        assert len(pending) == 1

        filled = order_repo.find_by_status("acc_001", OrderStatus.FILLED)
        assert len(filled) == 1

    def test_get_pending_orders(self, order_repo):
        """Test getting pending orders."""
        order = Order(
            order_id="ord_001",
            account_id="acc_001",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=1.0,
            price=45000.0,
        )
        order_repo.save(order)

        pending = order_repo.get_pending_orders("acc_001")
        assert len(pending) == 1
        assert pending[0].status == OrderStatus.PENDING

    def test_get_order_count(self, order_repo):
        """Test getting order count."""
        for i in range(5):
            order = Order(
                order_id=f"ord_00{i}",
                account_id="acc_001",
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=1.0,
            )
            order_repo.save(order)

        count = order_repo.get_order_count("acc_001")
        assert count == 5

    def test_delete_by_account(self, order_repo):
        """Test deleting all orders for account."""
        for i in range(3):
            order = Order(
                order_id=f"ord_00{i}",
                account_id="acc_001",
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=1.0,
            )
            order_repo.save(order)

        deleted = order_repo.delete_by_account("acc_001")
        assert deleted == 3

        count = order_repo.get_order_count("acc_001")
        assert count == 0


class TestSQLitePerformanceRepository:
    """Tests for SQLitePerformanceRepository."""

    def test_save_and_find(self, performance_repo):
        """Test saving and finding metrics."""
        today = date.today()
        metrics = PerformanceMetrics(
            account_id="acc_001",
            date=today,
            total_value_usd=15000.0,
            pnl_daily=500.0,
            pnl_total=2000.0,
            sharpe_ratio=1.5,
            win_rate=0.60,
        )

        performance_repo.save(metrics)

        found = performance_repo.find_by_date("acc_001", today)
        assert found is not None
        assert found.pnl_daily == 500.0

    def test_find_range(self, performance_repo):
        """Test finding metrics by date range."""
        today = date.today()

        for i in range(5):
            query_date = today - timedelta(days=i)
            metrics = PerformanceMetrics(
                account_id="acc_001",
                date=query_date,
                total_value_usd=10000.0 + i * 100,
                pnl_daily=100.0 * i,
                pnl_total=500.0 * i,
            )
            performance_repo.save(metrics)

        start = today - timedelta(days=4)
        end = today
        metrics_range = performance_repo.find_range("acc_001", start, end)
        assert len(metrics_range) == 5

    def test_find_latest(self, performance_repo):
        """Test finding latest metrics."""
        today = date.today()

        for i in range(10):
            query_date = today - timedelta(days=i)
            metrics = PerformanceMetrics(
                account_id="acc_001",
                date=query_date,
                total_value_usd=10000.0,
                pnl_daily=100.0,
                pnl_total=500.0,
            )
            performance_repo.save(metrics)

        latest = performance_repo.find_latest("acc_001", days=5)
        assert len(latest) <= 5

    def test_get_total_pnl(self, performance_repo):
        """Test calculating total P&L."""
        today = date.today()

        for i in range(5):
            query_date = today - timedelta(days=i)
            metrics = PerformanceMetrics(
                account_id="acc_001",
                date=query_date,
                total_value_usd=10000.0,
                pnl_daily=100.0 * (i + 1),
                pnl_total=100.0,
            )
            performance_repo.save(metrics)

        total = performance_repo.get_total_pnl("acc_001")
        # Sum of 100, 200, 300, 400, 500 = 1500
        assert total == 1500.0

    def test_get_best_day(self, performance_repo):
        """Test getting best performing day."""
        today = date.today()

        pnls = [100.0, 250.0, -50.0, 500.0, 75.0]
        for i, pnl in enumerate(pnls):
            query_date = today - timedelta(days=i)
            metrics = PerformanceMetrics(
                account_id="acc_001",
                date=query_date,
                total_value_usd=10000.0,
                pnl_daily=pnl,
                pnl_total=0.0,
            )
            performance_repo.save(metrics)

        best = performance_repo.get_best_day("acc_001")
        assert best is not None
        assert best.pnl_daily == 500.0

    def test_get_worst_day(self, performance_repo):
        """Test getting worst performing day."""
        today = date.today()

        pnls = [100.0, 250.0, -50.0, 500.0, 75.0]
        for i, pnl in enumerate(pnls):
            query_date = today - timedelta(days=i)
            metrics = PerformanceMetrics(
                account_id="acc_001",
                date=query_date,
                total_value_usd=10000.0,
                pnl_daily=pnl,
                pnl_total=0.0,
            )
            performance_repo.save(metrics)

        worst = performance_repo.get_worst_day("acc_001")
        assert worst is not None
        assert worst.pnl_daily == -50.0

    def test_get_metrics_count(self, performance_repo):
        """Test getting metrics count."""
        today = date.today()

        for i in range(10):
            query_date = today - timedelta(days=i)
            metrics = PerformanceMetrics(
                account_id="acc_001",
                date=query_date,
                total_value_usd=10000.0,
                pnl_daily=100.0,
                pnl_total=500.0,
            )
            performance_repo.save(metrics)

        count = performance_repo.get_metrics_count("acc_001")
        assert count == 10

    def test_delete_by_account(self, performance_repo):
        """Test deleting all metrics for account."""
        today = date.today()

        for i in range(5):
            query_date = today - timedelta(days=i)
            metrics = PerformanceMetrics(
                account_id="acc_001",
                date=query_date,
                total_value_usd=10000.0,
                pnl_daily=100.0,
                pnl_total=500.0,
            )
            performance_repo.save(metrics)

        deleted = performance_repo.delete_by_account("acc_001")
        assert deleted == 5

        count = performance_repo.get_metrics_count("acc_001")
        assert count == 0
