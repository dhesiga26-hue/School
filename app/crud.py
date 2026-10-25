"""Data access layer for student records.

Contains all SQL statements. Exceptions defined here are translated into HTTP
errors by the route layer, keeping the API layer free of database details and
keeping database users free of internal exception data.
"""

from __future__ import annotations

import sqlite3
from typing import List, Optional

from app import schemas
from app.database import db_session

# Columns read back in a stable, documented order.
_STUDENT_COLUMNS = (
    "id",
    "name",
    "date_of_birth",
    "email",
    "phone",
    "course",
    "created_at",
    "updated_at",
)


class StudentNotFoundError(Exception):
    """Raised when a student id does not exist."""


class DuplicateEmailError(Exception):
    """Raised when an email is already assigned to another student."""


def _row_to_dict(row: sqlite3.Row) -> dict:
    """Convert a sqlite Row into a plain dict."""
    return {column: row[column] for column in _STUDENT_COLUMNS}


def _handle_integrity_error(error: sqlite3.IntegrityError) -> None:
    """Translate database integrity errors into domain exceptions."""
    if "UNIQUE" in str(error):
        raise DuplicateEmailError("email already registered") from error
    raise error


def create_student(payload: schemas.StudentCreate) -> dict:
    """Insert a new student and return the stored record."""
    data = payload.model_dump_db()
    with db_session() as connection:
        try:
            cursor = connection.execute(
                """
                INSERT INTO students (name, date_of_birth, email, phone, course)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    data["name"],
                    data["date_of_birth"],
                    data["email"],
                    data["phone"],
                    data["course"],
                ),
            )
        except sqlite3.IntegrityError as error:
            _handle_integrity_error(error)
        student = _row_to_dict(
            _fetch_one(connection, cursor.lastrowid)
        )
    return student


def list_students(name: Optional[str] = None) -> List[dict]:
    """Return all students, optionally filtered by a partial name match."""
    query = "SELECT " + ", ".join(_STUDENT_COLUMNS) + " FROM students"
    parameters: tuple = ()
    if name:
        query += " WHERE name LIKE ? COLLATE NOCASE"
        parameters = (f"%{name.strip()}%",)
    query += " ORDER BY id ASC"
    with db_session() as connection:
        rows = connection.execute(query, parameters).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_student(student_id: int) -> dict:
    """Return a single student or raise StudentNotFoundError."""
    with db_session() as connection:
        row = _fetch_one(connection, student_id)
    if row is None:
        raise StudentNotFoundError(f"student {student_id} does not exist")
    return _row_to_dict(row)


def update_student(student_id: int, payload: schemas.StudentUpdate) -> dict:
    """Apply a partial update to a student and return the updated record."""
    if not payload.has_fields():
        raise ValueError("no fields to update")

    with db_session() as connection:
        existing = _fetch_one(connection, student_id)
        if existing is None:
            raise StudentNotFoundError(f"student {student_id} does not exist")

        # Use only fields that were explicitly sent with non-null values.
        data = payload.model_dump(exclude_unset=True)
        data = {key: value for key, value in data.items() if value is not None}

        # Build the UPDATE statement dynamically using parameterized values.
        set_clauses: List[str] = []
        parameters: List = []
        for field_name, value in data.items():
            set_clauses.append(f"{field_name} = ?")
            parameters.append(_to_db_value(field_name, value))

        set_clauses.append("updated_at = datetime('now')")
        parameters.append(student_id)
        try:
            connection.execute(
                f"""
                UPDATE students
                SET {', '.join(set_clauses)}
                WHERE id = ?
                """,
                parameters,
            )
        except sqlite3.IntegrityError as error:
            _handle_integrity_error(error)

        updated = _fetch_one(connection, student_id)
    return _row_to_dict(updated)


def replace_student(student_id: int, payload: schemas.StudentCreate) -> dict:
    """Completely replace every editable field of a student (PUT semantics)."""
    fields = _STUDENT_COLUMNS[1:-2]  # name, date_of_birth, email, phone, course
    set_clauses = ", ".join(f"{field} = ?" for field in fields)
    data = payload.model_dump_db()
    values = tuple(data[field] for field in fields)

    with db_session() as connection:
        existing = _fetch_one(connection, student_id)
        if existing is None:
            raise StudentNotFoundError(f"student {student_id} does not exist")
        try:
            connection.execute(
                f"UPDATE students SET {set_clauses}, updated_at = datetime('now') "
                "WHERE id = ?",
                (*values, student_id),
            )
        except sqlite3.IntegrityError as error:
            _handle_integrity_error(error)
        updated = _fetch_one(connection, student_id)
    return _row_to_dict(updated)


def delete_student(student_id: int) -> dict:
    """Remove a student and return the deleted record, or raise 404-ish error."""
    with db_session() as connection:
        existing = _fetch_one(connection, student_id)
        if existing is None:
            raise StudentNotFoundError(f"student {student_id} does not exist")
        deleted = _row_to_dict(existing)
        connection.execute("DELETE FROM students WHERE id = ?", (student_id,))
    return deleted


def _fetch_one(connection: sqlite3.Connection, student_id: int) -> Optional[sqlite3.Row]:
    """Fetch a single student row by id using a parameterized query."""
    query = "SELECT " + ", ".join(_STUDENT_COLUMNS) + " FROM students WHERE id = ?"
    return connection.execute(query, (student_id,)).fetchone()


def _to_db_value(field_name: str, value: object) -> object:
    """Convert validated model values into values suitable for SQLite."""
    if field_name == "date_of_birth":
        return value.isoformat()
    return value