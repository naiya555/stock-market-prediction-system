"""SQLite Database Connection Management.

Provides connection factory with WAL mode, foreign key enforcement,
busy timeout handling, and transactional session context management.
"""

from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Generator, Optional, Union

from app.core.config import get_settings


def get_default_db_path() -> Path:
    """Return the default SQLite database path configured in settings."""
    settings = get_settings()
    return settings.data_dir / "predictions.db"


def create_connection(
    db_path: Optional[Union[str, Path]] = None,
    timeout: float = 10.0,
) -> sqlite3.Connection:
    """Create and configure a SQLite connection.

    Args:
        db_path: Path to SQLite database file or ':memory:'. Defaults to settings.data_dir/predictions.db.
        timeout: Lock acquisition timeout in seconds.

    Returns:
        Configured sqlite3.Connection with foreign keys enabled, Row factory, and WAL mode.
    """
    if db_path is None:
        target_path = str(get_default_db_path())
    else:
        target_path = str(db_path)

    # Ensure parent directory exists for file-based databases
    if target_path != ":memory:":
        Path(target_path).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(target_path, timeout=timeout)
    conn.row_factory = sqlite3.Row

    # Enforce SQLite performance and safety pragmas
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 5000;")

    # WAL mode is supported only for file-based databases
    if target_path != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL;")

    return conn


@contextmanager
def db_session(
    db_path: Optional[Union[str, Path]] = None,
    existing_conn: Optional[sqlite3.Connection] = None,
) -> Generator[sqlite3.Connection, None, None]:
    """Context manager providing a transactional database connection.

    Automatically commits on successful block exit, rolls back on error,
    and closes the connection if it was created locally.
    """
    if existing_conn is not None:
        yield existing_conn
        return

    conn = create_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
