"""Pydantic schemas used for request validation and response serialization."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

_PHONE_PATTERN = re.compile(r"^\+?[0-9][0-9\s\-()]{6,19}$")
_MIN_PHONE_DIGITS = 7


def _validate_not_blank(value: str, field_name: str) -> str:
    """Reject empty or whitespace-only text fields."""
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field_name} must not be empty")
    return stripped


def _validate_phone(value: str) -> str:
    """Reject phone numbers that do not look like real phone numbers."""
    cleaned = "".join(char for char in value if char.isdigit())
    if len(cleaned) < _MIN_PHONE_DIGITS:
        raise ValueError("must contain at least 7 digits")
    if not _PHONE_PATTERN.fullmatch(value):
        raise ValueError("invalid phone number format")
    return value.strip()


class StudentBase(BaseModel):
    """Fields shared by create and complete-update payloads."""

    name: str = Field(..., min_length=1, max_length=120)
    date_of_birth: date
    email: EmailStr
    phone: str = Field(..., min_length=7, max_length=20)
    course: str = Field(..., min_length=1, max_length=120)

    @field_validator("name", "course")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        return _validate_not_blank(value, cls.__name__)

    @field_validator("phone")
    @classmethod
    def _phone(cls, value: str) -> str:
        return _validate_phone(value)

    def model_dump_db(self) -> dict:
        """Return a plain dict of fields minus the identifier columns."""
        data = super().model_dump()
        data["date_of_birth"] = data["date_of_birth"].isoformat()
        return data


class StudentCreate(StudentBase):
    """Payload for creating a student (POST /students)."""


class StudentUpdate(BaseModel):
    """Payload for partially updating a student (PATCH).

    Every field is optional but at least one must be provided.
    """

    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    date_of_birth: Optional[date] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, min_length=7, max_length=20)
    course: Optional[str] = Field(default=None, min_length=1, max_length=120)

    @field_validator("name", "course")
    @classmethod
    def _not_blank(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return _validate_not_blank(value, cls.__name__)

    @field_validator("phone")
    @classmethod
    def _phone(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return _validate_phone(value)

    def has_fields(self) -> bool:
        """Return True when at least one updatable field was sent."""
        return any(
            field_name is not None
            for field_name in (
                self.name,
                self.date_of_birth,
                self.email,
                self.phone,
                self.course,
            )
        )


class StudentOut(BaseModel):
    """Response representation of a stored student record."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    date_of_birth: date
    email: EmailStr
    phone: str
    course: str
    created_at: datetime
    updated_at: datetime


class StudentDeleteResponse(BaseModel):
    """Success message returned when a student is deleted."""

    message: str
    deleted_id: int