from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    """Shared audit columns mixed into every domain table.

    Inherit first (or anywhere before Base is fine with SQLAlchemy 2.0
    declarative) so models get created_at / updated_at for free.
    """

    # --- audit timestamps (timezone-aware) ---
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        # Postgres sets this on INSERT if the app does not pass a value.
        server_default=func.now(),
        nullable=False,
        comment="When this row was first created (DB server default, timezone-aware)",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        # server_default covers the first insert; onupdate covers later ORM writes.
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="When this row was last updated (server default + ORM onupdate)",
    )
