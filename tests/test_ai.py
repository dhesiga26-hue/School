"""Offline tests for the optional AI question parser.

These tests never contact Ollama or the network; they only verify the intent
classifier that decides which records to retrieve.
"""

from __future__ import annotations

from app.ai import _builtin_answer, _question_intent, _relevant_students


def test_intent_count():
    assert _question_intent("How many students are there?")["kind"] == "count"
    assert _question_intent("count students")["kind"] == "count"


def test_intent_born_after():
    intent = _question_intent("List students born after 2005.")
    assert intent["kind"] == "born_after"
    assert intent["year"] == 2005


def test_intent_born_before():
    intent = _question_intent("students born before 2000")
    assert intent["kind"] == "born_before"
    assert intent["year"] == 2000


def test_intent_generic():
    assert _question_intent("Who is enrolled?")["kind"] == "generic"


def test_relevant_students_born_after(tmp_path, monkeypatch):
    from app import crud
    from app.database import init_db
    from app.crud import create_student
    from app.schemas import StudentCreate

    monkeypatch.setenv("STUDENTS_DB_PATH", str(tmp_path / "test_ai.db"))
    init_db()

    created = create_student(
        StudentCreate(
            name="Young Learner",
            date_of_birth="2007-03-01",
            email="young@example.com",
            phone="+1-555-0142",
            course="Math",
        )
    )
    try:
        intent = {"kind": "born_after", "year": 2005}
        students = _relevant_students(intent)
        assert any(s["id"] == created["id"] for s in students)
        answer, matched = _builtin_answer(intent, students)
        assert matched >= 1
        assert "Young Learner" in answer
    finally:
        crud.delete_student(created["id"])