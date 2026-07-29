from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import JobType, Priority
from app.models.mixins import TimestampMixin

# Avoid circular imports: only needed for static typing / IDE navigation.
if TYPE_CHECKING:
    from app.models.application_status_history import ApplicationStatusHistory
    from app.models.company import Company
    from app.models.interview import Interview


class JobApplication(TimestampMixin, Base):
    """One application to one role at one company (plus interviews & status log)."""

    __tablename__ = "job_applications"
    # Business rule: same title can exist at different companies, but not twice
    # under the same company (e.g. two "SWE" rows at Acme).
    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "job_title",
            name="uq_job_applications_company_title",
        ),
    )

    # --- identity ---
    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid4,
        comment="Primary key (UUID generated in the app via uuid4)",
    )

    # --- ownership (many applications → one company) ---
    company_id: Mapped[UUID] = mapped_column(
        # RESTRICT: cannot delete a company while applications still point at it.
        ForeignKey("companies.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="FK to companies.id; exactly one company owns this application",
    )

    # --- posting / role details ---
    job_title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Role title (unique per company via composite constraint)",
    )
    job_description: Mapped[str | None] = mapped_column(
        Text,
        comment="Full or pasted job description text",
    )
    job_url: Mapped[str | None] = mapped_column(
        String(512),
        unique=True,
        comment="Canonical job posting URL; unique when set",
    )
    job_type: Mapped[JobType] = mapped_column(
        # native_enum=False → VARCHAR; values_callable stores "full_time" etc.
        Enum(
            JobType,
            name="job_type",
            native_enum=False,
            length=32,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        comment="Employment type (JobType enum value, e.g. full_time)",
    )
    location: Mapped[str | None] = mapped_column(
        String(255),
        comment="Job location or remote label (not unique — many jobs share cities)",
    )
    salary_min: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        comment="Lower bound of expected or listed pay (Numeric 12,2)",
    )
    salary_max: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        comment="Upper bound of expected or listed pay (Numeric 12,2)",
    )
    applied_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        comment="When you submitted the application; null if still a wishlist item",
    )
    priority: Mapped[Priority | None] = mapped_column(
        Enum(
            Priority,
            name="priority",
            native_enum=False,
            length=16,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        comment="Personal priority in the tracker (Priority enum value)",
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        comment="Free-form notes for this application",
    )

    # --- relationships ---
    # Many applications → one company. Matching side: Company.job_applications
    company: Mapped[Company] = relationship(back_populates="job_applications")

    # One application → many interviews. delete-orphan: removing from this
    # list (or deleting the app via ORM) also deletes interview rows.
    interviews: Mapped[list[Interview]] = relationship(
        back_populates="job_application",
        cascade="all, delete-orphan",
    )
    # One application → many status events (audit trail over time).
    status_history: Mapped[list[ApplicationStatusHistory]] = relationship(
        back_populates="job_application",
        cascade="all, delete-orphan",
    )
