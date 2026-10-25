from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def test_db():
    from app.core.config import settings
    from app.models import Company, Contact, TrackedRole, User

    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    sessions = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    owner_ids = (uuid4(), uuid4())
    try:
        async with sessions.begin() as session:
            session.add_all([User(id=id, name="Example owner") for id in owner_ids])
        yield sessions, owner_ids
    finally:
        try:
            async with sessions.begin() as session:
                await session.execute(
                    delete(TrackedRole).where(TrackedRole.user_id.in_(owner_ids))
                )
                await session.execute(
                    delete(Contact).where(Contact.user_id.in_(owner_ids))
                )
                await session.execute(
                    delete(Company).where(Company.user_id.in_(owner_ids))
                )
                await session.execute(delete(User).where(User.id.in_(owner_ids)))
        finally:
            await engine.dispose()


@pytest.fixture
def sessions(test_db):
    return test_db[0]


@pytest.fixture
def owner_ids(test_db):
    return test_db[1]


@pytest.fixture
async def saved_company(sessions, owner_ids):
    from app.models import Company

    async with sessions.begin() as session:
        company = Company(user_id=owner_ids[0], name="Amazon")
        session.add(company)
    return company


@pytest.fixture
async def saved_contact(sessions, owner_ids, saved_company):
    from app.models import Contact

    async with sessions.begin() as session:
        contact = Contact(
            user_id=owner_ids[0],
            company_id=saved_company.id,
            name="Jane Doe",
            notes="Original notes",
        )
        session.add(contact)
    return contact


@pytest.fixture
async def saved_role(sessions, owner_ids, saved_company):
    from app.models import TrackedRole

    async with sessions.begin() as session:
        role = TrackedRole(
            user_id=owner_ids[0],
            company_id=saved_company.id,
            title="Backend Developer",
            status="saved",
            salary_min=Decimal(80000),
            salary_max=Decimal(100000),
            notes="Original notes",
        )
        session.add(role)
    return role


@pytest.fixture
async def api_client(sessions):
    from httpx2 import ASGITransport, AsyncClient

    from app.core.database import get_db
    from app.main import app

    async def override_get_db():
        async with sessions() as session:
            yield session

    previous_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield client
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous_override
