"""Event endpoints with request-owned transactions.

Event changes and history entries share a transaction. These routes do not authenticate
callers or check ownership.
"""

from datetime import datetime
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

from app.core.database import get_db
from app.models.tracked_role.event import TrackedRoleEvent
from app.schemas.event import EventCreate, EventRead, EventUpdate
from app.services.event import EventService
from app.services.exceptions.event import EventNotFoundError, EventServiceError
from app.services.exceptions.tracked_role import TrackedRoleNotFoundError

router: APIRouter = APIRouter(prefix="/events", tags=["events"])


@router.get("/", response_model=list[EventRead])
async def get_events(
    tracked_role_id: UUID, db: AsyncSession = Depends(get_db)
) -> list[TrackedRoleEvent]:
    """List an existing role's events without guaranteed ordering."""
    async with db.begin():
        event_service: EventService = EventService(db)
        try:
            return await event_service.get_all_events(tracked_role_id)
        except TrackedRoleNotFoundError as exc:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND, detail=str(exc)
            ) from exc
        except EventServiceError as exc:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
            ) from exc


@router.get("/{id}", response_model=EventRead)
async def get_event(id: UUID, db: AsyncSession = Depends(get_db)) -> TrackedRoleEvent:
    """Retrieve an event by UUID."""
    async with db.begin():
        event_service: EventService = EventService(db)
        try:
            return await event_service.get_event(id)
        except EventNotFoundError as exc:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND, detail=str(exc)
            ) from exc
        except EventServiceError as exc:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
            ) from exc


@router.post("/", response_model=EventRead, status_code=HTTP_201_CREATED)
async def create_event(
    new_event: EventCreate,
    db: AsyncSession = Depends(get_db),
    occurred_at: datetime | None = None,
) -> TrackedRoleEvent:
    """Create an event and its initial status-history entry.

    The optional occurred_at query parameter timestamps history independently of the
    scheduled activity; it defaults to the current UTC time.
    """
    async with db.begin():
        event_service: EventService = EventService(db)
        try:
            return await event_service.create_event(new_event, occurred_at=occurred_at)
        except TrackedRoleNotFoundError as exc:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND, detail=str(exc)
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
        except EventServiceError as exc:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
            ) from exc


@router.patch("/{id}", response_model=EventRead)
async def update_event(
    id: UUID,
    event_data: EventUpdate,
    db: AsyncSession = Depends(get_db),
    occurred_at: datetime | None = None,
) -> TrackedRoleEvent:
    """Apply supplied changes and record actual status transitions.

    Omitted fields remain unchanged; the resulting type and custom label must be valid
    together. The optional occurred_at query parameter timestamps a new transition and
    defaults to the current UTC time.
    """
    async with db.begin():
        event_service: EventService = EventService(db)
        try:
            return await event_service.update_event(
                id, event_data, occurred_at=occurred_at
            )
        except EventNotFoundError as exc:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND, detail=str(exc)
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc
        except EventServiceError as exc:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
            ) from exc


@router.delete("/{id}", status_code=HTTP_204_NO_CONTENT, response_class=Response)
async def delete_event(id: UUID, db: AsyncSession = Depends(get_db)) -> Response:
    """Delete an event and its status history while retaining its parent role."""
    async with db.begin():
        event_service: EventService = EventService(db)
        try:
            await event_service.delete_event(id)
            return Response(status_code=HTTP_204_NO_CONTENT)
        except EventNotFoundError as exc:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND, detail=str(exc)
            ) from exc
        except EventServiceError as exc:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
            ) from exc
