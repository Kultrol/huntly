from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.event import EventService
from app.services.exceptions.event import EventServiceError

pytestmark = pytest.mark.anyio


# Listing events for an opportunity that does not exist returns 404.
async def test_event_list_for_missing_role_returns_404(api_client):
    response = await api_client.get(
        "/events/", params={"tracked_role_id": str(uuid4())}
    )
    assert response.status_code == 404


# Creating an event for an opportunity that does not exist returns 404.
async def test_event_create_for_missing_role_returns_404(api_client):
    response = await api_client.post(
        "/events/",
        json={
            "tracked_role_id": str(uuid4()),
            "title": "Missing parent",
            "event_type": "interview",
            "event_date": "2026-10-20",
            "status": "scheduled",
        },
    )
    assert response.status_code == 404


# An unknown event ID returns 404, while an ID in the wrong format returns 422.
@pytest.mark.parametrize("method", ["GET", "PATCH", "DELETE"])
async def test_event_missing_and_invalid_ids(api_client, method):
    payload = {"title": "Missing"} if method == "PATCH" else None
    response = await api_client.request(method, f"/events/{uuid4()}", json=payload)
    assert response.status_code == 404
    response = await api_client.request(
        method,
        "/events/not-a-uuid",
        json=payload,
    )
    assert response.status_code == 422


# Invalid event fields are rejected before the saved activity is changed.
@pytest.mark.parametrize(
    "patch",
    [
        {"status": None},
        {"title": " "},
        {"event_date": "invalid"},
        {"event_type": "unknown"},
    ],
)
async def test_event_invalid_patch_returns_422(api_client, saved_event, patch):
    response = await api_client.patch(f"/events/{saved_event.id}", json=patch)
    assert response.status_code == 422


# An event status change rejects a date that is not a valid date and time.
async def test_event_occurred_at_must_be_valid_query_datetime(api_client, saved_event):
    response = await api_client.patch(
        f"/events/{saved_event.id}",
        params={"occurred_at": "invalid"},
        json={"status": "completed"},
    )
    assert response.status_code == 422


# Each event endpoint returns a 500 response with the service's failure message.
@pytest.mark.parametrize(
    "method, path, service_method",
    [
        ("GET", "/events/{id}", "get_event"),
        ("GET", "/events/", "get_all_events"),
        ("POST", "/events/", "create_event"),
        ("PATCH", "/events/{id}", "update_event"),
        ("DELETE", "/events/{id}", "delete_event"),
    ],
)
async def test_event_service_failure_returns_500(
    api_client, owner_ids, monkeypatch, method, path, service_method
):
    failure = EventServiceError("Storage unavailable")
    mocked_operation = AsyncMock(side_effect=failure)
    monkeypatch.setattr(EventService, service_method, mocked_operation)
    if method == "POST":
        payload = {
            "tracked_role_id": str(uuid4()),
            "title": "Interview",
            "event_date": "2026-01-01",
            "event_type": "interview",
            "status": "pending",
        }
    elif method == "PATCH":
        payload = {"title": "Updated"}
    else:
        payload = None
    response = await api_client.request(
        method,
        path.format(id=uuid4()),
        params={"tracked_role_id": str(uuid4())},
        json=payload,
    )
    assert response.status_code == 500
    assert response.json() == {"detail": "Storage unavailable"}
    mocked_operation.assert_awaited_once()


# An unexpected programming error remains visible instead of becoming a handled event error.
async def test_event_api_does_not_swallow_programming_errors(api_client, monkeypatch):
    mocked_get = AsyncMock(side_effect=TypeError("Unexpected programming error"))
    monkeypatch.setattr(EventService, "get_event", mocked_get)
    with pytest.raises(TypeError, match="Unexpected programming error"):
        await api_client.get(f"/events/{uuid4()}")
    mocked_get.assert_awaited_once()
