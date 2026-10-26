from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.enums import TrackedRoleStatus
from app.models import (
    StatusHistory,
    TrackedRole,
)
from app.schemas.tracked_role import TrackedRoleCreate, TrackedRoleUpdate
from app.services.tracked_role import TrackedRoleService

pytestmark = pytest.mark.anyio


# Creating a role must record its initial status and infer application dates only when
# needed.
@pytest.mark.parametrize(
    "status, applied_at, occurred_at, expected_applied_at",
    [
        ("saved", None, datetime(2026, 1, 2, tzinfo=UTC), None),
        (
            "applied",
            None,
            datetime(2026, 1, 2, tzinfo=UTC),
            datetime(2026, 1, 2, tzinfo=UTC),
        ),
        (
            "applied",
            datetime(2026, 1, 1, tzinfo=UTC),
            None,
            datetime(2026, 1, 1, tzinfo=UTC),
        ),
        (
            "applied",
            datetime(2026, 1, 1, tzinfo=UTC),
            datetime(2026, 1, 2, tzinfo=UTC),
            datetime(2026, 1, 1, tzinfo=UTC),
        ),
    ],
)
async def test_role_creation_records_initial_status_and_application_date(
    sessions, owner_ids, status, applied_at, occurred_at, expected_applied_at
):
    data = TrackedRoleCreate.model_validate(
        {
            "user_id": owner_ids[0],
            "title": "  Backend   Developer ",
            "status": status,
            "applied_at": applied_at,
            "salary_min": "80000.50",
            "salary_max": "100000",
        }
    )
    async with sessions() as session:
        role = await TrackedRoleService(session).create_tracked_role(
            data, occurred_at=occurred_at
        )
        await session.commit()
    async with sessions() as session:
        found = await session.get(TrackedRole, role.id)
        assert found is not None
        assert found.title == "Backend Developer"
        assert found.user_id == owner_ids[0]
        assert found.salary_min == Decimal("80000.50")
        assert found.salary_max == Decimal(100000)
        assert found.applied_at == expected_applied_at
        history = list(
            await session.scalars(
                select(StatusHistory).where(StatusHistory.tracked_role_id == role.id)
            )
        )
        assert len(history) == 1
        assert history[0].from_status is None
        assert history[0].to_status == status
        assert history[0].occurred_at == (occurred_at or applied_at)
        assert history[0].created_at > history[0].occurred_at


# Only a changed role status must append history and infer a first application date.
@pytest.mark.parametrize(
    "patch, expected_status, expected_history_count",
    [
        ({"status": "applied"}, "applied", 2),
        ({"status": "saved"}, "saved", 1),
        ({"title": "Software Engineer"}, "saved", 1),
        ({}, "saved", 1),
    ],
)
async def test_role_update_only_records_changed_status(
    sessions, saved_role, patch, expected_status, expected_history_count
):
    occurred_at = datetime(2026, 2, 1, tzinfo=UTC)
    async with sessions() as session:
        await TrackedRoleService(session).update_tracked_role(
            saved_role.id,
            TrackedRoleUpdate.model_validate(patch),
            occurred_at=occurred_at,
        )
        await session.commit()
    async with sessions() as session:
        role = await session.get(TrackedRole, saved_role.id)
        assert role is not None
        assert role.status == expected_status
        assert role.title == patch.get("title", "Backend Developer")
        assert role.notes == "Original notes"
        history = list(
            await session.scalars(
                select(StatusHistory).where(StatusHistory.tracked_role_id == role.id)
            )
        )
        assert len(history) == expected_history_count
        if expected_status == "applied":
            changed = next(row for row in history if row.from_status is not None)
            assert changed.from_status == TrackedRoleStatus.SAVED
            assert changed.to_status == TrackedRoleStatus.APPLIED
            assert changed.occurred_at == occurred_at
            assert role.applied_at == occurred_at


# Returning to applied after clearing its date must preserve that deliberate absence.
async def test_reentering_applied_does_not_recreate_cleared_application_date(
    sessions, saved_role
):
    async with sessions() as session:
        service = TrackedRoleService(session)
        await service.update_tracked_role(
            saved_role.id, TrackedRoleUpdate(status=TrackedRoleStatus.APPLIED)
        )
        await session.commit()
    async with sessions() as session:
        await TrackedRoleService(session).update_tracked_role(
            saved_role.id,
            TrackedRoleUpdate(status=TrackedRoleStatus.SAVED, applied_at=None),
        )
        await session.commit()
    async with sessions() as session:
        await TrackedRoleService(session).update_tracked_role(
            saved_role.id, TrackedRoleUpdate(status=TrackedRoleStatus.APPLIED)
        )
        await session.commit()
    async with sessions() as session:
        role = await session.get(TrackedRole, saved_role.id)
        assert role is not None
        assert role.status == TrackedRoleStatus.APPLIED
        assert role.applied_at is None
        history = list(
            await session.scalars(
                select(StatusHistory).where(StatusHistory.tracked_role_id == role.id)
            )
        )
        assert len(history) == 4
        assert sum(row.to_status == TrackedRoleStatus.APPLIED for row in history) == 2
