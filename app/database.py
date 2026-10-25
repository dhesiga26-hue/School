"""SQLite database connection and schema management.

This module owns all direct interaction with SQLite. Every query executed
elsewhere in the application goes through a connection created here, and all
statements use parameter binding to avoid SQL injection.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from typing import Iterator

# Project root is the parent directory of this ``app`` package.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_DB_PATH = os.path.join(_PROJECT_ROOT, "students.db")

# Schema is created on startup and is safe to run repeatedly.
_CREATE_STUDENTS_TABLE = """
CREATE TABLE IF NOT EXISTS students (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL,
    date_of_birth TEXT    NOT NULL,
    email         TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    phone         TEXT    NOT NULL,
    course        TEXT    NOT NULL,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""


def get_database_path() -> str:
    """Return the active database path.

    The path can be overridden with the ``STUDENTS_DB_PATH`` environment
    variable, which allows tests to use an isolated temporary database without
    touching real application data.
    """
    return os.environ.get("STUDENTS_DB_PATH", _DEFAULT_DB_PATH)


def _connect() -> sqlite3.Connection:
    """Open a new SQLite connection with row access by column name."""
    connection = sqlite3.connect(get_database_path())
    connection.row_factory = sqlite3.Row
    return connection


@contextmanager
def db_session() -> Iterator[sqlite3.Connection]:
    """Provide a transactional SQLite connection.

    Commits on success, rolls back on error and always closes the connection.
    """
    connection = _connect()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db() -> None:
    """Create the database file and required tables if they do not exist."""
    with db_session() as connection:
        connection.execute(_CREATE_STUDENTS_TABLE)
