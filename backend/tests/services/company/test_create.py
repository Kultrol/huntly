import pytest
from sqlalchemy import select

from app.models.company import Company
from app.schemas.company import CompanyCreate
from app.services.company import CompanyService
from app.services.exceptions.company import (
    CompanyAlreadyExistsError,
)

pytestmark = pytest.mark.anyio


# A created company must still exist when read through a new session.
async def test_company_creation_persistence(sessions, owner_ids):
    new_company_create = CompanyCreate(user_id=owner_ids[0], name="Amazon")

    async with sessions() as session:
        company_service = CompanyService(db=session)
        new_company = await company_service.create_company(new_company_create)
        await session.commit()

    async with sessions() as session:
        found_new_company = await session.get(Company, new_company.id)
        assert found_new_company is not None
        assert found_new_company.name == "Amazon"
        assert found_new_company.user_id == owner_ids[0]


# Optional company details must survive creation and a fresh database read.
async def test_company_create_persists_optional_fields(
    sessions, owner_ids, company_metadata
):
    new_company_create = CompanyCreate(
        user_id=owner_ids[0], name="Amazon", **company_metadata
    )

    async with sessions() as session:
        company_service = CompanyService(db=session)
        new_company = await company_service.create_company(new_company_create)
        await session.commit()

    async with sessions() as session:
        found_company = await session.get(Company, new_company.id)

        assert found_company is not None
        assert found_company.user_id == owner_ids[0]
        assert found_company.website == company_metadata["website"]
        assert found_company.linkedin_url == company_metadata["linkedin_url"]
        assert found_company.location == company_metadata["location"]
        assert found_company.notes == company_metadata["notes"]


# New companies must store normalized display and comparison names.
@pytest.mark.parametrize(
    "name, expected_name, expected_normalized_name",
    [
        ("  Acme\t  LABS\n", "Acme LABS", "acme labs"),
        ("  Straße\u2003 GMBH  ", "Straße GMBH", "strasse gmbh"),
        ("  CAFÉ  ", "CAFÉ", "café"),
    ],
)
async def test_company_create_name_normalization_persistence(
    sessions, owner_ids, name, expected_name, expected_normalized_name
):
    new_company_create = CompanyCreate(user_id=owner_ids[0], name=name)

    async with sessions() as session:
        company_service = CompanyService(db=session)
        new_company = await company_service.create_company(new_company_create)
        await session.commit()

    async with sessions() as session:
        found_new_company = await session.get(Company, new_company.id)
        assert found_new_company is not None
        assert found_new_company.name == expected_name
        assert found_new_company.normalized_name == expected_normalized_name
        assert found_new_company.user_id == owner_ids[0]


# Equivalent names for one owner must be rejected without changing the original.
@pytest.mark.parametrize(
    "name, duplicate_name",
    [
        pytest.param("Amazon", " amazon ", id="case-and-trimming"),
        pytest.param("Straße GmbH", " STRASSE\tGMBH ", id="unicode-casefold"),
        pytest.param("Acme Labs", "Acme\u00a0 \u2003Labs", id="unicode-whitespace"),
    ],
)
async def test_company_create_normalized_duplicate_preserves_original(
    sessions, owner_ids, company_factory, name, duplicate_name
):
    new_company = await company_factory(name=name)
    duplicate_company_create = CompanyCreate(user_id=owner_ids[0], name=duplicate_name)

    async with sessions() as session:
        company_service = CompanyService(db=session)
        with pytest.raises(CompanyAlreadyExistsError):
            await company_service.create_company(duplicate_company_create)
        await session.rollback()

    async with sessions() as session:
        found_company = await session.get(Company, new_company.id)
        assert found_company is not None
        assert found_company.name == name
        assert found_company.user_id == owner_ids[0]
        found_companies = list(
            await session.scalars(
                select(Company).where(Company.user_id == owner_ids[0])
            )
        )
        assert len(found_companies) == 1
        assert found_companies[0].id == new_company.id


# Different owners may create companies whose comparison names are identical.
async def test_company_create_same_normalized_name_for_different_owners(
    sessions, owner_ids, company_factory
):
    first_company = await company_factory(name="Straße GmbH")
    second_company_create = CompanyCreate(user_id=owner_ids[1], name="STRASSE  GmbH")

    async with sessions() as session:
        company_service = CompanyService(db=session)
        second_company = await company_service.create_company(second_company_create)
        await session.commit()

    async with sessions() as session:
        found_first_company = await session.get(Company, first_company.id)
        found_second_company = await session.get(Company, second_company.id)
        assert found_first_company is not None
        assert found_second_company is not None
        assert found_first_company.user_id == owner_ids[0]
        assert found_second_company.user_id == owner_ids[1]
        assert found_first_company.normalized_name == "strasse gmbh"
        assert found_second_company.normalized_name == "strasse gmbh"
