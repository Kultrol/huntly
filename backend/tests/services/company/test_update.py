import pytest

from app.models.company import Company
from app.schemas.company import CompanyUpdate
from app.services.company import CompanyService
from app.services.exceptions.company import (
    CompanyAlreadyExistsError,
)

pytestmark = pytest.mark.anyio


# A committed name change must keep the company identity and owner.
async def test_company_update_persistence(sessions, owner_ids, saved_company):
    update_data = CompanyUpdate(name="Google")

    async with sessions() as session:
        company_service = CompanyService(db=session)
        updated_company = await company_service.update_company(
            id=saved_company.id, company_data=update_data
        )
        await session.commit()
        assert updated_company.id == saved_company.id

    async with sessions() as session:
        found_updated_company = await session.get(Company, saved_company.id)
        assert found_updated_company is not None
        assert found_updated_company.user_id == owner_ids[0]
        assert found_updated_company.name == "Google"


# Updating optional details must retain the company name and owner.
async def test_company_update_persists_optional_fields(
    sessions, owner_ids, saved_company, company_metadata
):
    update_data = CompanyUpdate(**company_metadata)

    async with sessions() as session:
        company_service = CompanyService(db=session)
        await company_service.update_company(
            id=saved_company.id, company_data=update_data
        )
        await session.commit()

    async with sessions() as session:
        found_company = await session.get(Company, saved_company.id)

        assert found_company is not None
        assert found_company.name == "Amazon"
        assert found_company.user_id == owner_ids[0]
        assert found_company.website == company_metadata["website"]
        assert found_company.linkedin_url == company_metadata["linkedin_url"]
        assert found_company.location == company_metadata["location"]
        assert found_company.notes == company_metadata["notes"]


# Renaming a company must update both its display and comparison names.
@pytest.mark.parametrize(
    "name, expected_name, expected_normalized_name",
    [
        ("  Acme\t  LABS\n", "Acme LABS", "acme labs"),
        ("  Straße\u2003 GMBH  ", "Straße GMBH", "strasse gmbh"),
    ],
)
async def test_company_update_name_normalization_persistence(
    sessions, owner_ids, saved_company, name, expected_name, expected_normalized_name
):
    update_data = CompanyUpdate(name=name)

    async with sessions() as session:
        company_service = CompanyService(db=session)
        await company_service.update_company(
            id=saved_company.id, company_data=update_data
        )
        await session.commit()

    async with sessions() as session:
        found_updated_company = await session.get(Company, saved_company.id)
        assert found_updated_company is not None
        assert found_updated_company.name == expected_name
        assert found_updated_company.normalized_name == expected_normalized_name
        assert found_updated_company.user_id == owner_ids[0]


# A conflicting rename must leave both companies unchanged.
async def test_company_update_duplicate_name_preserves_both_companies(
    sessions, saved_company, company_factory
):
    second_company = await company_factory(name="Straße GmbH")
    update_data = CompanyUpdate(name=" STRASSE\tGMBH ")

    async with sessions() as session:
        company_service = CompanyService(db=session)
        with pytest.raises(CompanyAlreadyExistsError):
            await company_service.update_company(
                id=saved_company.id, company_data=update_data
            )
        await session.rollback()

    async with sessions() as session:
        found_first_company = await session.get(Company, saved_company.id)
        found_second_company = await session.get(Company, second_company.id)
        assert found_first_company is not None
        assert found_second_company is not None
        assert found_first_company.name == "Amazon"
        assert found_first_company.normalized_name == "amazon"
        assert found_second_company.name == "Straße GmbH"
        assert found_second_company.normalized_name == "strasse gmbh"


# A company may change capitalization without conflicting with itself.
async def test_company_update_same_normalized_name_is_allowed(
    sessions, owner_ids, saved_company
):
    update_data = CompanyUpdate(name="  AMAZON  ")

    async with sessions() as session:
        company_service = CompanyService(db=session)
        await company_service.update_company(
            id=saved_company.id, company_data=update_data
        )
        await session.commit()

    async with sessions() as session:
        found_updated_company = await session.get(Company, saved_company.id)
        assert found_updated_company is not None
        assert found_updated_company.name == "AMAZON"
        assert found_updated_company.normalized_name == "amazon"
        assert found_updated_company.user_id == owner_ids[0]


