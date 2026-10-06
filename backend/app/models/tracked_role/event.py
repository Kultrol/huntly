from __future__ import annotations

import re
from datetime import date, time
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import UUID as SQL_UUID
from sqlalchemy import CheckConstraint, Date, ForeignKey, String, Text, Time, event
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.database import Base
from app.models.enums import EventStatus, EventType, enum_type
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.tracked_role.event_status_history import EventStatusHistory
    from app.models.tracked_role.tracked_role import TrackedRole


class TrackedRoleEvent(Base, TimestampMixin):
    __tablename__ = "tracked_role_events"

    __table_args__ = (
        CheckConstraint(
            "(event_type = 'custom' AND custom_type_name IS NOT NULL "
            "AND length(trim(custom_type_name)) > 0) "
            "OR (event_type <> 'custom' AND custom_type_name IS NULL)",
            name="ck_tracked_role_events_custom_type_name",
        ),
    )

    id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String, nullable=False)
    tracked_role_id: Mapped[UUID] = mapped_column(
        SQL_UUID, ForeignKey("tracked_roles.id", ondelete="CASCADE"), nullable=False
    )
    tracked_role: Mapped[TrackedRole] = relationship(back_populates="events")
    status_history: Mapped[list[EventStatusHistory]] = relationship(
        back_populates="tracked_role_event",
        cascade="all, delete",
        passive_deletes=True,
    )
    event_type: Mapped[EventType] = mapped_column(
        enum_type(EventType, "ck_tracked_role_events_event_type"),
        nullable=False,
        comment="The type of the event.",
    )
    custom_type_name: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        comment="The custom type name of the event.",
    )
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    event_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    status: Mapped[EventStatus] = mapped_column(
        enum_type(EventStatus, "ck_tracked_role_events_status"),
        nullable=False,
        comment="The status of the event.",
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str | None] = mapped_column(String, nullable=True)
    location: Mapped[str | None] = mapped_column(String, nullable=True)

    @validates("title")
    def validate_title(self, key: str, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Event title must contain non-whitespace characters.")
        return " ".join(value.split())

    @validates("event_type")
    def validate_event_type(self, key: str, value: EventType | str) -> EventType:
        return EventType(value)

    @validates("status")
    def validate_status(self, key: str, value: EventStatus | str) -> EventStatus:
        return EventStatus(value)

    @validates("custom_type_name")
    def validate_custom_type_name(self, key: str, value: str | None) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Custom event type name must not be blank.")
        normalized_name = re.sub(r"[\s_-]+", " ", value).strip().casefold()
        canonical_names = {member.value.replace("_", " ") for member in EventType}
        if normalized_name in canonical_names:
            raise ValueError(
                "Custom event type name must not reproduce a canonical type."
            )
        return " ".join(value.split())


@event.listens_for(TrackedRoleEvent, "before_insert")
@event.listens_for(TrackedRoleEvent, "before_update")
def validate_custom_type(mapper, connection, target: TrackedRoleEvent) -> None:
    # Check both fields together after assignment so updates are order-independent.
    if target.event_type == EventType.CUSTOM:
        if target.custom_type_name is None:
            raise ValueError("Custom events require a custom type name.")
        target.validate_custom_type_name("custom_type_name", target.custom_type_name)
    elif target.custom_type_name is not None:
        raise ValueError("Only custom events may have a custom type name.")
