from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin

# Runtime-safe forward ref only — see company.py for why TYPE_CHECKING.
if TYPE_CHECKING:
    from app.models.company import Company


class Contact(TimestampMixin, Base):
    """A person at a company (recruiter, hiring manager, referral, etc.)."""

    __tablename__ = "contacts"

    # --- identity ---
    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid4,
        comment="Primary key (UUID generated in the app via uuid4)",
    )

    # --- ownership (many contacts → one company) ---
    company_id: Mapped[UUID] = mapped_column(
        # CASCADE: deleting a company also deletes its contacts.
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to companies.id; company this person works at / represents",
    )

    # --- contact details ---
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Contact full name",
    )
    phone_number: Mapped[str | None] = mapped_column(
        String(32),
        unique=True,
        comment="Phone number; unique when set",
    )
    role: Mapped[str | None] = mapped_column(
        String(255),
        comment="Job title or relationship (e.g. Recruiter, Eng Manager)",
    )
    email: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        comment="Email address; unique when set",
    )
    linkedin_url: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        comment="Personal LinkedIn profile URL; unique when set",
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        comment="Free-form notes (last conversation, intro path, etc.)",
    )

    # --- relationships ---
    # Many contacts → one company. Matching side: Company.contacts
    company: Mapped[Company] = relationship(back_populates="contacts")
