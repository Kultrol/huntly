import pytest

from app.enums import TrackedRoleStatus
from app.models.company import Company
from app.models.contact import Contact
from app.models.tracked_role.tracked_role import TrackedRole
from app.services.company import CompanyService

pytestmark = pytest.mark.anyio


# A committed deletion must remove the company from later sessions.
async def test_company_delete_persistence(sessions, saved_company):
    async with sessions() as session:
        company_service = CompanyService(db=session)
        assert await company_service.get_company_by_id(saved_company.id) is not None
        await company_service.delete_company(id=saved_company.id)
        await session.commit()

    async with sessions() as session:
        deleted_company = await session.get(Company, saved_company.id)
        assert deleted_company is None


# Deleting a company must clear its links without deleting contacts or roles.
async def test_company_delete_preserves_contacts_and_tracked_roles(
    sessions, owner_ids, saved_company
):
    async with sessions() as session:
        contact = Contact(
            user_id=owner_ids[0], company_id=saved_company.id, name="John Doe"
        )
        tracked_role = TrackedRole(
            user_id=owner_ids[0],
            company_id=saved_company.id,
            title="Backend Developer",
            status=TrackedRoleStatus.SAVED,
        )
        session.add_all([contact, tracked_role])
        await session.commit()

    async with sessions() as session:
        found_contact = await session.get(Contact, contact.id)
        found_role = await session.get(TrackedRole, tracked_role.id)
        assert found_contact is not None
        assert found_role is not None
        assert found_contact.company_id == saved_company.id
        assert found_role.company_id == saved_company.id

        company_service = CompanyService(db=session)
        await company_service.delete_company(saved_company.id)
        await session.commit()

    async with sessions() as session:
        assert await session.get(Company, saved_company.id) is None
        found_contact = await session.get(Contact, contact.id)
        found_role = await session.get(TrackedRole, tracked_role.id)

        assert found_contact is not None
        assert found_contact.user_id == owner_ids[0]
        assert found_contact.company_id is None
        assert found_contact.name == "John Doe"
        assert found_role is not None
        assert found_role.user_id == owner_ids[0]
        assert found_role.company_id is None
        assert found_role.title == "Backend Developer"
