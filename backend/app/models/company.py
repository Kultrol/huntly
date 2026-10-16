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
    """A company record belonging to one user's private workspace.

    Attributes:
        name: Display name with repeated whitespace collapsed.
        normalized_name: Case-folded display name used for user-scoped uniqueness.
        tracked_roles: Opportunities whose company links are cleared on deletion.
        contacts: People whose company links are cleared on deletion.

    Notes:
        Normalization handles formatting differences, not legal-name aliases.
        Another user may independently store the same normalized company name.
        The foreign key identifies the owner; authorization belongs to callers.
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
        """Normalize the display name and synchronize its duplicate-check key.

        Args:
            key: SQLAlchemy attribute name triggering validation.
            value: Proposed company display name.

        Returns:
            The name with leading, trailing, and repeated whitespace removed.

        Raises:
            ValueError: If the value is not a string or contains only whitespace.

        Notes:
            Also updates ``normalized_name`` using Unicode case folding.
            Punctuation and company suffixes remain significant for uniqueness.
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
    """Restore the name-derived uniqueness key before an ORM write.

    Args:
        mapper: SQLAlchemy mapper supplied by the persistence event.
        connection: Connection for the pending write; unused by this hook.
        company: Company being inserted or updated.

    Returns:
        None. The company is normalized in place.

    Raises:
        ValueError: If the company's display name is invalid.

    Notes:
        Direct SQL writes bypass this ORM hook.
    """
    # A stale or manually assigned key could bypass user-scoped deduplication.
    company.name = company.validate_name("name", company.name)
