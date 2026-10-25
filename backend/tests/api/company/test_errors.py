from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.company import CompanyService
from app.services.exceptions.company import CompanyServiceError

pytestmark = pytest.mark.anyio


# An unknown company ID returns 404, while an ID in the wrong format returns 422.
@pytest.mark.parametrize("method", ["GET", "PATCH", "DELETE"])
async def test_company_missing_and_invalid_ids(api_client, method):
    payload = {"name": "Example"} if method == "PATCH" else None
    response = await api_client.request(method, f"/companies/{uuid4()}", json=payload)
    assert response.status_code == 404
    response = await api_client.request(
        method,
        "/companies/not-a-uuid",
        json=payload,
    )
    assert response.status_code == 422


# Invalid company fields are rejected before the request can create or change a record.
@pytest.mark.parametrize(
    "method, payload",
    [
        ("POST", {"name": " "}),
        ("POST", {"name": "Example", "website": "invalid"}),
        ("PATCH", {"name": None}),
    ],
)
async def test_company_invalid_request_returns_422(
    api_client, owner_ids, saved_company, method, payload
):
    if method == "POST":
        response = await api_client.post(
            "/companies/", json={"user_id": str(owner_ids[0]), **payload}
        )
    else:
        response = await api_client.patch(
            f"/companies/{saved_company.id}", json=payload
        )
    assert response.status_code == 422


# Each company endpoint returns a 500 response with the service's failure message.
@pytest.mark.parametrize(
    "method, path, service_method",
    [
        ("GET", "/companies/{id}", "get_company_by_id"),
        ("GET", "/companies/", "get_all_companies"),
        ("POST", "/companies/", "create_company"),
        ("PATCH", "/companies/{id}", "update_company"),
        ("DELETE", "/companies/{id}", "delete_company"),
    ],
)
async def test_company_service_failure_returns_500(
    api_client, owner_ids, monkeypatch, method, path, service_method
):
    failure = CompanyServiceError("Storage unavailable")
    mocked_operation = AsyncMock(side_effect=failure)
    monkeypatch.setattr(CompanyService, service_method, mocked_operation)
    if method == "POST":
        payload = {"user_id": str(owner_ids[0]), "name": "Example"}
    elif method == "PATCH":
        payload = {"name": "Updated"}
    else:
        payload = None
    response = await api_client.request(
        method,
        path.format(id=uuid4()),
        params={"user_id": str(owner_ids[0])},
        json=payload,
    )
    assert response.status_code == 500
    assert response.json() == {"detail": "Storage unavailable"}
    mocked_operation.assert_awaited_once()


# An unexpected programming error remains visible instead of becoming a handled company error.
async def test_company_api_does_not_swallow_programming_errors(api_client, monkeypatch):
    mocked_get = AsyncMock(side_effect=TypeError("Unexpected programming error"))
    monkeypatch.setattr(CompanyService, "get_company_by_id", mocked_get)
    with pytest.raises(TypeError, match="Unexpected programming error"):
        await api_client.get(f"/companies/{uuid4()}")
    mocked_get.assert_awaited_once()
