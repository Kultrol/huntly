from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import UUID as SQL_UUID
from sqlalchemy import ForeignKey, String, Text, UniqueConstraint, event
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Mapped, Mapper, mapped_column, relationship, validates

from app.core.database import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.contact import Contact
    from app.models.tracked_role.tracked_role import TrackedRole
    from app.models.user import User


class Company(TimestampMixin, Base):
    """A company owned by one user, unique by normalized name within that user.

    Names collapse whitespace and use Unicode case folding for the duplicate key;
    punctuation and legal-name aliases remain distinct. Deleting a company clears
    its role and contact links without deleting those records. Callers enforce
    access to the owner's records.
    """

    __tablename__: str = "companies"

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

    __table_args__: tuple[UniqueConstraint, ...] = (
        UniqueConstraint("user_id", "normalized_name", name="uq_company_user_name"),
    )

    @validates("name")
    def validate_name(self, key: str, value: str) -> str:
        """Collapse whitespace and update the Unicode case-folded duplicate key.

        Blank and non-string names are rejected; punctuation and suffixes are retained.
        """
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Company name must contain non-whitespace characters")
        name: str = " ".join(value.split())
        self.normalized_name = name.casefold()
        return name


@event.listens_for(Company, "before_insert")
@event.listens_for(Company, "before_update")
def maintain_normalized_name(
    mapper: Mapper[Company], connection: Connection, company: Company
) -> None:
    """Rebuild the duplicate key before ORM writes, including manual key edits.

    Direct SQL writes bypass this hook.
    """
    # A stale or manually assigned key could bypass user-scoped deduplication.
    company.name = company.validate_name("name", company.name)
