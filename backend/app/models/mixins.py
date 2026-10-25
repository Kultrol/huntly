from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    """Storage timestamps, separate from when a job-search activity occurred.

    The database supplies initial values. SQLAlchemy updates ``updated_at`` on
    writes, but raw SQL does not refresh it automatically.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="When this row was first created (DB server default, timezone-aware)",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="When this row was last updated (server default + ORM onupdate)",
    )
