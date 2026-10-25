"""FastAPI application entry point.

Run with:  uvicorn main:app --reload
Swagger UI is available at http://127.0.0.1:8000/docs once the app is running.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import routes
from app.database import init_db

_STATIC_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables on startup; close nothing special on shutdown."""
    init_db()
    yield


app = FastAPI(
    title="Student Management API",
    description=(
        "A Student Database CRUD backend built with FastAPI, SQLite and "
        "Pydantic for the EWB Edu Tech internship assignment."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(routes.router)

# Optional Ollama extension. If it cannot be imported the core API stays intact.
try:
    from app.ai import router as ai_router

    app.include_router(ai_router)
except Exception:  # pragma: no cover - depends on optional dependencies
    pass


@app.get("/", tags=["system"])
def root() -> dict:
    """Return a simple status message for the API."""
    return {
        "status": "ok",
        "message": "Student Management API is running. Visit /docs for interactive documentation.",
    }


@app.get("/ui", include_in_schema=False, tags=["ui"])
def ui_page() -> FileResponse:
    """Serve the single-page dashboard."""
    return FileResponse(_STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")