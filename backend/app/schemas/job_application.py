"""Pydantic schemas for JobApplication create/read/update."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.models.enums import JobType, Priority


class JobApplicationBase(BaseModel):
    company_id: UUID
    job_title: str = Field(..., min_length=1, max_length=255)
    job_description: str | None = None
    job_url: HttpUrl | None = None
    job_type: JobType
    location: str | None = Field(default=None, max_length=255)
    salary_min: Decimal | None = None
    salary_max: Decimal | None = None
    applied_at: datetime | None = None
    priority: Priority | None = None
    notes: str | None = None


class CreateJobApplication(JobApplicationBase):
    pass


class ReadJobApplication(JobApplicationBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class UpdateJobApplication(BaseModel):
    company_id: UUID | None = None
    job_title: str | None = Field(None, min_length=1, max_length=255)
    job_description: str | None = None
    job_url: HttpUrl | None = None
    job_type: JobType | None = None
    location: str | None = Field(None, max_length=255)
    salary_min: Decimal | None = None
    salary_max: Decimal | None = None
    applied_at: datetime | None = None
    priority: Priority | None = None
    notes: str | None = None
