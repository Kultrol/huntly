from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import RelationshipType, enum_type
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.contact import Contact
    from app.models.tracked_role.tracked_role import TrackedRole


class TrackedRoleContact(TimestampMixin, Base):
    """A contact's relationship to one specific tracked opportunity."""

    __tablename__ = "tracked_role_contact_associations"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    relationship_type: Mapped[RelationshipType | None] = mapped_column(
        enum_type(RelationshipType, "tracked_role_contact_relationship_type"),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    tracked_role_id: Mapped[UUID] = mapped_column(
        ForeignKey("tracked_roles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    contact_id: Mapped[UUID] = mapped_column(
        ForeignKey("contacts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    tracked_role: Mapped[TrackedRole] = relationship(
        back_populates="contact_associations"
    )
    contact: Mapped[Contact] = relationship(back_populates="role_associations")

    __table_args__ = (
        UniqueConstraint(
            "tracked_role_id", "contact_id", name="unique_tracked_role_contact"
        ),
    )


# Retain the earlier Python import name while exposing the domain entity name.
TrackedRoleContactAssociation = TrackedRoleContact
