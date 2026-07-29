from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin

# TYPE_CHECKING is True only for type checkers / IDEs. These imports are
# not executed at runtime, which avoids circular imports between models.
if TYPE_CHECKING:
    from app.models.contact import Contact
    from app.models.job_application import JobApplication


class Company(TimestampMixin, Base):
    """An employer you track: owns many contacts and many job applications."""

    __tablename__ = "companies"

    # --- identity ---
    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid4,
        comment="Primary key (UUID generated in the app via uuid4)",
    )

    # --- company profile ---
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        comment="Company display name (unique across the tracker)",
    )
    website: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        comment="Company website URL; unique when set",
    )
    linkedin_url: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        comment="Company LinkedIn page URL; unique when set",
    )
    location: Mapped[str | None] = mapped_column(
        String(255),
        comment="Headquarters or primary company location",
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        comment="Free-form notes about the company (culture, referrals, etc.)",
    )

    # --- relationships (ORM only; no extra DB columns) ---
    # One company → many applications. Matching side: JobApplication.company
    job_applications: Mapped[list[JobApplication]] = relationship(
        back_populates="company",
    )
    # One company → many people. Matching side: Contact.company
    contacts: Mapped[list[Contact]] = relationship(
        back_populates="company",
    )
