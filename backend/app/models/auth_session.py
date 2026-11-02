from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import UUID as SQL_UUID
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class AuthSession(Base):
    """A revocable login whose random cookie token stays out of the database.

    Session and CSRF tokens have enough entropy for SHA-256 digests; passwords
    use separate salted password hashing on User. Deleting the owner also deletes
    these sessions through the foreign key.
    """

    __tablename__: str = "auth_sessions"

    id: Mapped[UUID] = mapped_column(SQL_UUID, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        SQL_UUID, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    csrf_token_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    # Authentication checks this absolute UTC deadline; using a session does not
    # extend it, and an expired row grants no access even before cleanup removes it.
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    user: Mapped[User] = relationship(back_populates="auth_sessions")
