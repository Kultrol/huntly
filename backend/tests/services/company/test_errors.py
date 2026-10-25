from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.models.company import Company
from app.schemas.company import CompanyCreate, CompanyUpdate
from app.services.company import CompanyService
from app.services.exceptions.company import (
    CompanyCreationError,
    CompanyDeletionError,
    CompanyFetchingError,
    CompanyNotFoundError,
    CompanyUpdateError,
)

pytestmark = pytest.mark.anyio


# Reading, updating, or deleting an unknown company must report it as missing.
@pytest.mark.parametrize("operation", ["get", "update", "delete"])
async def test_company_missing_record_raises_company_not_found(sessions, operation):
    missing_company_id = uuid4()

    async with sessions() as session:
        company_service = CompanyService(db=session)
        with pytest.raises(CompanyNotFoundError):
            if operation == "get":
                await company_service.get_company_by_id(missing_company_id)
            elif operation == "update":
                await company_service.update_company(
                    id=missing_company_id, company_data=CompanyUpdate(name="Google")
                )
            else:
                await company_service.delete_company(id=missing_company_id)
        await session.rollback()


# Database failures must retain their original cause and allow caller rollback.
@pytest.mark.parametrize(
    ("operation", "database_method", "expected_error"),
    [
        ("get", "get", CompanyFetchingError),
        ("list", "scalars", CompanyFetchingError),
        ("create", "scalar", CompanyCreationError),
        ("create", "flush", CompanyCreationError),
        ("update", "flush", CompanyUpdateError),
        ("update", "refresh", CompanyUpdateError),
        ("delete", "flush", CompanyDeletionError),
    ],
)
async def test_company_database_error_preserves_cause(
    sessions,
    owner_ids,
    saved_company,
    monkeypatch,
    operation,
    database_method,
    expected_error,
):
    async with sessions() as session:
        company_service = CompanyService(db=session)
        database_error = SQLAlchemyError("Database operation failed")
        with monkeypatch.context() as patch:
            patch.setattr(
                session, database_method, AsyncMock(side_effect=database_error)
            )
            with pytest.raises(expected_error) as error:
                if operation == "get":
                    await company_service.get_company_by_id(saved_company.id)
                elif operation == "list":
                    await company_service.get_all_companies(user_id=owner_ids[0])
                elif operation == "create":
                    await company_service.create_company(
                        CompanyCreate(user_id=owner_ids[0], name="Google")
                    )
                elif operation == "update":
                    await company_service.update_company(
                        id=saved_company.id,
                        company_data=CompanyUpdate(name="Google"),
                    )
                else:
                    await company_service.delete_company(id=saved_company.id)
        assert error.value.__cause__ is database_error
        await session.rollback()

    async with sessions() as session:
        found_company = await session.get(Company, saved_company.id)
        assert found_company is not None
        assert found_company.name == "Amazon"
        assert found_company.user_id == owner_ids[0]
