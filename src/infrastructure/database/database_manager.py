"""SQLite database manager with connection pooling and transactions."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from threading import Lock
from typing import Optional, Tuple

from loguru import logger

from .schema import init_database, verify_database


class DatabaseManager:
    """
    Manage SQLite database connections with pooling and transaction support.

    Features:
    - Connection pooling for efficient resource usage
    - Automatic transaction management
    - WAL mode for better concurrency
    - Backup functionality
    - Type-safe queries
    """

    def __init__(self, db_path: str, max_connections: int = 5):
        """
        Initialize DatabaseManager.

        Args:
            db_path: Path to SQLite database file
            max_connections: Maximum connections in pool

        Raises:
            ValueError: If db_path is invalid
        """
        if not db_path:
            raise ValueError("db_path cannot be empty")

        self.db_path = str(Path(db_path).resolve())
        self.max_connections = max_connections
        self._connections: list[sqlite3.Connection] = []
        self._lock = Lock()
        self._initialized = False

        # Create database if not exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"DatabaseManager initialized: {self.db_path}")

    def initialize(self) -> None:
        """
        Initialize database with schema and optimizations.

        Raises:
            sqlite3.DatabaseError: If initialization fails
        """
        if self._initialized:
            logger.debug("Database already initialized")
            return

        try:
            init_database(self.db_path)
            verified = verify_database(self.db_path)

            if not verified:
                raise sqlite3.DatabaseError("Database verification failed")

            self._initialized = True
            logger.info(f"Database initialized: {self.db_path}")

        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """
        Get database connection from pool.

        Yields:
            sqlite3.Connection: Database connection

        Example:
            with manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM accounts")
        """
        if not self._initialized:
            self.initialize()

        conn: Optional[sqlite3.Connection] = None

        with self._lock:
            if len(self._connections) > 0:
                conn = self._connections.pop()
            else:
                conn = sqlite3.connect(self.db_path, check_same_thread=False)
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA foreign_keys = ON")
                conn.execute("PRAGMA journal_mode = WAL")

        try:
            yield conn
        finally:
            with self._lock:
                if len(self._connections) < self.max_connections:
                    self._connections.append(conn)
                else:
                    conn.close()

    @contextmanager
    def transaction(self):
        """
        Context manager for database transactions.

        Auto-commits on success, rolls back on exception.

        Yields:
            sqlite3.Connection: Database connection

        Example:
            with manager.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO accounts ...")
                # Auto-committed on exit
        """
        with self.get_connection() as conn:
            try:
                yield conn
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"Transaction rolled back: {e}")
                raise

    def execute_query(self, sql: str, params: Tuple = ()) -> list[sqlite3.Row]:
        """
        Execute SELECT query.

        Args:
            sql: SQL query string
            params: Query parameters (for parameterized queries)

        Returns:
            List of result rows

        Raises:
            sqlite3.DatabaseError: If query fails
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Query failed: {e}")
            raise sqlite3.DatabaseError(f"Query execution failed: {e}")

    def execute_update(self, sql: str, params: Tuple = ()) -> int:
        """
        Execute INSERT/UPDATE/DELETE query.

        Args:
            sql: SQL query string
            params: Query parameters

        Returns:
            Number of affected rows

        Raises:
            sqlite3.DatabaseError: If update fails
        """
        try:
            with self.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                return cursor.rowcount
        except sqlite3.Error as e:
            logger.error(f"Update failed: {e}")
            raise sqlite3.DatabaseError(f"Update execution failed: {e}")

    def execute_many(self, sql: str, params_list: list[Tuple]) -> int:
        """
        Execute INSERT/UPDATE/DELETE for many records.

        Args:
            sql: SQL query string
            params_list: List of parameter tuples

        Returns:
            Total number of affected rows

        Raises:
            sqlite3.DatabaseError: If execution fails
        """
        try:
            with self.transaction() as conn:
                cursor = conn.cursor()
                cursor.executemany(sql, params_list)
                return cursor.rowcount
        except sqlite3.Error as e:
            logger.error(f"Batch update failed: {e}")
            raise sqlite3.DatabaseError(f"Batch execution failed: {e}")

    def close(self) -> None:
        """Close all pooled connections."""
        with self._lock:
            for conn in self._connections:
                try:
                    conn.close()
                except sqlite3.Error as e:
                    logger.warning(f"Error closing connection: {e}")
            self._connections.clear()

        logger.info("Database connections closed")

    def backup(self, backup_path: str) -> None:
        """
        Create database backup.

        Args:
            backup_path: Path for backup file

        Raises:
            OSError: If backup fails
        """
        try:
            backup_file = Path(backup_path).resolve()
            backup_file.parent.mkdir(parents=True, exist_ok=True)

            with self.get_connection() as source_conn:
                backup_conn = sqlite3.connect(str(backup_file))
                try:
                    source_conn.backup(backup_conn)
                    logger.info(f"Database backed up to: {backup_path}")
                finally:
                    backup_conn.close()

        except Exception as e:
            logger.error(f"Backup failed: {e}")
            raise OSError(f"Database backup failed: {e}")

    def restore(self, backup_path: str) -> None:
        """
        Restore database from backup.

        Args:
            backup_path: Path to backup file

        Raises:
            OSError: If restore fails
        """
        try:
            self.close()

            backup_file = Path(backup_path)
            if not backup_file.exists():
                raise FileNotFoundError(f"Backup file not found: {backup_path}")

            # Copy backup to current db
            backup_conn = sqlite3.connect(str(backup_file))
            try:
                with self.get_connection() as db_conn:
                    backup_conn.backup(db_conn)
                    logger.info(f"Database restored from: {backup_path}")
            finally:
                backup_conn.close()

            self._initialized = False
            self.initialize()

        except Exception as e:
            logger.error(f"Restore failed: {e}")
            raise OSError(f"Database restore failed: {e}")

    def __enter__(self):
        """Context manager entry."""
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
