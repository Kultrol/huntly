"""Manage account credentials within transactions owned by the API routes."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.security import DUMMY_PASSWORD_HASH, hash_password, verify_password
from app.models import User
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.auth_session import AuthSessionService


class AuthService:
    """Coordinate credentials and login sessions without committing changes.

    Routes commit before setting or clearing cookies. The session service owns
    session queries; this service owns account and password decisions.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.sessions = AuthSessionService(db)

    async def register(
        self, data: RegisterRequest, old_token: str | None
    ) -> tuple[User, str]:
        """Create an account and its first session in the caller's transaction."""
        # A helper thread handles slow password work while other requests run.
        password_hash = await run_in_threadpool(
            hash_password, data.password.get_secret_value()
        )
        user = User(name=data.name, email=str(data.email), password_hash=password_hash)
        self.db.add(user)
        # Assign the user ID before creating the session, without committing yet.
        await self.db.flush()
        token = await self.sessions.create(user.id, old_token)
        return user, token

    async def login(
        self, data: LoginRequest, old_token: str | None
    ) -> tuple[User, str]:
        """Verify credentials and rotate the browser's session on success."""
        # Password changes take the same lock, so verification and session
        # creation cannot overlap a password replacement for this user.
        user = await self.db.scalar(
            select(User).where(User.email == str(data.email)).with_for_update()
        )
        password_hash = user.password_hash if user is not None else None
        password_matches = await run_in_threadpool(
            verify_password,
            data.password.get_secret_value(),
            password_hash or DUMMY_PASSWORD_HASH,
        )
        if not password_matches or user is None or password_hash is None:
            raise HTTPException(status_code=401, detail="Invalid email or password.")
        token = await self.sessions.create(user.id, old_token)
        return user, token
