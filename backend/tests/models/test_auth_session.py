from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import AuthSession, User

pytestmark = pytest.mark.anyio


async def test_auth_session_defaults_and_owner_relationship(sessions, owner_ids):
    expires_at = datetime.now(UTC) + timedelta(days=7)
    async with sessions.begin() as session:
        auth_session = AuthSession(
            user_id=owner_ids[0],
            token_hash="a" * 64,
            csrf_token_hash="b" * 64,
            expires_at=expires_at,
        )
        session.add(auth_session)

    async with sessions() as session:
        owner = await session.scalar(
            select(User)
            .where(User.id == owner_ids[0])
            .options(selectinload(User.auth_sessions))
        )
        assert owner is not None
        assert len(owner.auth_sessions) == 1
        saved = owner.auth_sessions[0]
        assert isinstance(saved.id, UUID)
        assert saved.user_id == owner.id
        assert saved.token_hash == "a" * 64
        assert saved.csrf_token_hash == "b" * 64
        assert saved.created_at.tzinfo is not None
        assert saved.created_at < saved.expires_at
        assert saved.expires_at == expires_at


async def test_deleting_user_cascades_to_unloaded_auth_sessions(sessions, owner_ids):
    async with sessions.begin() as session:
        auth_session = AuthSession(
            user_id=owner_ids[0],
            token_hash="a" * 64,
            csrf_token_hash="b" * 64,
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        session.add(auth_session)

    async with sessions.begin() as session:
        owner = await session.get(User, owner_ids[0])
        await session.delete(owner)

    async with sessions() as session:
        assert await session.get(User, owner_ids[0]) is None
        assert await session.get(AuthSession, auth_session.id) is None
