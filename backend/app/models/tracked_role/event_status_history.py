from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import UUID as SQL_UUID
from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.database import Base
from app.models.enums import EventStatus, enum_type

if TYPE_CHECKING:
    from app.models.tracked_role.event import TrackedRoleEvent


class EventStatusHistory(Base):
    __tablename__ = "event_status_histories"
    id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid4)
    event_id: Mapped[UUID] = mapped_column(
        SQL_UUID,
        ForeignKey("tracked_role_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    from_status: Mapped[EventStatus | None] = mapped_column(
        enum_type(EventStatus, "ck_event_status_histories_from_status"),
        nullable=True,
        comment="The previous status before the status transition occurred.",
    )
    to_status: Mapped[EventStatus] = mapped_column(
        enum_type(EventStatus, "ck_event_status_histories_to_status"),
        nullable=False,
        comment="The new status after the status transition occurred.",
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="The actual time the status change occurred - user led",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="The timestamp when the status history was created - system generated",
    )
    tracked_role_event: Mapped[TrackedRoleEvent] = relationship(
        back_populates="status_history"
    )

    @validates("from_status")
    def validate_from_status(
        self, key: str, value: EventStatus | str | None
    ) -> EventStatus | None:
        return None if value is None else EventStatus(value)

    @validates("to_status")
    def validate_to_status(self, key: str, value: EventStatus | str) -> EventStatus:
        return EventStatus(value)
