from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import UUID as SQL_UUID
from sqlalchemy import CheckConstraint, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.auth_session import AuthSession
    from app.models.company import Company
    from app.models.contact import Contact
    from app.models.tracked_role.tracked_role import TrackedRole


class User(Base):
    """Owner of companies, contacts, and opportunities.

    Existing users may have no credentials; registration provisions an email and
    password hash together. Keeping both fields nullable preserves legacy owners
    and their records without giving them invented login credentials. The display
    name remains independent of the login and cannot identify an account securely.
    """

    __tablename__: str = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        # A legacy owner has neither credential field; a login account has both.
        CheckConstraint(
            "(email IS NULL) = (password_hash IS NULL)",
            name="ck_users_credentials_pair",
        ),
    )
    id: Mapped[UUID] = mapped_column(SQL_UUID, default=uuid4, primary_key=True)
    name: Mapped[str] = mapped_column(
        String,
        nullable=False,
        comment="User Display Name",
    )
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # The database deletes unloaded sessions; ORM cascade handles loaded sessions
    # and sessions explicitly removed from this relationship.
    auth_sessions: Mapped[list[AuthSession]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    tracked_roles: Mapped[list[TrackedRole]] = relationship(back_populates="user")
    companies: Mapped[list[Company]] = relationship(back_populates="user")
    contacts: Mapped[list[Contact]] = relationship(back_populates="user")
