from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx2 import ASGITransport, AsyncClient

from app.main import app
from app.models import Company
from app.services.company import CompanyService

pytestmark = pytest.mark.anyio


# The company endpoint asks the service for the requested record and formats its dates.
async def test_get_company(monkeypatch: pytest.MonkeyPatch):
    user_id = uuid4()
    company_id = uuid4()
    created_at = datetime.now(UTC)
    updated_at = datetime.now(UTC)

    mock_company = Company(
        id=company_id,
        name="amazon",
        user_id=user_id,
        created_at=created_at,
        updated_at=updated_at,
    )
    mock_get = AsyncMock(return_value=mock_company)

    monkeypatch.setattr(
        target=CompanyService,
        name="get_company_by_id",
        value=mock_get,
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as cli:
        response = await cli.get(f"/companies/{company_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "amazon"
        assert data["user_id"] == str(user_id)
        assert data["id"] == str(company_id)
        assert datetime.fromisoformat(data["created_at"]) == created_at
        assert datetime.fromisoformat(data["updated_at"]) == updated_at

        mock_get.assert_awaited_once_with(company_id)


# Fetching a company returns the saved record, including its owner and dates.
async def test_company_get_returns_saved_record(api_client, saved_company):
    response = await api_client.get(f"/companies/{saved_company.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(saved_company.id)
    assert data["user_id"] == str(saved_company.user_id)
    assert data["name"] == "Amazon"
    assert data["normalized_name"] == "amazon"
    assert datetime.fromisoformat(data["created_at"]) == saved_company.created_at
    assert datetime.fromisoformat(data["updated_at"]) == saved_company.updated_at


# A company list includes this user's records and leaves out another user's companies.
async def test_company_list_excludes_other_owners_records(
    api_client, sessions, owner_ids, saved_company
):
    async with sessions.begin() as session:
        other_company = Company(user_id=owner_ids[1], name="Other company")
        session.add(other_company)
    response = await api_client.get(
        "/companies/", params={"user_id": str(owner_ids[0])}
    )
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [str(saved_company.id)]
    assert response.json()[0]["user_id"] == str(owner_ids[0])


# A user with no companies receives an empty list even when another user has records.
async def test_company_list_for_owner_without_companies_is_empty(
    api_client, owner_ids, saved_company
):
    response = await api_client.get(
        "/companies/", params={"user_id": str(owner_ids[1])}
    )
    assert response.status_code == 200
    assert response.json() == []
