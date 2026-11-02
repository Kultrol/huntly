"""Authenticated tracked-role endpoints with owner-scoped access."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import (
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from app.api.ownership import require_owned_resource, validate_supplied_owner
from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.tracked_role.tracked_role import TrackedRole
from app.models.user import User
from app.schemas.resource_requests import TrackedRoleCreateRequest
from app.schemas.tracked_role import (
    TrackedRoleCreate,
    TrackedRoleRead,
    TrackedRoleUpdate,
)
from app.services.exceptions.tracked_role import (
    TrackedRoleCompanyError,
    TrackedRoleNotFoundError,
    TrackedRoleServiceError,
)
from app.services.exceptions.user import UserNotFoundError, UserServiceError
from app.services.tracked_role import TrackedRoleService

router: APIRouter = APIRouter(prefix="/tracked-roles", tags=["tracked roles"])


@router.get("/", response_model=list[TrackedRoleRead])
async def get_tracked_roles(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[TrackedRole]:
    """List the signed-in user's tracked roles without guaranteed ordering."""
    async with db.begin():
        tracked_role_service: TrackedRoleService = TrackedRoleService(db)
        try:
            return await tracked_role_service.get_all_tracked_roles(current_user.id)
        except UserNotFoundError as exc:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND, detail=str(exc)
            ) from exc
        except (TrackedRoleServiceError, UserServiceError) as exc:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
            ) from exc


@router.get("/{id}", response_model=TrackedRoleRead)
async def get_tracked_role(
    id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TrackedRole:
    """Retrieve a tracked role after checking the signed-in user's ownership."""
    async with db.begin():
        await require_owned_resource(db, TrackedRole, id, current_user.id)
        tracked_role_service: TrackedRoleService = TrackedRoleService(db)
        try:
            return await tracked_role_service.get_tracked_role_by_id(id)
        except TrackedRoleNotFoundError as exc:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND, detail=str(exc)
            ) from exc
        except TrackedRoleServiceError as exc:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
            ) from exc


@router.post("/", response_model=TrackedRoleRead, status_code=HTTP_201_CREATED)
async def create_tracked_role(
    new_tracked_role: TrackedRoleCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    occurred_at: datetime | None = None,
) -> TrackedRole:
    """Create a tracked role for the signed-in user and its initial history entry.

    Any linked company must share the owner. History uses the optional occurred_at query
    parameter, then applied_at for an applied role, then the current UTC time.
    """
    validate_supplied_owner(new_tracked_role.user_id, current_user.id)
    service_data = new_tracked_role.model_dump()
    service_data["user_id"] = current_user.id
    service_input = TrackedRoleCreate.model_validate(service_data)
    async with db.begin():
        tracked_role_service: TrackedRoleService = TrackedRoleService(db)
        try:
            return await tracked_role_service.create_tracked_role(
                service_input, occurred_at=occurred_at
            )
        except UserNotFoundError as exc:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND, detail=str(exc)
            ) from exc
        except TrackedRoleCompanyError as exc:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
        except (TrackedRoleServiceError, UserServiceError) as exc:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
            ) from exc


@router.patch("/{id}", response_model=TrackedRoleRead)
async def update_tracked_role(
    id: UUID,
    tracked_role_data: TrackedRoleUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    occurred_at: datetime | None = None,
) -> TrackedRole:
    """Apply supplied changes and record actual status transitions.

    Omitted fields remain unchanged. Salary bounds are validated together; the first
    applied transition can fill a missing application date. The optional occurred_at
    query parameter timestamps a new transition and defaults to the current UTC time.
    """
    async with db.begin():
        await require_owned_resource(db, TrackedRole, id, current_user.id)
        tracked_role_service: TrackedRoleService = TrackedRoleService(db)
        try:
            return await tracked_role_service.update_tracked_role(
                id, tracked_role_data, occurred_at=occurred_at
            )
        except TrackedRoleNotFoundError as exc:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND, detail=str(exc)
            ) from exc
        except TrackedRoleCompanyError as exc:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
        except TrackedRoleServiceError as exc:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
            ) from exc


@router.delete("/{id}", status_code=HTTP_204_NO_CONTENT, response_class=Response)
async def delete_tracked_role(
    id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    """Delete a role, its history, events, event history, and contact associations."""
    async with db.begin():
        await require_owned_resource(db, TrackedRole, id, current_user.id)
        tracked_role_service: TrackedRoleService = TrackedRoleService(db)
        try:
            await tracked_role_service.delete_tracked_role(id)
            return Response(status_code=HTTP_204_NO_CONTENT)
        except TrackedRoleNotFoundError as exc:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND, detail=str(exc)
            ) from exc
        except TrackedRoleServiceError as exc:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
            ) from exc
