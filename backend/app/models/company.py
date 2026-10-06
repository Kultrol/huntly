from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import UUID as SQL_UUID
from sqlalchemy import ForeignKey, String, Text, UniqueConstraint, event
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.database import Base
from app.models.mixins import TimestampMixin

# Type-only imports avoid circular imports between models.
if TYPE_CHECKING:
    from app.models.contact import Contact
    from app.models.tracked_role.tracked_role import TrackedRole
    from app.models.user import User


class Company(TimestampMixin, Base):
    __tablename__ = "companies"

    id: Mapped[UUID] = mapped_column(
        SQL_UUID,
        primary_key=True,
        default=uuid4,
        comment="Primary key (UUID generated in the app via uuid4)",
    )

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Company display name",
    )
    normalized_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="System-generated company name; unique within its user's workspace",
    )
    website: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Company website URL",
    )
    linkedin_url: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Company LinkedIn page URL",
    )
    location: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Headquarters or primary company location",
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Free-form notes about the company (culture, referrals, etc.)",
    )

    tracked_roles: Mapped[list[TrackedRole]] = relationship(
        back_populates="company", passive_deletes=True
    )

    contacts: Mapped[list[Contact]] = relationship(
        back_populates="company", passive_deletes=True
    )

    user: Mapped[User] = relationship(back_populates="companies")

    __table_args__ = (
        UniqueConstraint("user_id", "normalized_name", name="uq_company_user_name"),
    )

    @validates("name")
    def validate_name(self, key: str, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Company name must contain non-whitespace characters")
        name = " ".join(value.split())
        self.normalized_name = name.casefold()
        return name


@event.listens_for(Company, "before_insert")
@event.listens_for(Company, "before_update")
def maintain_normalized_name(mapper, connection, company: Company) -> None:
    # Recompute normalized_name before saving, even if it was assigned directly.
    company.name = company.validate_name("name", company.name)
