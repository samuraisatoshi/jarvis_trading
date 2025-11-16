"""SQLite implementation of PerformanceRepository."""

import csv
from datetime import date, datetime
from typing import List, Optional

from loguru import logger

from src.domain.analytics.repositories.performance_repository import (
    PerformanceMetrics,
    PerformanceRepository,
)
from src.infrastructure.database import DatabaseManager


class SQLitePerformanceRepository(PerformanceRepository):
    """
    SQLite implementation of PerformanceRepository.

    Stores and queries daily performance metrics and analytics.
    """

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize SQLitePerformanceRepository.

        Args:
            db_manager: Database manager instance
        """
        self.db = db_manager
        logger.debug("SQLitePerformanceRepository initialized")

    def save(self, metrics: PerformanceMetrics) -> None:
        """
        Save performance metrics.

        Args:
            metrics: Performance metrics to save

        Raises:
            sqlite3.DatabaseError: If save fails
        """
        try:
            self.db.execute_update(
                """
                INSERT OR REPLACE INTO performance_metrics
                (account_id, date, total_value_usd, pnl_daily, pnl_total,
                 sharpe_ratio, sortino_ratio, max_drawdown, win_rate,
                 profit_factor, trades_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    metrics.account_id,
                    metrics.date.isoformat(),
                    metrics.total_value_usd,
                    metrics.pnl_daily,
                    metrics.pnl_total,
                    metrics.sharpe_ratio,
                    metrics.sortino_ratio,
                    metrics.max_drawdown,
                    metrics.win_rate,
                    metrics.profit_factor,
                    metrics.trades_count,
                ),
            )
            logger.debug(f"Performance metrics saved: {metrics.account_id} {metrics.date}")

        except Exception as e:
            logger.error(f"Failed to save performance metrics: {e}")
            raise

    def find_by_date(self, account_id: str, query_date: date) -> Optional[PerformanceMetrics]:
        """
        Find metrics for specific date.

        Args:
            account_id: Account ID
            query_date: Date to query

        Returns:
            PerformanceMetrics if found, None otherwise

        Raises:
            sqlite3.DatabaseError: If query fails
        """
        try:
            rows = self.db.execute_query(
                """
                SELECT * FROM performance_metrics
                WHERE account_id = ? AND date = ?
                """,
                (account_id, query_date.isoformat()),
            )

            if not rows:
                return None

            return self._row_to_metrics(rows[0])

        except Exception as e:
            logger.error(f"Failed to find metrics by date: {e}")
            raise

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
            sqlite3.DatabaseError: If query fails
        """
        try:
            rows = self.db.execute_query(
                """
                SELECT * FROM performance_metrics
                WHERE account_id = ? AND date BETWEEN ? AND ?
                ORDER BY date DESC
                """,
                (account_id, start_date.isoformat(), end_date.isoformat()),
            )

            return [self._row_to_metrics(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to find metrics by range: {e}")
            raise

    def find_latest(self, account_id: str, days: int = 30) -> List[PerformanceMetrics]:
        """
        Find latest metrics.

        Args:
            account_id: Account ID
            days: Number of days to retrieve

        Returns:
            List of recent metrics

        Raises:
            sqlite3.DatabaseError: If query fails
        """
        try:
            rows = self.db.execute_query(
                """
                SELECT * FROM performance_metrics
                WHERE account_id = ?
                ORDER BY date DESC
                LIMIT ?
                """,
                (account_id, days),
            )

            return [self._row_to_metrics(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to find latest metrics: {e}")
            raise

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
            sqlite3.DatabaseError: If query fails
        """
        try:
            rows = self.db.execute_query(
                """
                SELECT
                    AVG(pnl_daily) as avg_pnl_daily,
                    AVG(pnl_total) as avg_pnl_total,
                    AVG(sharpe_ratio) as avg_sharpe_ratio,
                    AVG(sortino_ratio) as avg_sortino_ratio,
                    AVG(max_drawdown) as avg_max_drawdown,
                    AVG(win_rate) as avg_win_rate,
                    AVG(profit_factor) as avg_profit_factor,
                    AVG(trades_count) as avg_trades_count
                FROM performance_metrics
                WHERE account_id = ?
                ORDER BY date DESC
                LIMIT ?
                """,
                (account_id, days),
            )

            if not rows:
                return None

            row = rows[0]
            return {
                "avg_pnl_daily": row["avg_pnl_daily"],
                "avg_pnl_total": row["avg_pnl_total"],
                "avg_sharpe_ratio": row["avg_sharpe_ratio"],
                "avg_sortino_ratio": row["avg_sortino_ratio"],
                "avg_max_drawdown": row["avg_max_drawdown"],
                "avg_win_rate": row["avg_win_rate"],
                "avg_profit_factor": row["avg_profit_factor"],
                "avg_trades_count": row["avg_trades_count"],
            }

        except Exception as e:
            logger.error(f"Failed to get average metrics: {e}")
            raise

    def get_best_day(self, account_id: str) -> Optional[PerformanceMetrics]:
        """
        Get best performing day.

        Args:
            account_id: Account ID

        Returns:
            PerformanceMetrics with highest P&L or None

        Raises:
            sqlite3.DatabaseError: If query fails
        """
        try:
            rows = self.db.execute_query(
                """
                SELECT * FROM performance_metrics
                WHERE account_id = ?
                ORDER BY pnl_daily DESC
                LIMIT 1
                """,
                (account_id,),
            )

            return self._row_to_metrics(rows[0]) if rows else None

        except Exception as e:
            logger.error(f"Failed to get best day: {e}")
            raise

    def get_worst_day(self, account_id: str) -> Optional[PerformanceMetrics]:
        """
        Get worst performing day.

        Args:
            account_id: Account ID

        Returns:
            PerformanceMetrics with lowest P&L or None

        Raises:
            sqlite3.DatabaseError: If query fails
        """
        try:
            rows = self.db.execute_query(
                """
                SELECT * FROM performance_metrics
                WHERE account_id = ?
                ORDER BY pnl_daily ASC
                LIMIT 1
                """,
                (account_id,),
            )

            return self._row_to_metrics(rows[0]) if rows else None

        except Exception as e:
            logger.error(f"Failed to get worst day: {e}")
            raise

    def get_total_pnl(self, account_id: str) -> float:
        """
        Get total cumulative P&L.

        Args:
            account_id: Account ID

        Returns:
            Total P&L in USD

        Raises:
            sqlite3.DatabaseError: If query fails
        """
        try:
            rows = self.db.execute_query(
                """
                SELECT COALESCE(SUM(pnl_daily), 0) as total
                FROM performance_metrics
                WHERE account_id = ?
                """,
                (account_id,),
            )

            return float(rows[0]["total"]) if rows else 0.0

        except Exception as e:
            logger.error(f"Failed to get total P&L: {e}")
            raise

    def get_metrics_count(self, account_id: str) -> int:
        """
        Get total metrics count.

        Args:
            account_id: Account ID

        Returns:
            Number of metric records

        Raises:
            sqlite3.DatabaseError: If query fails
        """
        try:
            rows = self.db.execute_query(
                "SELECT COUNT(*) as count FROM performance_metrics WHERE account_id = ?",
                (account_id,),
            )

            return int(rows[0]["count"]) if rows else 0

        except Exception as e:
            logger.error(f"Failed to get metrics count: {e}")
            raise

    def delete_by_account(self, account_id: str) -> int:
        """
        Delete all metrics for account.

        Args:
            account_id: Account ID

        Returns:
            Number of deleted records

        Raises:
            sqlite3.DatabaseError: If delete fails
        """
        try:
            affected = self.db.execute_update(
                "DELETE FROM performance_metrics WHERE account_id = ?",
                (account_id,),
            )
            logger.debug(f"Deleted {affected} metric records for account {account_id}")
            return affected

        except Exception as e:
            logger.error(f"Failed to delete metrics: {e}")
            raise

    def get_by_date_range(
        self, account_id: str, start_date: date, end_date: date
    ) -> List[PerformanceMetrics]:
        """
        Get metrics for date range (alias for find_range).

        Args:
            account_id: Account ID
            start_date: Start date
            end_date: End date

        Returns:
            List of metrics in range
        """
        return self.find_range(account_id, start_date, end_date)

    def export_to_csv(self, account_id: str, filepath: str) -> None:
        """
        Export metrics to CSV.

        Args:
            account_id: Account ID
            filepath: Output file path

        Raises:
            OSError: If export fails
        """
        try:
            metrics_list = self.find_latest(account_id, days=10000)

            with open(filepath, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "Date",
                        "Total Value (USD)",
                        "Daily P&L",
                        "Total P&L",
                        "Sharpe Ratio",
                        "Sortino Ratio",
                        "Max Drawdown",
                        "Win Rate",
                        "Profit Factor",
                        "Trades Count",
                    ]
                )

                for metrics in metrics_list:
                    writer.writerow(
                        [
                            metrics.date.isoformat(),
                            f"{metrics.total_value_usd:.2f}",
                            f"{metrics.pnl_daily:.2f}",
                            f"{metrics.pnl_total:.2f}",
                            f"{metrics.sharpe_ratio:.4f}" if metrics.sharpe_ratio else "",
                            f"{metrics.sortino_ratio:.4f}"
                            if metrics.sortino_ratio
                            else "",
                            f"{metrics.max_drawdown:.4f}" if metrics.max_drawdown else "",
                            f"{metrics.win_rate:.2%}" if metrics.win_rate else "",
                            f"{metrics.profit_factor:.2f}" if metrics.profit_factor else "",
                            metrics.trades_count or "",
                        ]
                    )

            logger.info(f"Exported {len(metrics_list)} metric records to {filepath}")

        except Exception as e:
            logger.error(f"Failed to export metrics to CSV: {e}")
            raise OSError(f"Export failed: {e}")

    def _row_to_metrics(self, row) -> PerformanceMetrics:
        """
        Convert database row to PerformanceMetrics.

        Args:
            row: Database row

        Returns:
            PerformanceMetrics entity
        """
        return PerformanceMetrics(
            account_id=row["account_id"],
            date=date.fromisoformat(row["date"]),
            total_value_usd=row["total_value_usd"],
            pnl_daily=row["pnl_daily"],
            pnl_total=row["pnl_total"],
            sharpe_ratio=row["sharpe_ratio"],
            sortino_ratio=row["sortino_ratio"],
            max_drawdown=row["max_drawdown"],
            win_rate=row["win_rate"],
            profit_factor=row["profit_factor"],
            trades_count=row["trades_count"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )
