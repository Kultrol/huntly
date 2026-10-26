from datetime import datetime
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import select

from app.models import (
    Contact,
    EventStatusHistory,
    StatusHistory,
    TrackedRole,
    TrackedRoleContact,
    TrackedRoleEvent,
)

pytestmark = pytest.mark.anyio


# Creating an opportunity saves its salary and records its starting status at the supplied
# time.
async def test_role_create_saves_salary_and_initial_history(
    api_client, sessions, owner_ids
):
    occurred_at = datetime.fromisoformat("2026-01-01T10:00:00+00:00")
    response = await api_client.post(
        "/tracked-roles/",
        params={"occurred_at": occurred_at.isoformat()},
        json={
            "user_id": str(owner_ids[0]),
            "title": "Backend Developer",
            "status": "saved",
            "salary_min": "80000.50",
        },
    )
    assert response.status_code == 201
    data = response.json()
    role_id = UUID(data["id"])
    assert data["salary_min"] == "80000.50"
    assert data["title"] == "Backend Developer"
    assert data["user_id"] == str(owner_ids[0])
    assert data["status"] == "saved"
    async with sessions() as session:
        role = await session.get(TrackedRole, role_id)
        assert role is not None
        assert role.title == "Backend Developer"
        assert role.salary_min == Decimal("80000.50")
        assert role.status == "saved"
        history = list(
            await session.scalars(
                select(StatusHistory).where(StatusHistory.tracked_role_id == role_id)
            )
        )
        assert len(history) == 1
        assert history[0].from_status is None
        assert history[0].to_status == "saved"
        assert history[0].occurred_at == occurred_at


# Marking an opportunity as applied saves the application date and adds one status change.
async def test_role_patch_saves_application_date_and_changed_status_history(
    api_client, sessions, saved_role
):
    occurred_at = datetime.fromisoformat("2026-02-01T10:00:00+00:00")
    response = await api_client.patch(
        f"/tracked-roles/{saved_role.id}",
        params={"occurred_at": occurred_at.isoformat()},
        json={"status": "applied"},
    )
    assert response.status_code == 200
    assert datetime.fromisoformat(response.json()["applied_at"]) == occurred_at
    assert response.json()["status"] == "applied"
    async with sessions() as session:
        role = await session.get(TrackedRole, saved_role.id)
        assert role is not None
        assert role.status == "applied"
        assert role.applied_at == occurred_at
        assert role.title == "Backend Developer"
        history = list(
            await session.scalars(
                select(StatusHistory).where(StatusHistory.tracked_role_id == role.id)
            )
        )
        assert len(history) == 2
        initial = next(row for row in history if row.from_status is None)
        changed = next(row for row in history if row.from_status is not None)
        assert initial.to_status == "saved"
        assert changed.from_status == "saved"
        assert changed.to_status == "applied"
        assert changed.occurred_at == occurred_at


# Deleting an opportunity removes its activity and links while keeping the contact.
async def test_role_delete_removes_dependent_activity(
    api_client, sessions, saved_role, saved_event, saved_contact
):
    async with sessions.begin() as session:
        link = TrackedRoleContact(
            tracked_role_id=saved_role.id, contact_id=saved_contact.id
        )
        session.add(link)
    response = await api_client.delete(f"/tracked-roles/{saved_role.id}")
    assert response.status_code == 204
    assert response.content == b""
    async with sessions() as session:
        assert await session.get(TrackedRole, saved_role.id) is None
        assert await session.get(TrackedRoleEvent, saved_event.id) is None
        assert await session.get(TrackedRoleContact, link.id) is None
        history = list(
            await session.scalars(
                select(StatusHistory).where(
                    StatusHistory.tracked_role_id == saved_role.id
                )
            )
        )
        event_history = list(
            await session.scalars(
                select(EventStatusHistory).where(
                    EventStatusHistory.event_id == saved_event.id
                )
            )
        )
        assert history == []
        assert event_history == []
        assert await session.get(Contact, saved_contact.id) is not None
