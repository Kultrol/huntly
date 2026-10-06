from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

eng = create_async_engine(settings.database_url)

SessionLocal = async_sessionmaker(bind=eng, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with SessionLocal() as db_session:
        yield db_session
