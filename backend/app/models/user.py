from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import UUID as SQL_UUID
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.contact import Contact
    from app.models.tracked_role.tracked_role import TrackedRole


class User(Base):
    __tablename__ = "users"
    id: Mapped[UUID] = mapped_column(SQL_UUID, default=uuid4, primary_key=True)
    name: Mapped[str] = mapped_column(
        String,
        nullable=False,
        comment="User Display Name",
    )
    tracked_roles: Mapped[list[TrackedRole]] = relationship(back_populates="user")
    companies: Mapped[list[Company]] = relationship(back_populates="user")
    contacts: Mapped[list[Contact]] = relationship(back_populates="user")
