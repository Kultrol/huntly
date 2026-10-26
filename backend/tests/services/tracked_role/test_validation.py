from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.enums import TrackedRoleStatus
from app.models import (
    Company,
    TrackedRole,
)
from app.schemas.tracked_role import TrackedRoleCreate, TrackedRoleUpdate
from app.services.exceptions.tracked_role import (
    TrackedRoleCompanyError,
)
from app.services.tracked_role import TrackedRoleService

pytestmark = pytest.mark.anyio


# A one-sided salary patch must remain compatible with the other stored bound.
@pytest.mark.parametrize("patch", [{"salary_min": 110000}, {"salary_max": 70000}])
async def test_role_partial_salary_update_rejects_inverted_stored_range(
    sessions, saved_role, patch
):
    async with sessions() as session:
        with pytest.raises(ValidationError):
            await TrackedRoleService(session).update_tracked_role(
                saved_role.id, TrackedRoleUpdate.model_validate(patch)
            )
        await session.rollback()
    async with sessions() as session:
        found = await session.get(TrackedRole, saved_role.id)
        assert found is not None
        assert found.salary_min == Decimal(80000)
        assert found.salary_max == Decimal(100000)


# Explicit nulls must clear requested role details and preserve omitted salary bounds.
async def test_role_update_clears_nullable_fields(sessions, saved_role):
    async with sessions() as session:
        await TrackedRoleService(session).update_tracked_role(
            saved_role.id,
            TrackedRoleUpdate(company_id=None, notes=None, salary_min=None),
        )
        await session.commit()
    async with sessions() as session:
        found = await session.get(TrackedRole, saved_role.id)
        assert found is not None
        assert found.company_id is None
        assert found.notes is None
        assert found.salary_min is None
        assert found.salary_max == Decimal(100000)


# A role cannot link to a missing company or another owner's company.
@pytest.mark.parametrize("operation", ["create", "update"])
@pytest.mark.parametrize("company_exists", [True, False])
async def test_role_rejects_missing_or_other_owners_company(
    sessions, owner_ids, saved_role, operation, company_exists
):
    company_id = uuid4()
    if company_exists:
        async with sessions.begin() as session:
            session.add(
                Company(id=company_id, user_id=owner_ids[1], name="Other company")
            )
    async with sessions() as session:
        service = TrackedRoleService(session)
        with pytest.raises(TrackedRoleCompanyError):
            if operation == "create":
                await service.create_tracked_role(
                    TrackedRoleCreate(
                        user_id=owner_ids[0],
                        title="Rejected",
                        status=TrackedRoleStatus.SAVED,
                        company_id=company_id,
                    )
                )
            else:
                await service.update_tracked_role(
                    saved_role.id, TrackedRoleUpdate(company_id=company_id)
                )
        await session.rollback()
    async with sessions() as session:
        roles = list(
            await session.scalars(
                select(TrackedRole).where(TrackedRole.user_id == owner_ids[0])
            )
        )
        assert [role.id for role in roles] == [saved_role.id]
        assert roles[0].company_id == saved_role.company_id
