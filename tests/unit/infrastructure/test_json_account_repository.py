"""Tests for JsonAccountRepository."""

import json
import tempfile
from pathlib import Path

import pytest

from src.domain.account.entities.account import Account
from src.domain.account.value_objects.currency import Currency
from src.domain.account.value_objects.money import Money
from src.infrastructure.persistence.json_account_repository import (
    JsonAccountRepository,
)


@pytest.fixture
def temp_dir() -> Path:
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def repository(temp_dir: Path) -> JsonAccountRepository:
    """Create repository with temp directory."""
    return JsonAccountRepository(str(temp_dir))


class TestRepositoryCreation:
    """Test repository creation."""

    def test_create_repository(self, temp_dir: Path) -> None:
        """Test creating repository."""
        repo = JsonAccountRepository(str(temp_dir))
        assert (temp_dir / "accounts.json").exists()


class TestRepositorySave:
    """Test repository save operations."""

    def test_save_account(self, repository: JsonAccountRepository) -> None:
        """Test saving account."""
        account = Account(name="Test Account")
        account.deposit(Money(1000, Currency.USDT))

        repository.save(account)
        assert repository.exists(account.account_id)

    def test_save_multiple_accounts(
        self, repository: JsonAccountRepository
    ) -> None:
        """Test saving multiple accounts."""
        account1 = Account(name="Account 1")
        account1.deposit(Money(1000, Currency.USDT))

        account2 = Account(name="Account 2")
        account2.deposit(Money(2000, Currency.USDT))

        repository.save(account1)
        repository.save(account2)

        assert repository.exists(account1.account_id)
        assert repository.exists(account2.account_id)

    def test_save_account_with_multiple_currencies(
        self, repository: JsonAccountRepository
    ) -> None:
        """Test saving account with multiple currencies."""
        account = Account(name="Multi Currency")
        account.deposit(Money(1000, Currency.USDT))
        account.deposit(Money(0.5, Currency.BTC))
        account.deposit(Money(10, Currency.ETH))

        repository.save(account)
        retrieved = repository.find_by_id(account.account_id)

        assert retrieved is not None
        assert retrieved.get_available_balance(Currency.USDT).amount == 1000
        assert retrieved.get_available_balance(Currency.BTC).amount == 0.5
        assert retrieved.get_available_balance(Currency.ETH).amount == 10

    def test_save_account_with_transactions(
        self, repository: JsonAccountRepository
    ) -> None:
        """Test saving account with transaction history."""
        account = Account(name="With Transactions")
        account.deposit(Money(1000, Currency.USDT))
        account.withdraw(Money(100, Currency.USDT))
        account.record_fee(Money(1, Currency.USDT), "Trading fee")

        repository.save(account)
        retrieved = repository.find_by_id(account.account_id)

        assert retrieved is not None
        assert retrieved.get_transaction_count() == 3


class TestRepositoryFind:
    """Test repository find operations."""

    def test_find_by_id(self, repository: JsonAccountRepository) -> None:
        """Test finding account by ID."""
        account = Account(name="Find Me")
        account.deposit(Money(1000, Currency.USDT))
        repository.save(account)

        retrieved = repository.find_by_id(account.account_id)
        assert retrieved is not None
        assert retrieved.account_id == account.account_id
        assert retrieved.name == "Find Me"

    def test_find_by_id_not_found(
        self, repository: JsonAccountRepository
    ) -> None:
        """Test finding nonexistent account."""
        retrieved = repository.find_by_id("nonexistent")
        assert retrieved is None

    def test_find_by_name(self, repository: JsonAccountRepository) -> None:
        """Test finding account by name."""
        account = Account(name="Unique Name")
        account.deposit(Money(1000, Currency.USDT))
        repository.save(account)

        retrieved = repository.find_by_name("Unique Name")
        assert retrieved is not None
        assert retrieved.name == "Unique Name"

    def test_find_by_name_not_found(
        self, repository: JsonAccountRepository
    ) -> None:
        """Test finding nonexistent account by name."""
        retrieved = repository.find_by_name("Nonexistent")
        assert retrieved is None

    def test_find_all(self, repository: JsonAccountRepository) -> None:
        """Test finding all accounts."""
        account1 = Account(name="Account 1")
        account2 = Account(name="Account 2")
        account1.deposit(Money(1000, Currency.USDT))
        account2.deposit(Money(2000, Currency.USDT))

        repository.save(account1)
        repository.save(account2)

        all_accounts = repository.find_all()
        assert len(all_accounts) == 2

    def test_find_all_active(self, repository: JsonAccountRepository) -> None:
        """Test finding all active accounts."""
        account1 = Account(name="Active")
        account2 = Account(name="Closed")
        account1.deposit(Money(1000, Currency.USDT))
        account2.deposit(Money(2000, Currency.USDT))
        account2.close()

        repository.save(account1)
        repository.save(account2)

        active = repository.find_all_active()
        assert len(active) == 1
        assert active[0].name == "Active"


