from uuid import UUID

import pytest
from sqlalchemy import func, select

from app.models import Company, Contact, TrackedRole, TrackedRoleEvent

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize(
    "path, payload",
    [
        ("/companies/", {"name": "Unauthorized"}),
        ("/contacts/", {"name": "Unauthorized"}),
        ("/tracked-roles/", {"title": "Unauthorized", "status": "saved"}),
        (
            "/events/",
            {
                "title": "Unauthorized",
                "event_type": "interview",
                "event_date": "2026-10-30",
                "status": "scheduled",
            },
        ),
    ],
)
async def test_resource_collections_require_authentication(
    anonymous_client, saved_role, path, payload
):
    response = await anonymous_client.get(
        path, params={"tracked_role_id": str(saved_role.id)}
    )
    assert response.status_code == 401
    if path == "/events/":
        payload = {**payload, "tracked_role_id": str(saved_role.id)}
    response = await anonymous_client.post(path, json=payload)
    assert response.status_code == 401


@pytest.mark.parametrize("method", ["GET", "PATCH", "DELETE"])
@pytest.mark.parametrize("path", ["companies", "contacts", "tracked-roles", "events"])
async def test_resource_details_require_authentication(
    anonymous_client,
    saved_company,
    saved_contact,
    saved_role,
    saved_event,
    path,
    method,
):
    resource = {
        "companies": saved_company,
        "contacts": saved_contact,
        "tracked-roles": saved_role,
        "events": saved_event,
    }[path]
    payload = {"notes": "Unauthorized"} if method == "PATCH" else None
    response = await anonymous_client.request(
        method, f"/{path}/{resource.id}", json=payload
    )
    assert response.status_code == 401


@pytest.mark.parametrize("method", ["GET", "PATCH", "DELETE"])
@pytest.mark.parametrize(
    "path, model, original_notes",
    [
        ("companies", Company, None),
        ("contacts", Contact, "Original notes"),
        ("tracked-roles", TrackedRole, "Original notes"),
        ("events", TrackedRoleEvent, "Original notes"),
    ],
)
async def test_other_users_cannot_read_change_or_delete_resources(
    client_factory,
    sessions,
    owner_ids,
    saved_company,
    saved_contact,
    saved_role,
    saved_event,
    path,
    model,
    original_notes,
    method,
):
    resource = {
        "companies": saved_company,
        "contacts": saved_contact,
        "tracked-roles": saved_role,
        "events": saved_event,
    }[path]
    payload = {"notes": "Unauthorized change"} if method == "PATCH" else None
    async with client_factory(owner_ids[1]) as other_client:
        response = await other_client.request(
            method, f"/{path}/{resource.id}", json=payload
        )
    assert response.status_code == 404
    async with sessions() as session:
        stored = await session.get(model, resource.id)
        assert stored is not None
        assert stored.notes == original_notes
        contact = await session.get(Contact, saved_contact.id)
        role = await session.get(TrackedRole, saved_role.id)
        event = await session.get(TrackedRoleEvent, saved_event.id)
        assert contact is not None
        assert role is not None
        assert event is not None
        assert contact.company_id == saved_company.id
        assert role.company_id == saved_company.id
        assert event.tracked_role_id == saved_role.id


@pytest.mark.parametrize(
    "path, model",
    [
        ("/companies/", Company),
        ("/contacts/", Contact),
        ("/tracked-roles/", TrackedRole),
    ],
)
async def test_list_ignores_spoofed_user_id(
    api_client,
    sessions,
    owner_ids,
    saved_company,
    saved_contact,
    saved_role,
    path,
    model,
):
    fields = {"user_id": owner_ids[1]}
    if model is TrackedRole:
        fields.update(title="Other role", status="saved")
    else:
        fields["name"] = "Other record"
    async with sessions.begin() as session:
        foreign = model(**fields)
        session.add(foreign)
    response = await api_client.get(path, params={"user_id": str(owner_ids[1])})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["user_id"] == str(owner_ids[0])
    assert data[0]["id"] != str(foreign.id)


@pytest.mark.parametrize(
    "path, model, payload",
    [
        ("/companies/", Company, {"name": "New company"}),
        ("/contacts/", Contact, {"name": "New contact"}),
        (
            "/tracked-roles/",
            TrackedRole,
            {"title": "New role", "status": "saved"},
        ),
    ],
)
async def test_create_uses_authenticated_owner_without_body_user_id(
    api_client, sessions, owner_ids, path, model, payload
):
    response = await api_client.post(path, json=payload)
    assert response.status_code == 201
    assert response.json()["user_id"] == str(owner_ids[0])
    async with sessions() as session:
        stored = await session.get(model, UUID(response.json()["id"]))
        assert stored is not None
        assert stored.user_id == owner_ids[0]


@pytest.mark.parametrize(
    "path, model, payload",
    [
        ("/companies/", Company, {"name": "Forged company"}),
        ("/contacts/", Contact, {"name": "Forged contact"}),
        (
            "/tracked-roles/",
            TrackedRole,
            {"title": "Forged role", "status": "saved"},
        ),
    ],
)
async def test_create_rejects_foreign_body_user_id_without_saving(
    api_client, sessions, owner_ids, path, model, payload
):
    response = await api_client.post(
        path, json={**payload, "user_id": str(owner_ids[1])}
    )
    assert response.status_code == 403
    async with sessions() as session:
        count = await session.scalar(
            select(func.count()).select_from(model).where(model.user_id.in_(owner_ids))
        )
        assert count == 0


async def test_events_cannot_be_listed_or_created_under_another_users_role(
    client_factory, sessions, owner_ids, saved_role, saved_event
):
    async with client_factory(owner_ids[1]) as other_client:
        response = await other_client.get(
            "/events/", params={"tracked_role_id": str(saved_role.id)}
        )
        assert response.status_code == 404
        response = await other_client.post(
            "/events/",
            json={
                "tracked_role_id": str(saved_role.id),
                "title": "Unauthorized event",
                "event_type": "interview",
                "event_date": "2026-10-30",
                "status": "scheduled",
            },
        )
        assert response.status_code == 404
    async with sessions() as session:
        events = list(
            await session.scalars(
                select(TrackedRoleEvent).where(
                    TrackedRoleEvent.tracked_role_id == saved_role.id
                )
            )
        )
        assert [event.id for event in events] == [saved_event.id]
        assert events[0].title == "Phone screen"
