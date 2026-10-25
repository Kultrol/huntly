from uuid import uuid4

import pytest

from app.models.company import Company
from app.services.company import CompanyService

pytestmark = pytest.mark.anyio


# Looking up an existing company must return its saved fields.
async def test_company_get_by_id_returns_saved_company(
    sessions, owner_ids, saved_company
):
    async with sessions() as session:
        company_service = CompanyService(db=session)
        found_company = await company_service.get_company_by_id(saved_company.id)

        assert found_company.id == saved_company.id
        assert found_company.name == "Amazon"
        assert found_company.normalized_name == "amazon"
        assert found_company.user_id == owner_ids[0]


# Each owner must receive only their own companies in name order.
async def test_company_list_filters_by_owner_and_orders_by_name(
    sessions, owner_ids, company_factory
):
    zebra_company = await company_factory(name="Zebra")
    amazon_company = await company_factory()
    other_owner_company = await company_factory(name="Google", user_id=owner_ids[1])

    async with sessions() as session:
        company_service = CompanyService(db=session)
        owner_companies = await company_service.get_all_companies(owner_ids[0])
        other_owner_companies = await company_service.get_all_companies(owner_ids[1])

        assert [company.id for company in owner_companies] == [
            amazon_company.id,
            zebra_company.id,
        ]
        assert [company.name for company in owner_companies] == ["Amazon", "Zebra"]
        assert all(company.user_id == owner_ids[0] for company in owner_companies)
        assert [company.id for company in other_owner_companies] == [
            other_owner_company.id
        ]
        assert other_owner_companies[0].user_id == owner_ids[1]


# The unfiltered company list must include both owners and sort equal names by ID.
async def test_company_list_without_owner_includes_both_owners_and_orders_ties(
    sessions, owner_ids
):
    amazon_ids = sorted([uuid4(), uuid4()], reverse=True)

    async with sessions() as session:
        zebra_company = Company(user_id=owner_ids[0], name="Zebra")
        first_amazon = Company(id=amazon_ids[0], user_id=owner_ids[0], name="Amazon")
        second_amazon = Company(id=amazon_ids[1], user_id=owner_ids[1], name="Amazon")
        # Insert matching names with the larger ID first to exercise the ID sort.
        session.add_all([zebra_company, first_amazon, second_amazon])
        await session.commit()

    async with sessions() as session:
        company_service = CompanyService(db=session)
        all_companies = await company_service.get_all_companies()
        owner_companies = [
            company for company in all_companies if company.user_id in owner_ids
        ]

        expected_ids = sorted([first_amazon.id, second_amazon.id])
        expected_ids.append(zebra_company.id)
        assert [company.id for company in owner_companies] == expected_ids
        assert {company.user_id for company in owner_companies} == set(owner_ids)
