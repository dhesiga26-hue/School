# Student Management API

A backend **Student Database CRUD Application** built for the **EWB Edu Tech Python Backend Development Internship Assignment**.

The application manages student records using Create, Read, Update and Delete operations over a REST API, with persistent storage in SQLite and input validation powered by Pydantic.

## Objective

Provide a clean, tested, submission-ready backend that lets users:

- Create new student records.
- Read all students (with optional name filtering) or a single student.
- Update students completely (`PUT`) or partially (`PATCH`).
- Delete students.
- Validate all incoming data and return meaningful errors.
- Persist data across application restarts.

## Features

- `POST /students` – create a student (unique ID auto-generated, returns `201`).
- `GET /students` – list all students, optional `?name=` filter.
- `GET /students/{student_id}` – fetch one student (`404` if missing).
- `PUT /students/{student_id}` – complete update.
- `PATCH /students/{student_id}` – partial update.
- `DELETE /students/{student_id}` – delete a student.
- Validation of name, email, date of birth, phone and course fields.
- Duplicate email detection (`409 Conflict`).
- SQLite persistence with parameterized queries (SQL-injection safe).
- Automatic Swagger documentation at `/docs`.
- A styled single-page dashboard at `/ui` for managing students in the browser.
- Automated test suite running against an isolated temporary database.
- Optional Ollama natural-language question answering (`/ai/ask`) — fully independent of the CRUD core.

## Technologies Used

- Python 3.10+
- FastAPI
- Uvicorn
- SQLite (stdlib `sqlite3`)
- Pydantic v2 (with `email-validator`)
- Pytest + FastAPI `TestClient`

## Project Folder Structure

```
BWE/
├── app/
│   ├── __init__.py        # Package marker
│   ├── database.py        # SQLite connection + table initialisation
│   ├── schemas.py         # Pydantic validation/response models
│   ├── crud.py            # Data access layer (all SQL lives here)
│   ├── routes.py          # API endpoints
│   ├── ai.py              # Optional Ollama question-answering endpoint
│   ├── static/            # Single-page dashboard (HTML, CSS, JS)
│   └── main.py            # FastAPI app factory + root route
├── tests/
│   ├── conftest.py        # Fixtures – isolated temp database per test
│   └── test_students.py   # CRUD, validation and persistence tests
├── main.py                # Uvicorn entry point
├── requirements.txt
├── README.md
└── .gitignore
```

## Prerequisites

- **Python 3.10 or newer** installed on your machine.
- Check your version:

  ```bash
  python --version
  ```

## Virtual Environment Setup

Create and activate a virtual environment:

**Windows (PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## Install Dependencies

```bash
pip install -r requirements.txt
```

This installs FastAPI, Uvicorn, Pydantic, `email-validator`, Pytest and HTTPX.

## Run the Application

From the project root, with the virtual environment activated:

```bash
uvicorn main:app --reload
```

Or run the entry point directly:

```bash
python main.py
```

The API will be available at:

- **Dashboard (UI):** http://127.0.0.1:8000/ui
- **API root:** http://127.0.0.1:8000/
- **Swagger UI (docs):** http://127.0.0.1:8000/docs
- **ReDoc:** http://127.0.0.1:8000/redoc

The SQLite database file (`students.db`) is created automatically on first startup. Data persists across restarts.

## Example API Requests

Create a student:

```bash
curl -X POST http://127.0.0.1:8000/students \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"Alice Wonder\", \"date_of_birth\": \"2006-04-12\", \"email\": \"alice.wonder@example.com\", \"phone\": \"+1-555-0101\", \"course\": \"Computer Science\"}"
```

List all students:

```bash
curl http://127.0.0.1:8000/students
```

Filter by name:

```bash
curl "http://127.0.0.1:8000/students?name=alice"
```

Get one student:

```bash
curl http://127.0.0.1:8000/students/1
```

Update completely (PUT – all fields required):

```bash
curl -X PUT http://127.0.0.1:8000/students/1 \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"Alice Wonder Jr.\", \"date_of_birth\": \"2007-01-20\", \"email\": \"alice.jr@example.com\", \"phone\": \"+1-555-0182\", \"course\": \"Software Engineering\"}"
```

Update partially (PATCH – only the fields you send):

```bash
curl -X PATCH http://127.0.0.1:8000/students/1 \
  -H "Content-Type: application/json" \
  -d "{\"course\": \"Data Science\"}"
```

Delete a student:

```bash
curl -X DELETE http://127.0.0.1:8000/students/1
```

## Optional: Ollama AI Extension

An optional natural-language endpoint at `POST /ai/ask` lets you ask questions
about the stored students, e.g.:

```json
{ "question": "How many students are there?" }
```

or

```json
{ "question": "List students born after 2005." }
```

How it works:

- Relevant records are **retrieved from SQLite in backend code** (the normal
  parameterized `crud` layer) — the model is **never** allowed to run SQL.
- If Ollama is running locally (default `http://localhost:11434`, model
  `llama3.2`, both configurable via `OLLAMA_HOST` / `OLLAMA_MODEL`), the model
  phrases the answer using the retrieved facts as grounding context.
- If Ollama or the model is unavailable, the endpoint returns a clear message
  plus a precise, grounded built-in answer — the mandatory CRUD API is never
  affected by this extension.

The AI router is registered only if the module imports successfully; the core
CRUD endpoints have no dependency on Ollama.

## Running the Tests

The test suite uses an isolated temporary SQLite database, so it never touches real application data.

```bash
pytest -v
```

Or, if `pytest` is not on your PATH:

```bash
python -m pytest -v
```

Expected result: all tests pass (CRUD operations, validation, duplicate emails, 404 handling and persistence).

## GitHub Submission Instructions

1. Create a new repository on GitHub.
2. From the project folder:

   ```bash
   git init
   git add .
   git commit -m "Student Management CRUD API"
   git branch -M main
   git remote add origin https://github.com/<your-username>/<repo-name>.git
   git push -u origin main
   ```

3. Add the assignment title and submission notes to the repository description.

### Security notes for submission

- `.gitignore` excludes virtual environments, caches and local database files (`.db`), so **no personal/real student data is committed**.
- Use **dummy data** (e.g. `alice@example.com`) in demos or README examples.
- Never commit API keys, passwords or credentials.
- The repository is held locally until you explicitly decide to push it.

## Configuration

The database file location can be overridden with the `STUDENTS_DB_PATH` environment variable, e.g. for testing:

```bash
$env:STUDENTS_DB_PATH = "C:\\temp\\my.db"   # Windows PowerShell
export STUDENTS_DB_PATH=/tmp/my.db          # macOS / Linux
```