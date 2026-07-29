"""Pydantic schemas for Contact create/read/update."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl


class ContactBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    role: str | None = Field(default=None, max_length=255)
    phone_number: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None
    linkedin_url: HttpUrl | None = None
    notes: str | None = None


class CreateContact(ContactBase):
    company_id: UUID


class ReadContact(ContactBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    created_at: datetime
    updated_at: datetime


class UpdateContact(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    role: str | None = Field(None, max_length=255)
    phone_number: str | None = Field(None, max_length=32)
    email: EmailStr | None = None
    linkedin_url: HttpUrl | None = None
    notes: str | None = None
