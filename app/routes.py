"""HTTP API routes for student CRUD operations."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status

from app import crud, schemas

router = APIRouter(prefix="/students", tags=["students"])

# Error messages exposed to clients are safe, generic and never include raw
# database exceptions or internal stack information.
_MESSAGES = {
    "email": "a student with this email already exists",
}


def _email_conflict() -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_MESSAGES["email"])


def _not_found(student_id: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"student with id {student_id} was not found",
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=schemas.StudentOut)
def create_student(payload: schemas.StudentCreate) -> schemas.StudentOut:
    """Create a new student record."""
    try:
        return schemas.StudentOut(**crud.create_student(payload))
    except crud.DuplicateEmailError:
        raise _email_conflict()


@router.get("", response_model=List[schemas.StudentOut])
def list_students(
    name: Optional[str] = Query(default=None, description="Filter by student name"),
) -> List[schemas.StudentOut]:
    """Return all students, optionally filtered by name."""
    records = crud.list_students(name=name)
    return [schemas.StudentOut(**record) for record in records]


@router.get("/{student_id}", response_model=schemas.StudentOut)
def get_student(student_id: int) -> schemas.StudentOut:
    """Return a single student by id."""
    try:
        return schemas.StudentOut(**crud.get_student(student_id))
    except crud.StudentNotFoundError:
        raise _not_found(student_id)


@router.put("/{student_id}", response_model=schemas.StudentOut)
def replace_student(
    student_id: int, payload: schemas.StudentCreate
) -> schemas.StudentOut:
    """Fully replace a student's editable fields (complete update)."""
    try:
        return schemas.StudentOut(**crud.replace_student(student_id, payload))
    except crud.StudentNotFoundError:
        raise _not_found(student_id)
    except crud.DuplicateEmailError:
        raise _email_conflict()


@router.patch("/{student_id}", response_model=schemas.StudentOut)
def partial_update_student(
    student_id: int, payload: schemas.StudentUpdate
) -> schemas.StudentOut:
    """Partially update an existing student."""
    try:
        return schemas.StudentOut(**crud.update_student(student_id, payload))
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error
    except crud.StudentNotFoundError:
        raise _not_found(student_id)
    except crud.DuplicateEmailError:
        raise _email_conflict()


@router.delete("/{student_id}", response_model=schemas.StudentDeleteResponse)
def delete_student(student_id: int) -> schemas.StudentDeleteResponse:
    """Delete a student record."""
    try:
        crud.delete_student(student_id)
    except crud.StudentNotFoundError:
        raise _not_found(student_id)
    return schemas.StudentDeleteResponse(
        message=f"student with id {student_id} was deleted", deleted_id=student_id
    )