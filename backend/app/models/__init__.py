"""ORM models package for Huntly."""

# Re-export models + enums so callers can `from app.models import Company`.
# Importing this package also registers all tables on Base.metadata (needed
# by Alembic autogenerate).
from app.models.application_status_history import ApplicationStatusHistory
from app.models.company import Company
from app.models.contact import Contact
from app.models.enums import (
    ApplicationStatus,
    InterviewOutcome,
    InterviewType,
    JobType,
    Priority,
)
from app.models.interview import Interview
from app.models.job_application import JobApplication

__all__ = [
    "ApplicationStatus",
    "ApplicationStatusHistory",
    "Company",
    "Contact",
    "Interview",
    "InterviewOutcome",
    "InterviewType",
    "JobApplication",
    "JobType",
    "Priority",
]
