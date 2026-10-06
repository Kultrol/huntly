from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.database import Base
from app.models.mixins import TimestampMixin
from app.models.tracked_role.role_contact_association import TrackedRoleContact

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.tracked_role.tracked_role import TrackedRole
    from app.models.user import User


class Contact(TimestampMixin, Base):
    """A user-owned person who may be associated with a company or tracked role."""

    __tablename__ = "contacts"

    # --- identity ---
    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid4,
        comment="Primary key (UUID generated in the app via uuid4)",
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        comment="FK to users.id",
    )

    company_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
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
        nullable=True,
        comment="Phone number",
    )
    role: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Professional title (e.g. Senior Technical Recruiter)",
    )
    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Email address",
    )
    linkedin_url: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Personal LinkedIn profile URL",
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Free-form notes (last conversation, intro path, etc.)",
    )

    # --- relationships ---
    # Many contacts → one company. Matching side: Company.contacts
    company: Mapped[Company | None] = relationship(back_populates="contacts")
    role_associations: Mapped[list[TrackedRoleContact]] = relationship(
        back_populates="contact",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    tracked_roles: Mapped[list[TrackedRole]] = relationship(
        secondary=TrackedRoleContact.__table__,
        back_populates="contacts",
        viewonly=True,
    )
    user: Mapped[User] = relationship(back_populates="contacts")

    @validates("name")
    def validate_name(self, key: str, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Contact name must contain non-whitespace characters")
        return " ".join(value.split())
