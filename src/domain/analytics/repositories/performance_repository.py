"""Performance repository for analytics."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from typing import List, Optional


@dataclass
class PerformanceMetrics:
    """Performance metrics for a trading day."""

    account_id: str
    date: date
    total_value_usd: float
    pnl_daily: float
    pnl_total: float
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    win_rate: Optional[float] = None
    profit_factor: Optional[float] = None
    trades_count: Optional[int] = None
    created_at: datetime = None

    def __post_init__(self):
        """Set default created_at."""
        if self.created_at is None:
            self.created_at = datetime.utcnow()

    def get_summary(self) -> dict:
        """Get metrics summary."""
        return {
            "account_id": self.account_id,
            "date": self.date.isoformat(),
            "total_value_usd": self.total_value_usd,
            "pnl_daily": self.pnl_daily,
            "pnl_total": self.pnl_total,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "max_drawdown": self.max_drawdown,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "trades_count": self.trades_count,
        }


class PerformanceRepository(ABC):
    """
    Repository abstraction for Performance metrics.

    Stores and retrieves daily performance metrics, analytics,
    and key performance indicators.
    """

    @abstractmethod
    def save(self, metrics: PerformanceMetrics) -> None:
        """
        Save performance metrics.

        Args:
            metrics: Performance metrics to save

        Raises:
            RepositoryException: If save fails
        """
        pass

    @abstractmethod
    def find_by_date(self, account_id: str, date: date) -> Optional[PerformanceMetrics]:
        """
        Find metrics for specific date.

        Args:
            account_id: Account ID
            date: Date to query

        Returns:
            PerformanceMetrics if found, None otherwise

        Raises:
            RepositoryException: If query fails
        """
        pass

    @abstractmethod
    def find_range(
        self, account_id: str, start_date: date, end_date: date
    ) -> List[PerformanceMetrics]:
        """
        Find metrics for date range.

        Args:
            account_id: Account ID
            start_date: Start date
            end_date: End date

        Returns:
            List of metrics in range

        Raises:
            RepositoryException: If query fails
        """
        pass

    @abstractmethod
    def find_latest(self, account_id: str, days: int = 30) -> List[PerformanceMetrics]:
        """
        Find latest metrics.

        Args:
            account_id: Account ID
            days: Number of days to retrieve

        Returns:
            List of recent metrics

        Raises:
            RepositoryException: If query fails
        """
        pass

    @abstractmethod
    def get_average_metrics(
        self, account_id: str, days: int = 30
    ) -> Optional[dict]:
        """
        Get average metrics for period.

        Args:
            account_id: Account ID
            days: Number of days

        Returns:
            Dictionary with average values or None

        Raises:
            RepositoryException: If query fails
        """
        pass

    @abstractmethod
    def get_best_day(self, account_id: str) -> Optional[PerformanceMetrics]:
        """
        Get best performing day.

        Args:
            account_id: Account ID

        Returns:
            PerformanceMetrics with highest P&L or None

        Raises:
            RepositoryException: If query fails
        """
        pass

    @abstractmethod
    def get_worst_day(self, account_id: str) -> Optional[PerformanceMetrics]:
        """
        Get worst performing day.

        Args:
            account_id: Account ID

        Returns:
            PerformanceMetrics with lowest P&L or None

        Raises:
            RepositoryException: If query fails
        """
        pass

    @abstractmethod
    def get_total_pnl(self, account_id: str) -> float:
        """
        Get total cumulative P&L.

        Args:
            account_id: Account ID

        Returns:
            Total P&L in USD

        Raises:
            RepositoryException: If query fails
        """
        pass

    @abstractmethod
    def get_metrics_count(self, account_id: str) -> int:
        """
        Get total metrics count.

        Args:
            account_id: Account ID

        Returns:
            Number of metric records

        Raises:
            RepositoryException: If query fails
        """
        pass

    @abstractmethod
    def delete_by_account(self, account_id: str) -> int:
        """
        Delete all metrics for account.

        Args:
            account_id: Account ID

        Returns:
            Number of deleted records

        Raises:
            RepositoryException: If delete fails
        """
        pass

    @abstractmethod
    def export_to_csv(self, account_id: str, filepath: str) -> None:
        """
        Export metrics to CSV.

        Args:
            account_id: Account ID
            filepath: Output file path

        Raises:
            OSError: If export fails
        """
        pass
