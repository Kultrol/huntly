"""Pydantic schemas for Interview create/read/update."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.models.enums import InterviewOutcome, InterviewType


class InterviewBase(BaseModel):
    scheduled_at: datetime
    interview_type: InterviewType
    location: str | None = Field(default=None, max_length=255)
    url_link: HttpUrl | None = None
    notes: str | None = None
    outcome: InterviewOutcome | None = None


class CreateInterview(InterviewBase):
    application_id: UUID


class ReadInterview(InterviewBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    application_id: UUID
    created_at: datetime
    updated_at: datetime


class UpdateInterview(BaseModel):
    scheduled_at: datetime | None = None
    interview_type: InterviewType | None = None
    location: str | None = Field(None, max_length=255)
    url_link: HttpUrl | None = None
    notes: str | None = None
    outcome: InterviewOutcome | None = None