class TestRepositoryDelete:
    """Test repository delete operations."""

    def test_delete_account(self, repository: JsonAccountRepository) -> None:
        """Test deleting account."""
        account = Account(name="To Delete")
        account.deposit(Money(1000, Currency.USDT))
        repository.save(account)

        assert repository.exists(account.account_id)
        deleted = repository.delete(account.account_id)
        assert deleted
        assert not repository.exists(account.account_id)

    def test_delete_nonexistent(
        self, repository: JsonAccountRepository
    ) -> None:
        """Test deleting nonexistent account."""
        deleted = repository.delete("nonexistent")
        assert not deleted


class TestRepositoryExists:
    """Test repository exists check."""

    def test_exists_true(self, repository: JsonAccountRepository) -> None:
        """Test exists returns true for saved account."""
        account = Account(name="Exists")
        account.deposit(Money(1000, Currency.USDT))
        repository.save(account)

        assert repository.exists(account.account_id)

    def test_exists_false(self, repository: JsonAccountRepository) -> None:
        """Test exists returns false for nonexistent."""
        assert not repository.exists("nonexistent")


class TestRepositoryPersistence:
    """Test repository persistence across instances."""

    def test_data_persists_across_instances(
        self, temp_dir: Path
    ) -> None:
        """Test that data persists when creating new repository."""
        # Create and save account
        repo1 = JsonAccountRepository(str(temp_dir))
        account = Account(name="Persistent")
        account.deposit(Money(1000, Currency.USDT))
        repo1.save(account)

        # Create new repository instance
        repo2 = JsonAccountRepository(str(temp_dir))
        retrieved = repo2.find_by_name("Persistent")

        assert retrieved is not None
        assert retrieved.name == "Persistent"
        assert retrieved.get_available_balance(Currency.USDT).amount == 1000


class TestRepositoryBalance:
    """Test repository handles balance state correctly."""

    def test_balance_available_and_reserved(
        self, repository: JsonAccountRepository
    ) -> None:
        """Test that available and reserved balance persists."""
        account = Account(name="Complex Balance")
        account.deposit(Money(1000, Currency.USDT))
        account.balance.reserve(Money(200, Currency.USDT))

        repository.save(account)
        retrieved = repository.find_by_id(account.account_id)

        assert retrieved is not None
        assert retrieved.get_available_balance(Currency.USDT).amount == 800
        assert retrieved.balance.get_reserved(Currency.USDT).amount == 200

    def test_closed_account_state(
        self, repository: JsonAccountRepository
    ) -> None:
        """Test that closed account state persists."""
        account = Account(name="Closed Account")
        account.deposit(Money(1000, Currency.USDT))
        account.close()

        repository.save(account)
        retrieved = repository.find_by_id(account.account_id)

        assert retrieved is not None
        assert not retrieved.is_active
        assert retrieved.closed_at is not None
