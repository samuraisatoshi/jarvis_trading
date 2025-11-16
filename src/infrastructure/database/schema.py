"""SQLite schema initialization and management."""

import sqlite3
from pathlib import Path
from typing import Optional


def init_database(db_path: str) -> None:
    """
    Initialize SQLite database with schema.

    Creates tables, indexes, and enables optimizations.

    Args:
        db_path: Path to SQLite database file

    Raises:
        sqlite3.DatabaseError: If schema creation fails
    """
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()

        # Enable optimizations
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute("PRAGMA journal_mode = WAL")
        cursor.execute("PRAGMA synchronous = NORMAL")
        cursor.execute("PRAGMA cache_size = -2000")  # 2MB cache
        cursor.execute("PRAGMA auto_vacuum = INCREMENTAL")

        # Read and execute schema
        schema_path = Path(__file__).parent / "schema.sql"
        with open(schema_path, "r") as f:
            schema_sql = f.read()

        # Split by semicolon and execute each statement
        for statement in schema_sql.split(";"):
            statement = statement.strip()
            if statement:
                cursor.execute(statement)

        conn.commit()
    finally:
        conn.close()


def get_schema_version() -> str:
    """
    Get current schema version.

    Returns:
        Version string (YYYYMMDD_HH format)
    """
    return "20251114_001"


def verify_database(db_path: str) -> bool:
    """
    Verify database integrity and schema.

    Args:
        db_path: Path to SQLite database file

    Returns:
        True if database is valid, False otherwise
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check for required tables
        required_tables = [
            "accounts",
            "balances",
            "transactions",
            "orders",
            "performance_metrics",
        ]

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        existing_tables = {row[0] for row in cursor.fetchall()}

        for table in required_tables:
            if table not in existing_tables:
                return False

        # Run PRAGMA integrity_check
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()

        conn.close()
        return result[0] == "ok"

    except sqlite3.Error:
        return False


def get_database_stats(db_path: str) -> dict:
    """
    Get database statistics.

    Args:
        db_path: Path to SQLite database file

    Returns:
        Dictionary with database statistics

    Raises:
        sqlite3.DatabaseError: If query fails
    """
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()

        stats = {
            "file_size_mb": Path(db_path).stat().st_size / (1024 * 1024),
            "tables": {},
        }

        tables = [
            "accounts",
            "balances",
            "transactions",
            "orders",
            "performance_metrics",
        ]

        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                stats["tables"][table] = count
            except sqlite3.OperationalError:
                stats["tables"][table] = 0

        return stats

    finally:
        conn.close()


def cleanup_database(db_path: str, keep_days: int = 30) -> int:
    """
    Clean up old records and vacuum database.

    Args:
        db_path: Path to SQLite database file
        keep_days: Number of days of data to keep

    Returns:
        Number of records deleted
    """
    from datetime import datetime, timedelta

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()

        cutoff_date = (datetime.utcnow() - timedelta(days=keep_days)).isoformat()

        # Delete old transactions
        cursor.execute(
            "DELETE FROM transactions WHERE created_at < ?", (cutoff_date,)
        )
        deleted = cursor.rowcount

        # Delete old orders
        cursor.execute(
            "DELETE FROM orders WHERE created_at < ? AND status IN ('FILLED', 'CANCELLED')",
            (cutoff_date,),
        )
        deleted += cursor.rowcount

        # Vacuum to reclaim space
        cursor.execute("VACUUM")

        conn.commit()
        return deleted

    finally:
        conn.close()
