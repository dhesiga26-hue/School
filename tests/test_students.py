"""Integration tests for the Student CRUD API.

All tests run against an isolated temporary SQLite database prepared by the
``client`` fixture. No external services are required.
"""

from __future__ import annotations

import sqlite3

from fastapi.testclient import TestClient

VALID_STUDENT = {
    "name": "Alice Wonder",
    "date_of_birth": "2006-04-12",
    "email": "alice.wonder@example.com",
    "phone": "+1-555-0101",
    "course": "Computer Science",
}


def _create_student(client: TestClient, overrides: dict | None = None) -> dict:
    payload = dict(VALID_STUDENT)
    if overrides:
        payload.update(overrides)
    response = client.post("/students", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_student_successfully(client: TestClient):
    response = client.post("/students", json=VALID_STUDENT)

    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["id"], int)
    assert body["name"] == VALID_STUDENT["name"]
    assert body["email"] == VALID_STUDENT["email"]
    assert body["course"] == VALID_STUDENT["course"]
    assert "created_at" in body and "updated_at" in body


def test_reject_invalid_student_data(client: TestClient):
    response = client.post("/students", json={"name": "", "email": "not-an-email"})

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert any(error.get("loc") and "email" in error["loc"] for error in detail)


def test_reject_duplicate_email(client: TestClient):
    _create_student(client)

    response = client.post(
        "/students",
        json={**VALID_STUDENT, "name": "Alice Another", "phone": "+1-555-0199"},
    )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"].lower()


def test_get_all_students(client: TestClient):
    _create_student(client, {"email": "one@example.com"})
    _create_student(client, {"email": "two@example.com"})

    response = client.get("/students")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_all_students_filter_by_name(client: TestClient):
    _create_student(client, {"email": "bob@example.com", "name": "Bob Builder"})
    _create_student(client, {"email": "anna@example.com", "name": "Anna Builder"})

    response = client.get("/students", params={"name": "anna"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["name"] == "Anna Builder"


def test_get_existing_student(client: TestClient):
    created = _create_student(client)

    response = client.get(f"/students/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_nonexistent_student_returns_404(client: TestClient):
    response = client.get("/students/99999")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_update_student_successfully(client: TestClient):
    created = _create_student(client)
    new_data = {
        "name": "Alice Wonder Jr.",
        "date_of_birth": "2007-01-20",
        "email": "alice.jr@example.com",
        "phone": "+1-555-0182",
        "course": "Software Engineering",
    }

    response = client.put(f"/students/{created['id']}", json=new_data)

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == new_data["name"]
    assert body["email"] == new_data["email"]
    assert body["course"] == new_data["course"]


def test_partial_update_student_successfully(client: TestClient):
    created = _create_student(client)

    response = client.patch(f"/students/{created['id']}", json={"course": "Data Science"})

    assert response.status_code == 200
    body = response.json()
    assert body["course"] == "Data Science"
    assert body["name"] == VALID_STUDENT["name"]
    assert body["email"] == VALID_STUDENT["email"]


def test_reject_update_with_invalid_data(client: TestClient):
    created = _create_student(client)

    response = client.patch(f"/students/{created['id']}", json={"email": "bad-email"})

    assert response.status_code == 422


def test_reject_update_to_duplicate_email(client: TestClient):
    _create_student(client, {"email": "keep@example.com"})
    created = _create_student(client, {"email": "change@example.com"})

    response = client.put(
        f"/students/{created['id']}",
        json={**VALID_STUDENT, "email": "keep@example.com"},
    )

    assert response.status_code == 409


def test_update_nonexistent_student_returns_404(client: TestClient):
    response = client.put("/students/99999", json=VALID_STUDENT)

    assert response.status_code == 404


def test_delete_student_successfully(client: TestClient):
    created = _create_student(client)

    response = client.delete(f"/students/{created['id']}")

    assert response.status_code == 200
    assert response.json()["deleted_id"] == created["id"]
    assert client.get(f"/students/{created['id']}").status_code == 404


def test_delete_nonexistent_student_returns_404(client: TestClient):
    response = client.delete("/students/99999")

    assert response.status_code == 404


def test_persistence_across_app_restart(client: TestClient, tmp_path, monkeypatch):
    """Records survive when the application is restarted with the same DB file."""
    db_file = tmp_path / "test_students.db"

    created = _create_student(client)

    # Simulate a restart: re-initialise against the same file and serve a new app.
    monkeypatch.setenv("STUDENTS_DB_PATH", str(db_file))
    from app.database import init_db

    init_db()

    with sqlite3.connect(str(db_file)) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute("SELECT * FROM students WHERE id = ?", (created["id"],)).fetchone()
    assert row is not None
    assert row["email"] == created["email"]

    # The restarted app still returns the student through the API.
    from app.main import app as restarted_app

    with TestClient(restarted_app) as restarted_client:
        response = restarted_client.get(f"/students/{created['id']}")
    assert response.status_code == 200
    assert response.json()["name"] == created["name"]


def test_root_endpoint_returns_status(client: TestClient):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_docs_endpoint_available(client: TestClient):
    response = client.get("/docs")

    assert response.status_code == 200
    assert "swagger" in response.text.lower()


def test_ui_dashboard_available(client: TestClient):
    response = client.get("/ui")

    assert response.status_code == 200
    assert "Student Management Dashboard" in response.text

    styles = client.get("/static/styles.css")
    assert styles.status_code == 200

    script = client.get("/static/app.js")
    assert script.status_code == 200