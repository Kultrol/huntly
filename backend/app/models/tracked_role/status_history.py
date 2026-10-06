from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import UUID as SQL_UUID
from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.core.database import Base
from app.models.enums import TrackedRoleStatus, enum_type

if TYPE_CHECKING:
    from app.models.tracked_role.tracked_role import TrackedRole


class StatusHistory(Base):
    __tablename__ = "status_history"

    id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid4)
    tracked_role_id: Mapped[UUID] = mapped_column(
        SQL_UUID, ForeignKey("tracked_roles.id", ondelete="CASCADE"), nullable=False
    )
    from_status: Mapped[TrackedRoleStatus | None] = mapped_column(
        enum_type(TrackedRoleStatus, "ck_status_history_from_status"), nullable=True
    )
    to_status: Mapped[TrackedRoleStatus] = mapped_column(
        enum_type(TrackedRoleStatus, "ck_status_history_to_status"), nullable=False
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="When this row was first created (DB server default, timezone-aware)",
    )
    tracked_role: Mapped[TrackedRole] = relationship(back_populates="status_history")

    @validates("from_status")
    def validate_from_status(
        self, key: str, value: TrackedRoleStatus | str | None
    ) -> TrackedRoleStatus | None:
        return None if value is None else TrackedRoleStatus(value)

    @validates("to_status")
    def validate_to_status(
        self, key: str, value: TrackedRoleStatus | str
    ) -> TrackedRoleStatus:
        return TrackedRoleStatus(value)
