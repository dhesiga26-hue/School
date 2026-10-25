"""Shared pytest fixtures.

Every test runs against its own temporary SQLite database so real application
data is never modified or deleted.
"""

from __future__ import annotations

import os
import sys

import pytest
from fastapi.testclient import TestClient

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """Provide a TestClient wired to a fresh temporary database."""
    db_file = tmp_path / "test_students.db"
    monkeypatch.setenv("STUDENTS_DB_PATH", str(db_file))

    from app.database import init_db
    from app.main import app

    init_db()
    with TestClient(app) as test_client:
        yield test_client