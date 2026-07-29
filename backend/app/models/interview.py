from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import InterviewOutcome, InterviewType
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.job_application import JobApplication


class Interview(TimestampMixin, Base):
    """One scheduled interview event belonging to a single job application."""

    __tablename__ = "interviews"

    # --- identity ---
    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid4,
        comment="Primary key (UUID generated in the app via uuid4)",
    )

    # --- ownership (many interviews → one application) ---
    application_id: Mapped[UUID] = mapped_column(
        # CASCADE: deleting the application removes its interviews in the DB.
        ForeignKey("job_applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to job_applications.id; application this interview belongs to",
    )

    # --- schedule & format ---
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Interview start time (timezone-aware)",
    )
    interview_type: Mapped[InterviewType] = mapped_column(
        Enum(
            InterviewType,
            name="interview_type",
            native_enum=False,
            length=32,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        comment="Interview format/focus (InterviewType enum value, e.g. video)",
    )

    # --- logistics (optional until known) ---
    location: Mapped[str | None] = mapped_column(
        String(255),
        comment="Physical location or office name for onsite interviews",
    )
    url_link: Mapped[str | None] = mapped_column(
        String(512),
        comment="Video call or portal URL for remote interviews",
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        comment="Prep notes, interviewer names, takeaways, etc.",
    )
    outcome: Mapped[InterviewOutcome | None] = mapped_column(
        Enum(
            InterviewOutcome,
            name="interview_outcome",
            native_enum=False,
            length=32,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        comment="Result of this interview only (InterviewOutcome enum value)",
    )

    # --- relationships ---
    # Many interviews → one application. Matching side: JobApplication.interviews
    job_application: Mapped[JobApplication] = relationship(
        back_populates="interviews",
    )
