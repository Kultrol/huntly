"""Pydantic schemas for Company create/read/update."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class CompanyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    website: HttpUrl | None = None
    linkedin_url: HttpUrl | None = None
    location: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None)


class CreateCompany(CompanyBase):
    pass


class ReadCompany(CompanyBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class UpdateCompany(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    website: HttpUrl | None = None
    linkedin_url: HttpUrl | None = None
    location: str | None = Field(None, max_length=255)
    notes: str | None = None
