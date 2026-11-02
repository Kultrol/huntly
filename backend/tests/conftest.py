from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
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
    from app.enums import TrackedRoleStatus
    from app.schemas.tracked_role import TrackedRoleCreate
    from app.services.tracked_role import TrackedRoleService

    async with sessions.begin() as session:
        role = await TrackedRoleService(session).create_tracked_role(
            TrackedRoleCreate(
                user_id=owner_ids[0],
                company_id=saved_company.id,
                title="Backend Developer",
                status=TrackedRoleStatus.SAVED,
                salary_min=Decimal(80000),
                salary_max=Decimal(100000),
                notes="Original notes",
            )
        )
    return role


@pytest.fixture
async def saved_event(sessions, saved_role):
    from app.schemas.event import EventCreate
    from app.services.event import EventService

    async with sessions.begin() as session:
        event = await EventService(session).create_event(
            EventCreate.model_validate(
                {
                    "tracked_role_id": saved_role.id,
                    "title": "Phone screen",
                    "event_type": "recruiter_screen",
                    "event_date": "2026-10-20",
                    "status": "scheduled",
                    "notes": "Original notes",
                }
            )
        )
    return event


@pytest.fixture
async def client_factory(sessions, monkeypatch):
    """Open anonymous or signed-in clients using the real session/CSRF checks.

    Each request receives a fresh database session from the test factory. Passing
    an owner ID seeds a login directly so resource tests can focus on ownership;
    registration and login tests instead start with an anonymous client.
    """
    from httpx2 import ASGITransport, AsyncClient

    from app.core.config import settings
    from app.core.database import get_db
    from app.core.security import csrf_token_for_session, digest_token
    from app.main import app
    from app.models import AuthSession

    # The in-process client uses HTTP, so it cannot send HTTPS-only cookies.
    monkeypatch.setattr(settings, "session_cookie_secure", False)

    async def override_get_db():
        async with sessions() as session:
            yield session

    @asynccontextmanager
    async def make_client(owner_id=None, *, raise_app_exceptions=True):
        headers = {}
        cookies = {}
        if owner_id is not None:
            # Store only token digests, just as production session creation does.
            token = uuid4().hex + uuid4().hex
            csrf_token = csrf_token_for_session(token)
            async with sessions.begin() as session:
                session.add(
                    AuthSession(
                        user_id=owner_id,
                        token_hash=digest_token(token),
                        csrf_token_hash=digest_token(csrf_token),
                        expires_at=datetime.now(UTC) + timedelta(hours=1),
                    )
                )
            headers["X-CSRF-Token"] = csrf_token
            cookies[settings.session_cookie_name] = token
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=raise_app_exceptions),
            base_url="http://test",
            headers=headers,
            cookies=cookies,
        ) as client:
            yield client

    # Restore the earlier dependency after the test to avoid leaking test state.
    previous_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    try:
        yield make_client
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous_override


@pytest.fixture
async def api_client(client_factory, owner_ids):
    async with client_factory(owner_ids[0]) as client:
        yield client


@pytest.fixture
async def anonymous_client(client_factory):
    async with client_factory() as client:
        yield client


@pytest.fixture
def authenticated_client_factory(client_factory):
    return client_factory
