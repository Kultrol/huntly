from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DECIMAL, CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy import UUID as SQL_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.database import Base
from app.models.enums import Priority, TrackedRoleStatus, TrackedRoleType, enum_type
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.contact import Contact
    from app.models.tracked_role.event import TrackedRoleEvent
    from app.models.tracked_role.role_contact_association import TrackedRoleContact
    from app.models.tracked_role.status_history import StatusHistory
    from app.models.user import User


class TrackedRole(TimestampMixin, Base):
    __tablename__ = "tracked_roles"

    __table_args__ = (
        CheckConstraint("length(trim(title)) > 0", name="ck_tracked_roles_title"),
        CheckConstraint("salary_min >= 0", name="tracked_roles_salary_min_check"),
        CheckConstraint("salary_max >= 0", name="tracked_roles_salary_max_check"),
        CheckConstraint(
            "salary_min IS NULL OR salary_max IS NULL OR salary_min <= salary_max",
            name="ck_tracked_roles_salary_range",
        ),
    )

    id: Mapped[UUID] = mapped_column(SQL_UUID, default=uuid4, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[UUID] = mapped_column(
        SQL_UUID, ForeignKey("users.id"), nullable=False
    )
    company_id: Mapped[UUID | None] = mapped_column(
        SQL_UUID,
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[TrackedRoleStatus] = mapped_column(
        enum_type(TrackedRoleStatus, "ck_tracked_roles_status"),
        nullable=False,
        comment="The status of the role the user wants to track.",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        comment="A description of the role the user wants to track.",
        nullable=True,
    )
    role_type: Mapped[TrackedRoleType | None] = mapped_column(
        enum_type(TrackedRoleType, "ck_tracked_roles_role_type"),
        nullable=True,
        comment="Optional employment arrangement retained alongside the V1 fields",
    )
    location: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        comment="The location of the role, so the office, building, or place in which the role is offered from.",
    )
    source: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        comment="The source of the role(i.e. a company or job posting).",
    )
    listing_url: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        comment="The URL of the listing for the role.",
    )
    priority: Mapped[Priority | None] = mapped_column(
        enum_type(Priority, "ck_tracked_roles_priority"),
        nullable=True,
        comment="The priority of the role the user wants to track.",
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Any notes or comments about the role.",
    )
    salary_min: Mapped[Decimal | None] = mapped_column(
        DECIMAL,
        nullable=True,
        comment="The minimum salary for the role.",
    )
    salary_max: Mapped[Decimal | None] = mapped_column(
        DECIMAL,
        nullable=True,
        comment="The maximum salary for the role.",
    )
    salary_currency: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        comment="Salary currency when supplied; NULL when unknown",
    )
    applied_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        comment="The date and time the role was applied for.",
        nullable=True,
    )

    # --- Relationships ---
    user: Mapped[User] = relationship(back_populates="tracked_roles")
    company: Mapped[Company | None] = relationship(back_populates="tracked_roles")
    status_history: Mapped[list[StatusHistory]] = relationship(
        back_populates="tracked_role",
        cascade="all, delete",
        passive_deletes=True,
    )
    events: Mapped[list[TrackedRoleEvent]] = relationship(
        back_populates="tracked_role",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    contacts: Mapped[list[Contact]] = relationship(
        secondary="tracked_role_contact_associations",
        back_populates="tracked_roles",
        viewonly=True,
    )
    contact_associations: Mapped[list[TrackedRoleContact]] = relationship(
        back_populates="tracked_role",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    @validates("title")
    def validate_title(self, key: str, value: str) -> str:
        if not isinstance(value, str):
            raise TypeError("A tracked role requires a string title")
        title = " ".join(value.split())
        if not title:
            raise ValueError("A tracked role title cannot be blank")
        return title

    @validates("status", "priority", "role_type")
    def validate_enum(self, key: str, value: str | StrEnum | None):
        enum_class = {
            "status": TrackedRoleStatus,
            "priority": Priority,
            "role_type": TrackedRoleType,
        }[key]
        if value is None and key != "status":
            return None
        return enum_class(value)
