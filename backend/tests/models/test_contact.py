from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Contact


# Contact names retain meaningful text while repeated whitespace is collapsed.
@pytest.mark.parametrize(
    "name, expected_name", [("  Jane\t Doe  ", "Jane Doe"), ("  José  ", "José")]
)
def test_contact_normalizes_name_on_construction_and_assignment(name, expected_name):
    contact = Contact(name=name)
    assert contact.name == expected_name
    contact.name = "  Janet   Doe "
    assert contact.name == "Janet Doe"


# Invalid names are rejected before they can replace an existing valid contact name.
@pytest.mark.parametrize("name", [None, 10, "", " \t\n"])
def test_contact_rejects_invalid_name_on_construction_and_assignment(name):
    with pytest.raises(ValueError):
        Contact(name=name)
    contact = Contact(name="Jane")
    with pytest.raises(ValueError):
        contact.name = name
    assert contact.name == "Jane"


# Contacts need a valid owner even when they have no company affiliation.
@pytest.mark.anyio
@pytest.mark.parametrize("user_id", [None, "missing"])
async def test_contact_requires_existing_owner(sessions, user_id):
    async with sessions() as session:
        session.add(Contact(user_id=uuid4() if user_id else None, name="Jane"))
        with pytest.raises(IntegrityError):
            await session.flush()
        await session.rollback()


# Contacts may share names and contact details without belonging to a company.
@pytest.mark.anyio
async def test_contact_allows_duplicate_identifiers_without_company(
    sessions, owner_ids
):
    async with sessions.begin() as session:
        first = Contact(
            user_id=owner_ids[0],
            name="Jane",
            email="jane@example.com",
            linkedin_url="https://example.com/jane",
        )
        second = Contact(
            user_id=owner_ids[0],
            name="Jane",
            email="jane@example.com",
            linkedin_url="https://example.com/jane",
        )
        session.add_all([first, second])
    async with sessions() as session:
        found_first = await session.get(Contact, first.id)
        found_second = await session.get(Contact, second.id)
        assert found_first is not None
        assert found_second is not None
        assert found_first.id != found_second.id
        assert found_first.company_id is None
        assert found_second.company_id is None
