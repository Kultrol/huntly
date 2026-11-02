"""Store and revoke login sessions within the caller's transaction."""

import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import csrf_token_for_session, digest_token
from app.models import AuthSession, User


class AuthSessionService:
    """Manage session rows without committing or opening transaction scopes."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: UUID, previous_token: str | None = None) -> str:
        """Rotate this browser's login and return its new raw cookie token."""
        now = datetime.now(UTC)
        await self.db.execute(
            delete(AuthSession).where(
                AuthSession.user_id == user_id, AuthSession.expires_at <= now
            )
        )
        # The previous cookie may belong to another account when switching users.
        if previous_token and len(previous_token) <= 128:
            await self.db.execute(
                delete(AuthSession).where(
                    AuthSession.token_hash == digest_token(previous_token)
                )
            )
        token = secrets.token_urlsafe(32)
        self.db.add(
            AuthSession(
                user_id=user_id,
                token_hash=digest_token(token),
                csrf_token_hash=digest_token(csrf_token_for_session(token)),
                expires_at=now + timedelta(seconds=settings.session_lifetime_seconds),
            )
        )
        await self.db.flush()
        return token

    async def find_active_with_user(
        self, token: str
    ) -> tuple[AuthSession, User] | None:
        """Load an unexpired session and its owner in one query."""
        result = (
            await self.db.execute(
                select(AuthSession, User)
                .join(User, User.id == AuthSession.user_id)
                .where(
                    AuthSession.token_hash == digest_token(token),
                    AuthSession.expires_at > datetime.now(UTC),
                )
            )
        ).first()
        if result is None:
            return None
        return result[0], result[1]

    async def find_by_token(self, token: str | None) -> AuthSession | None:
        """Include expired sessions so logout can clean them up idempotently."""
        if token is None or len(token) > 128:
            return None
        return await self.db.scalar(
            select(AuthSession).where(AuthSession.token_hash == digest_token(token))
        )

    async def list_active(self, user_id: UUID) -> list[AuthSession]:
        """Return this owner's live sessions in stable creation order."""
        return list(
            await self.db.scalars(
                select(AuthSession)
                .where(
                    AuthSession.user_id == user_id,
                    AuthSession.expires_at > datetime.now(UTC),
                )
                .order_by(AuthSession.created_at, AuthSession.id)
            )
        )

    async def revoke_owned(self, session_id: UUID, user_id: UUID) -> bool:
        """Delete only an owned session and report whether it existed."""
        result = await self.db.execute(
            delete(AuthSession).where(
                AuthSession.id == session_id, AuthSession.user_id == user_id
            )
        )
        return result.rowcount > 0

    async def revoke_all(self, user_id: UUID) -> None:
        """Delete every session; callers coordinate any required user-row lock."""
        await self.db.execute(delete(AuthSession).where(AuthSession.user_id == user_id))
