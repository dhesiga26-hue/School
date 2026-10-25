"""Optional Ollama-backed natural-language question answering.

This module is OPTIONAL and completely independent of the CRUD core. Facts are
always retrieved from SQLite in backend code using the normal ``crud`` layer
(parameterized queries only). Ollama is only used to phrase a natural-language
answer, never to run SQL.

When Ollama or the configured model is unavailable, the endpoint returns a clear
message along with any facts that could be retrieved offline.
"""

from __future__ import annotations

import os
import re
from typing import List, Optional, Tuple

import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app import crud

router = APIRouter(prefix="/ai", tags=["ai (optional)"])

_OLLAMA_BASE_URL = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
_OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")
_OLLAMA_TIMEOUT = float(os.environ.get("OLLAMA_TIMEOUT", "15"))
_YEAR_PATTERN = re.compile(r"\b(19|20)\d{2}\b")


class AskRequest(BaseModel):
    """Payload for a natural-language question about the student data."""

    question: str = Field(..., min_length=1, max_length=500)


class AskResponse(BaseModel):
    """Answer plus provenance for transparency."""

    answer: str
    source: str = Field(..., description="ollama | builtin | unavailable")
    model_used: Optional[str] = None
    matched_students: int = 0


def _ollama_available() -> bool:
    """Returns True when an Ollama server is reachable on the configured host."""
    try:
        response = httpx.get(f"{_OLLAMA_BASE_URL}/api/tags", timeout=3)
        return response.status_code == 200
    except Exception:
        return False


def _ask_ollama(question: str, context: str) -> Optional[str]:
    """Ask the local model to phrase an answer grounded in ``context``.

    The model is explicitly told to rely only on the provided context. No SQL or
    data-access code is ever exposed to the model.
    """
    system_prompt = (
        "You answer questions about a student database. Use ONLY the facts in "
        "the provided context. If the context does not contain the answer, say "
        "you do not have enough data. Never invent student records."
    )
    payload = {
        "model": _OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Question: {question}\n\nContext:\n{context}",
            },
        ],
        "stream": False,
    }
    try:
        response = httpx.post(
            f"{_OLLAMA_BASE_URL}/api/chat", json=payload, timeout=_OLLAMA_TIMEOUT
        )
        if response.status_code != 200:
            return None
        message = response.json().get("message", {}).get("content", "")
        return message.strip() or None
    except Exception:
        return None


def _question_intent(question: str) -> dict:
    """Classify the question into one of the supported fact queries."""
    lowered = question.lower()
    year_match = _YEAR_PATTERN.search(question)

    if "how many" in lowered or lowered.strip().startswith("count"):
        return {"kind": "count"}

    if ("born after" in lowered or "born since" in lowered) and year_match:
        return {"kind": "born_after", "year": int(year_match.group())}

    if "born before" in lowered and year_match:
        return {"kind": "born_before", "year": int(year_match.group())}

    return {"kind": "generic"}


def _relevant_students(intent: dict) -> List[dict]:
    """Retrieve the records relevant to the question using crud only."""
    if intent["kind"] == "count":
        return crud.list_students()
    if intent["kind"] == "born_after":
        cutoff = f"{intent['year']}-12-31"
        return [
            s for s in crud.list_students() if s["date_of_birth"] > cutoff
        ]
    if intent["kind"] == "born_before":
        cutoff = f"{intent['year']}-01-01"
        return [s for s in crud.list_students() if s["date_of_birth"] < cutoff]
    return crud.list_students()[:50]


def _builtin_answer(intent: dict, students: List[dict]) -> Tuple[str, int]:
    """Produce a precise, grounded answer without any external service."""
    if intent["kind"] == "count":
        return f"There are {len(students)} student(s) in the database.", len(students)
    if intent["kind"] in ("born_after", "born_before"):
        if not students:
            filter_label = "after" if intent["kind"] == "born_after" else "before"
            return f"No students born {filter_label} {intent['year']}.", 0
        names = ", ".join(s["name"] for s in students)
        filter_label = "after" if intent["kind"] == "born_after" else "before"
        return (
            f"{len(students)} student(s) born {filter_label} {intent['year']}: {names}.",
            len(students),
        )
    names = ", ".join(s["name"] for s in students) if students else "none"
    return f"I found these student records: {names}.", len(students)


def _to_context(students: List[dict]) -> str:
    """Render retrieved records as a compact grounding context."""
    if not students:
        return "No student records match."
    lines = ["Student records | name | date_of_birth | email | course"]
    for student in students:
        lines.append(
            f"- {student['name']} | {student['date_of_birth']} | "
            f"{student['email']} | {student['course']}"
        )
    return "\n".join(lines)


@router.post("/ask", response_model=AskResponse, response_model_exclude_none=True)
def ask(payload: AskRequest) -> AskResponse:
    """Answer a natural-language question about stored students."""
    intent = _question_intent(payload.question)
    students = _relevant_students(intent)
    context = _to_context(students)

    model_reply: Optional[str] = None
    if _ollama_available():
        model_reply = _ask_ollama(payload.question, context)
        if model_reply:
            return AskResponse(
                answer=model_reply,
                source="ollama",
                model_used=_OLLAMA_MODEL,
                matched_students=len(students),
            )

    answer, matched = _builtin_answer(intent, students)
    source = "builtin"
    unavailable_message = ""
    if _ollama_available():
        unavailable_message = (
            f" ([{_OLLAMA_MODEL}] could not be used; a grounded built-in answer is "
            "shown instead)"
        )
    else:
        unavailable_message = " (Ollama is not running or unreachable; a grounded built-in answer is shown)"
    response_model = AskResponse(
        answer=answer + unavailable_message,
        source="unavailable" if not _ollama_available() else "builtin",
        model_used=_OLLAMA_MODEL if _ollama_available() else None,
        matched_students=matched,
    )
    return response_model