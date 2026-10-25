from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.company import Company
from app.schemas.company import CompanyCreate, CompanyUpdate
from app.services.company import CompanyService
from app.services.exceptions.company import (
    CompanyServiceError,
)

pytestmark = pytest.mark.anyio


# The database must reject a duplicate even when the service precheck misses it.
@pytest.mark.parametrize("operation", ["create", "update"])
async def test_company_duplicate_write_at_database_is_rolled_back(
    sessions, owner_ids, company_factory, monkeypatch, operation
):
    first_company = await company_factory()
    second_company = await company_factory(name="Google")

    async with sessions() as session:
        company_service = CompanyService(db=session)
        # Simulate a precheck that missed a conflicting write; flush still uses
        # the real database and its unique constraint.
        skipped_precheck = AsyncMock(return_value=None)
        with monkeypatch.context() as patch:
            patch.setattr(session, "scalar", skipped_precheck)
            with pytest.raises(CompanyServiceError) as error:
                if operation == "create":
                    await company_service.create_company(
                        CompanyCreate(user_id=owner_ids[0], name="AMAZON")
                    )
                else:
                    await company_service.update_company(
                        id=second_company.id,
                        company_data=CompanyUpdate(name="AMAZON"),
                    )
        skipped_precheck.assert_awaited_once()
        assert isinstance(error.value.__cause__, IntegrityError)
        await session.rollback()

    async with sessions() as session:
        found_first_company = await session.get(Company, first_company.id)
        found_second_company = await session.get(Company, second_company.id)
        assert found_first_company is not None
        assert found_first_company.name == "Amazon"
        assert found_second_company is not None
        assert found_second_company.name == "Google"
        found_companies = list(
            await session.scalars(
                select(Company).where(Company.user_id == owner_ids[0])
            )
        )
        assert len(found_companies) == 2


# Rolling back a new company must remove its flushed database row.
async def test_company_creation_rollback_does_not_persist(sessions, owner_ids):
    new_company_create = CompanyCreate(user_id=owner_ids[0], name="Amazon")

    async with sessions() as session:
        company_service = CompanyService(db=session)
        new_company = await company_service.create_company(new_company_create)
        new_company_id = new_company.id
        assert await session.get(Company, new_company_id) is new_company
        await session.rollback()

    async with sessions() as session:
        found_new_company = await session.get(Company, new_company_id)
        assert found_new_company is None


# Rolling back a rename must restore the original company values.
async def test_company_update_rollback_preserves_original(
    sessions, owner_ids, saved_company
):
    async with sessions() as session:
        company_service = CompanyService(db=session)
        updated_company = await company_service.update_company(
            id=saved_company.id, company_data=CompanyUpdate(name="Google")
        )
        assert updated_company.name == "Google"
        await session.rollback()

    async with sessions() as session:
        found_company = await session.get(Company, saved_company.id)
        assert found_company is not None
        assert found_company.name == "Amazon"
        assert found_company.normalized_name == "amazon"
        assert found_company.user_id == owner_ids[0]


# Rolling back a company deletion must keep the original row.
async def test_company_delete_rollback_preserves_original(
    sessions, owner_ids, saved_company
):
    async with sessions() as session:
        company_service = CompanyService(db=session)
        await company_service.delete_company(id=saved_company.id)
        assert await session.get(Company, saved_company.id) is None
        await session.rollback()

    async with sessions() as session:
        found_company = await session.get(Company, saved_company.id)
        assert found_company is not None
        assert found_company.name == "Amazon"
        assert found_company.user_id == owner_ids[0]
