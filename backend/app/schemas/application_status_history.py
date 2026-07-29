"""Pydantic schemas for ApplicationStatusHistory create/read/update."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ApplicationStatus


class ApplicationStatusHistoryBase(BaseModel):
    status: ApplicationStatus
    notes: str | None = None


class CreateApplicationStatusHistory(ApplicationStatusHistoryBase):
    application_id: UUID


class ReadApplicationStatusHistory(ApplicationStatusHistoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    application_id: UUID
    created_at: datetime
    updated_at: datetime


class UpdateApplicationStatusHistory(BaseModel):
    status: ApplicationStatus | None = None
    notes: str | None = Field(default=None)
