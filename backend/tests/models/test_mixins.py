from datetime import UTC, datetime

import pytest
from sqlalchemy import text

from app.models import Company

pytestmark = pytest.mark.anyio


# ORM edits advance the update timestamp while preserving the creation timestamp.
async def test_storage_timestamps_are_generated_and_orm_update_changes_only_updated_at(
    sessions, saved_company
):
    async with sessions() as session:
        company = await session.get(Company, saved_company.id)
        assert company is not None
        assert company.created_at.tzinfo is not None
        assert company.updated_at.tzinfo is not None
        created_at = company.created_at
        # A fixed old timestamp avoids depending on sleeps or clock precision.
        await session.execute(
            text("UPDATE companies SET updated_at = :old WHERE id = :id"),
            {"old": datetime(2000, 1, 1, tzinfo=UTC), "id": company.id},
        )
        await session.commit()
    async with sessions() as session:
        company = await session.get(Company, saved_company.id)
        company.location = "Seattle"
        await session.commit()
    async with sessions() as session:
        company = await session.get(Company, saved_company.id)
        assert company is not None
        assert company.created_at == created_at
        assert company.updated_at > datetime(2000, 1, 1, tzinfo=UTC)


# Timestamp refreshes come from SQLAlchemy updates rather than a database trigger.
async def test_raw_sql_update_does_not_refresh_timestamp(sessions, saved_company):
    async with sessions() as session:
        await session.execute(
            text("UPDATE companies SET location = 'Seattle' WHERE id = :id"),
            {"id": saved_company.id},
        )
        await session.commit()
    async with sessions() as session:
        company = await session.get(Company, saved_company.id)
        assert company is not None
        assert company.location == "Seattle"
        assert company.updated_at == saved_company.updated_at
