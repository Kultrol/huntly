from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Enum, ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import ApplicationStatus
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.job_application import JobApplication


class ApplicationStatusHistory(TimestampMixin, Base):
    """One point-in-time status event for an application (append-mostly audit log).

    Current status for an application is typically the latest row by created_at
    """

    __tablename__ = "application_status_history"

    # --- identity ---
    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid4,
        comment="Primary key (UUID generated in the app via uuid4)",
    )

    # --- ownership (many history rows → one application) ---
    application_id: Mapped[UUID] = mapped_column(
        # CASCADE: deleting the application removes its status history.
        ForeignKey("job_applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to job_applications.id; application this status event belongs to",
    )

    # --- event payload ---
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(
            ApplicationStatus,
            name="application_status",
            native_enum=False,
            length=32,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        comment="Pipeline status at this history event (ApplicationStatus enum value)",
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        comment="Optional context for this status change (rejection reason, etc.)",
    )

    # --- relationships ---
    # Many history rows → one application. Matching: JobApplication.status_history
    job_application: Mapped[JobApplication] = relationship(
        back_populates="status_history",
    )
