import pytest

from app.schemas.company import CompanyCreate
from app.services.company import CompanyService


@pytest.fixture
def company_factory(sessions, owner_ids):

    async def create_company(name="Amazon", user_id=None, **fields):
        new_company_data = CompanyCreate(
            user_id=owner_ids[0] if user_id is None else user_id,
            name=name,
            **fields,
        )
        async with sessions() as session:
            company_service = CompanyService(db=session)
            company = await company_service.create_company(new_company_data)
            await session.commit()
        return company

    return create_company


@pytest.fixture
async def saved_company(company_factory):
    return await company_factory()


@pytest.fixture
def company_metadata():
    return {
        "website": "https://amazon.example/",
        "linkedin_url": "https://www.linkedin.com/company/amazon/",
        "location": "Seattle",
        "notes": "Ask about the backend team.",
    }


@pytest.fixture
async def company_with_metadata(company_factory, company_metadata):
    return await company_factory(**company_metadata)
