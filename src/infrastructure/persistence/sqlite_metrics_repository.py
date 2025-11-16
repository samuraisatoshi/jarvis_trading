"""
SQLite Metrics Repository

Handles database queries for performance metrics used by monitoring.
Encapsulates all metric-related database access.
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

from src.domain.monitoring import PerformanceMetrics


class SQLiteMetricsRepository:
    """
    Repository for fetching performance metrics from SQLite database.

    Provides clean interface for monitoring queries without exposing
    raw SQL to application layer.
    """

    def __init__(self, db_path: Path):
        """
        Initialize metrics repository.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path

    def get_portfolio_value(self) -> float:
        """
        Get current portfolio value.

        Returns:
            Current portfolio value, or 10000.0 if no data
        """
        if not self.db_path.exists():
            return 10000.0

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT value FROM portfolio_state "
                    "ORDER BY timestamp DESC LIMIT 1"
                )
                row = cursor.fetchone()
                return row[0] if row else 10000.0
        except Exception:
            return 10000.0

    def get_daily_trades_summary(self) -> Dict:
        """
        Get summary of today's trades.

        Returns:
            Dict with total, winning, losing counts and total PNL
        """
        if not self.db_path.exists():
            return {
                'total': 0,
                'winning': 0,
                'losing': 0,
                'pnl': 0.0
            }

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                today_start = datetime.now().replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                cursor.execute(
                    "SELECT COUNT(*), "
                    "SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END), "
                    "SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END), "
                    "SUM(pnl) "
                    "FROM trades "
                    "WHERE exit_timestamp >= ? AND status = 'CLOSED'",
                    (today_start.timestamp(),)
                )
                row = cursor.fetchone()
                return {
                    'total': row[0] or 0,
                    'winning': row[1] or 0,
                    'losing': row[2] or 0,
                    'pnl': row[3] or 0.0
                }
        except Exception:
            return {
                'total': 0,
                'winning': 0,
                'losing': 0,
                'pnl': 0.0
            }

    def get_consecutive_losses(self, limit: int = 10) -> int:
        """
        Get count of consecutive losing trades.

        Args:
            limit: Maximum number of recent trades to check

        Returns:
            Number of consecutive losses
        """
        if not self.db_path.exists():
            return 0

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT pnl FROM trades "
                    "WHERE status = 'CLOSED' "
                    "ORDER BY exit_timestamp DESC LIMIT ?",
                    (limit,)
                )
                recent_pnls = [row[0] for row in cursor.fetchall()]

                consecutive = 0
                for pnl in recent_pnls:
                    if pnl < 0:
                        consecutive += 1
                    else:
                        break
                return consecutive
        except Exception:
            return 0

    def get_drawdown(self, days: int = 30) -> float:
        """
        Calculate maximum drawdown over period.

        Args:
            days: Number of days to look back

        Returns:
            Drawdown as percentage (0.0 to 1.0)
        """
        if not self.db_path.exists():
            return 0.0

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                since = (datetime.now() - timedelta(days=days)).timestamp()

                cursor.execute(
                    "SELECT MAX(value) - MIN(value) FROM portfolio_state "
                    "WHERE timestamp >= ?",
                    (since,)
                )
                row = cursor.fetchone()

                if not row or not row[0]:
                    return 0.0

                # Get current value for percentage
                current_value = self.get_portfolio_value()
                return row[0] / current_value if current_value > 0 else 0.0
        except Exception:
            return 0.0

    def get_active_positions_count(self) -> int:
        """
        Get number of currently active positions.

        Returns:
            Count of active positions
        """
        if not self.db_path.exists():
            return 0

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) FROM trades WHERE status = 'ACTIVE'"
                )
                return cursor.fetchone()[0]
        except Exception:
            return 0

    def get_api_latency(self) -> float:
        """
        Get most recent API latency measurement.

        Returns:
            Latency in milliseconds, or 100.0 if no data
        """
        if not self.db_path.exists():
            return 100.0

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT latency_ms FROM api_health "
                    "ORDER BY timestamp DESC LIMIT 1"
                )
                row = cursor.fetchone()
                return row[0] if row else 100.0
        except Exception:
            return 100.0

    def get_data_freshness(self) -> float:
        """
        Get age of most recent market data.

        Returns:
            Seconds since last market data update
        """
        if not self.db_path.exists():
            return 0.0

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT MAX(timestamp) FROM market_data"
                )
                row = cursor.fetchone()

                if row and row[0]:
                    last_update = datetime.fromtimestamp(row[0])
                    return (datetime.now() - last_update).total_seconds()
                return 0.0
        except Exception:
            return 0.0

    def get_performance_metrics(self) -> PerformanceMetrics:
        """
        Get comprehensive performance metrics.

        Aggregates all metric queries into PerformanceMetrics entity.

        Returns:
            PerformanceMetrics with current state
        """
        portfolio_value = self.get_portfolio_value()
        daily_summary = self.get_daily_trades_summary()
        consecutive_losses = self.get_consecutive_losses()
        drawdown = self.get_drawdown()
        active_positions = self.get_active_positions_count()
        api_latency = self.get_api_latency()
        data_freshness = self.get_data_freshness()

        # Calculate derived metrics
        total_trades = daily_summary['total']
        winning_trades = daily_summary['winning']
        daily_pnl = daily_summary['pnl']

        win_rate = (
            winning_trades / total_trades
            if total_trades > 0 else 0.0
        )
        daily_pnl_pct = daily_pnl / portfolio_value if portfolio_value > 0 else 0.0

        # TODO: Calculate actual Sharpe and profit factor from historical data
        sharpe_ratio = 1.5  # Placeholder
        profit_factor = 2.0  # Placeholder

        return PerformanceMetrics(
            timestamp=datetime.now(),
            portfolio_value=portfolio_value,
            daily_pnl=daily_pnl,
            daily_pnl_pct=daily_pnl_pct,
            drawdown=drawdown,
            sharpe_ratio=sharpe_ratio,
            win_rate=win_rate,
            profit_factor=profit_factor,
            active_positions=active_positions,
            total_trades_today=total_trades,
            winning_trades_today=winning_trades,
            losing_trades_today=daily_summary['losing'],
            consecutive_losses=consecutive_losses,
            api_latency_ms=api_latency,
            data_freshness_seconds=data_freshness
        )
