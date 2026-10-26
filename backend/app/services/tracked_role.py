from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.engine import ScalarResult
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import TrackedRoleStatus
from app.models.company import Company
from app.models.tracked_role.status_history import StatusHistory
from app.models.tracked_role.tracked_role import TrackedRole
from app.schemas.tracked_role import TrackedRoleCreate, TrackedRoleUpdate
from app.services.exceptions.tracked_role import (
    TrackedRoleCompanyError,
    TrackedRoleCreationError,
    TrackedRoleDeletionError,
    TrackedRoleFetchingError,
    TrackedRoleNotFoundError,
    TrackedRoleUpdateError,
)
from app.services.user import UserService


class TrackedRoleService:
    """Manage tracked roles and their status histories.

    Mutations flush without committing; the caller owns commit and rollback. ID-based
    operations do not authorize access.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db: AsyncSession = db

    async def get_tracked_role_by_id(self, id: UUID) -> TrackedRole:
        """Fetch a role by ID without checking ownership.

        Raise TrackedRoleNotFoundError if absent.
        """
        try:
            tracked_role: TrackedRole | None = await self.db.get(TrackedRole, id)
            if tracked_role is None:
                raise TrackedRoleNotFoundError(f"Tracked role with id {id} not found.")
            return tracked_role
        except SQLAlchemyError as exc:
            raise TrackedRoleFetchingError(f"Failed to get tracked role: {id}") from exc

    async def get_all_tracked_roles(self, user_id: UUID) -> list[TrackedRole]:
        """List an existing user's roles without guaranteed ordering."""
        await UserService(db=self.db).get_user(user_id)
        try:
            stmt: Select[tuple[TrackedRole]] = select(TrackedRole).where(
                TrackedRole.user_id == user_id
            )
            tracked_roles: ScalarResult[TrackedRole] = await self.db.scalars(stmt)
            return list(tracked_roles)
        except SQLAlchemyError as exc:
            raise TrackedRoleFetchingError("Failed to get tracked roles") from exc

    async def create_tracked_role(
        self,
        new_tracked_role_data: TrackedRoleCreate,
        *,
        occurred_at: datetime | None = None,
    ) -> TrackedRole:
        """Create a role and its initial history entry in the caller's transaction.

        The owner must exist, and any linked company must share that owner. History uses
        occurred_at, then applied_at for an APPLIED role, then the current UTC time. An
        APPLIED role missing applied_at receives that effective time; a supplied
        application date is retained.
        """
        await UserService(db=self.db).get_user(new_tracked_role_data.user_id)
        try:
            if new_tracked_role_data.company_id is not None:
                stmt: Select[tuple[Company]] = select(Company).where(
                    Company.id == new_tracked_role_data.company_id,
                    Company.user_id == new_tracked_role_data.user_id,
                )
                company: Company | None = await self.db.scalar(stmt)
                if company is None:
                    raise TrackedRoleCompanyError(
                        "The company must exist and belong to the tracked role's user."
                    )

            tracked_role: TrackedRole = TrackedRole(
                **new_tracked_role_data.model_dump()
            )
            effective_time: datetime | None = occurred_at
            if effective_time is None:
                if tracked_role.status == TrackedRoleStatus.APPLIED:
                    effective_time = tracked_role.applied_at
                if effective_time is None:
                    effective_time = datetime.now(UTC)

            if (
                tracked_role.status == TrackedRoleStatus.APPLIED
                and tracked_role.applied_at is None
            ):
                tracked_role.applied_at = effective_time

            self.db.add(tracked_role)
            await self.db.flush()

            history: StatusHistory = StatusHistory(
                tracked_role_id=tracked_role.id,
                from_status=None,
                to_status=tracked_role.status,
                occurred_at=effective_time,
            )
            self.db.add(history)
            await self.db.flush()
            return tracked_role
        except SQLAlchemyError as exc:
            raise TrackedRoleCreationError("Failed to create tracked role") from exc

    async def update_tracked_role(
        self,
        id: UUID,
        tracked_role_data: TrackedRoleUpdate,
        *,
        occurred_at: datetime | None = None,
    ) -> TrackedRole:
        """Apply a patch validated against the complete resulting role.

        Omitted fields remain unchanged; explicit null clears nullable fields. Salary
        bounds must remain compatible, and any replacement company must share the owner.

        Only actual status changes append history, using occurred_at or the current UTC
        time. The first APPLIED transition fills a missing applied_at only if the patch
        omits it. Prior APPLIED history prevents reentry from recreating a cleared date.
        """
        tracked_role: TrackedRole = await self.get_tracked_role_by_id(id)
        try:
            updated_data: dict[str, Any] = tracked_role_data.model_dump(
                exclude_unset=True
            )

            # A patch may supply only one salary bound; it must remain compatible
            # with the bound already stored on the role.
            current_data: dict[str, Any] = TrackedRoleCreate.model_validate(
                tracked_role
            ).model_dump()
            current_data.update(updated_data)
            TrackedRoleCreate.model_validate(current_data)

            if updated_data.get("company_id") is not None:
                stmt: Select[tuple[Company]] = select(Company).where(
                    Company.id == updated_data["company_id"],
                    Company.user_id == tracked_role.user_id,
                )
                company: Company | None = await self.db.scalar(stmt)
                if company is None:
                    raise TrackedRoleCompanyError(
                        "The company must exist and belong to the tracked role's user."
                    )

            previous_status: TrackedRoleStatus = tracked_role.status
            new_status: TrackedRoleStatus = updated_data.get("status", previous_status)
            effective_time: datetime = occurred_at or datetime.now(UTC)

            if (
                new_status != previous_status
                and new_status == TrackedRoleStatus.APPLIED
                and "applied_at" not in updated_data
                and tracked_role.applied_at is None
            ):
                # History distinguishes a first application from a later reentry,
                # even if the user previously cleared the application date.
                previous_application: UUID | None = await self.db.scalar(
                    select(StatusHistory.id)
                    .where(
                        StatusHistory.tracked_role_id == tracked_role.id,
                        StatusHistory.to_status == TrackedRoleStatus.APPLIED,
                    )
                    .limit(1)
                )
                if previous_application is None:
                    updated_data["applied_at"] = effective_time

            for field, value in updated_data.items():
                setattr(tracked_role, field, value)

            if new_status != previous_status:
                history: StatusHistory = StatusHistory(
                    tracked_role_id=tracked_role.id,
                    from_status=previous_status,
                    to_status=new_status,
                    occurred_at=effective_time,
                )
                self.db.add(history)

            await self.db.flush()
            await self.db.refresh(tracked_role)
            return tracked_role
        except SQLAlchemyError as exc:
            raise TrackedRoleUpdateError(
                f"Failed to update tracked role: {id}"
            ) from exc

    async def delete_tracked_role(self, id: UUID) -> None:
        """Delete a role and its dependent history, events, event history, and contact
        links.

        The company and contacts remain independent records.
        """
        tracked_role: TrackedRole = await self.get_tracked_role_by_id(id)
        try:
            await self.db.delete(tracked_role)
            await self.db.flush()
        except SQLAlchemyError as exc:
            raise TrackedRoleDeletionError(
                f"Failed to delete tracked role: {id}"
            ) from exc
