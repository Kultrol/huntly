from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

eng: AsyncEngine = create_async_engine(settings.database_url)

# Responses are serialized after the route's transaction commits. Retaining
# loaded fields avoids an implicit database refresh during async serialization.
SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=eng, autoflush=False, autocommit=False, expire_on_commit=False
)


class Base(DeclarativeBase):
    """Shared table registry for ORM models and Alembic migrations."""


async def get_db() -> AsyncGenerator[AsyncSession]:
    """Yield a request-scoped session; routes own transactions and commits.

    Closing the session releases connections and rolls back pending work.
    Loaded fields survive commits, but relationships still need explicit loading.
    """
    async with SessionLocal() as db_session:
        yield db_session
