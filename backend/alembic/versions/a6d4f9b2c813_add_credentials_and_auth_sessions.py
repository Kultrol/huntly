"""Add optional user credentials and revocable authentication sessions.

Revision ID: a6d4f9b2c813
Revises: 22017b5e84d4

Existing owners and their records are preserved without inventing credentials.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a6d4f9b2c813"
down_revision: str | Sequence[str] | None = "22017b5e84d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add auth storage while retaining existing owners and all domain records."""
    # Leave both credentials null on old rows. Claiming those owners requires an
    # explicit trusted provisioning process, not a guessed email or password.
    op.add_column("users", sa.Column("email", sa.String(254), nullable=True))
    op.add_column("users", sa.Column("password_hash", sa.String(255), nullable=True))
    op.create_unique_constraint("uq_users_email", "users", ["email"])
    op.create_check_constraint(
        "ck_users_credentials_pair",
        "users",
        "(email IS NULL) = (password_hash IS NULL)",
    )
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("csrf_token_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
    op.create_index("ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"])


def downgrade() -> None:
    """Remove auth storage only when it holds no credentials or sessions."""
    # Keep the credential/session check valid until storage is removed: these
    # transaction-held locks prevent a concurrent signup or session insertion.
    op.execute("LOCK TABLE users, auth_sessions IN ACCESS EXCLUSIVE MODE")
    op.execute(
        """
        DO $auth_downgrade_guard$
        BEGIN
            IF EXISTS (SELECT 1 FROM users WHERE email IS NOT NULL)
                OR EXISTS (SELECT 1 FROM auth_sessions) THEN
                RAISE EXCEPTION 'Cannot downgrade populated authentication schema. '
                    'This would discard login credentials or sessions.';
            END IF;
        END
        $auth_downgrade_guard$;
        """
    )
    op.drop_index("ix_auth_sessions_expires_at", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_user_id", table_name="auth_sessions")
    op.drop_table("auth_sessions")
    op.drop_constraint("ck_users_credentials_pair", "users", type_="check")
    op.drop_constraint("uq_users_email", "users", type_="unique")
    op.drop_column("users", "password_hash")
    op.drop_column("users", "email")