# A rename may match a company belonging to another owner.
async def test_company_update_to_other_owners_name_is_allowed(
    sessions, owner_ids, saved_company, company_factory
):
    second_company = await company_factory(name="Google", user_id=owner_ids[1])
    update_data = CompanyUpdate(name=" GOOGLE ")

    async with sessions() as session:
        company_service = CompanyService(db=session)
        await company_service.update_company(
            id=saved_company.id, company_data=update_data
        )
        await session.commit()

    async with sessions() as session:
        found_first_company = await session.get(Company, saved_company.id)
        found_second_company = await session.get(Company, second_company.id)
        assert found_first_company is not None
        assert found_second_company is not None
        assert found_first_company.name == "GOOGLE"
        assert found_first_company.normalized_name == "google"
        assert found_first_company.user_id == owner_ids[0]
        assert found_second_company.name == "Google"
        assert found_second_company.normalized_name == "google"
        assert found_second_company.user_id == owner_ids[1]


# Fields omitted from a company patch must keep their stored values.
@pytest.mark.parametrize(
    "changes, expected_name, expected_notes",
    [
        pytest.param(
            {"name": "Google"},
            "Google",
            "Ask about the backend team.",
            id="omitted-metadata",
        ),
        pytest.param(
            {"notes": "Ask about internship opportunities."},
            "Amazon",
            "Ask about internship opportunities.",
            id="omitted-name",
        ),
        pytest.param({}, "Amazon", "Ask about the backend team.", id="empty-patch"),
    ],
)
async def test_company_update_preserves_omitted_fields(
    sessions,
    owner_ids,
    company_with_metadata,
    company_metadata,
    changes,
    expected_name,
    expected_notes,
):
    update_data = CompanyUpdate(**changes)

    async with sessions() as session:
        company_service = CompanyService(db=session)
        await company_service.update_company(
            id=company_with_metadata.id, company_data=update_data
        )
        await session.commit()

    async with sessions() as session:
        found_updated_company = await session.get(Company, company_with_metadata.id)
        assert found_updated_company is not None
        assert found_updated_company.user_id == owner_ids[0]
        assert found_updated_company.name == expected_name
        assert found_updated_company.normalized_name == expected_name.casefold()
        assert found_updated_company.website == company_metadata["website"]
        assert found_updated_company.linkedin_url == company_metadata["linkedin_url"]
        assert found_updated_company.location == company_metadata["location"]
        assert found_updated_company.notes == expected_notes


# An explicit null must clear only the requested optional company field.
@pytest.mark.parametrize("field", ["website", "linkedin_url", "location", "notes"])
async def test_company_update_explicit_none_clears_nullable_field(
    sessions, owner_ids, company_with_metadata, company_metadata, field
):
    update_data = CompanyUpdate(**{field: None})

    async with sessions() as session:
        company_service = CompanyService(db=session)
        await company_service.update_company(
            id=company_with_metadata.id, company_data=update_data
        )
        await session.commit()

    async with sessions() as session:
        found_updated_company = await session.get(Company, company_with_metadata.id)
        assert found_updated_company is not None
        assert found_updated_company.user_id == owner_ids[0]
        assert found_updated_company.name == "Amazon"
        assert found_updated_company.normalized_name == "amazon"
        assert found_updated_company.website == (
            None if field == "website" else company_metadata["website"]
        )
        assert found_updated_company.linkedin_url == (
            None if field == "linkedin_url" else company_metadata["linkedin_url"]
        )
        assert found_updated_company.location == (
            None if field == "location" else company_metadata["location"]
        )
        assert found_updated_company.notes == (
            None if field == "notes" else company_metadata["notes"]
        )
