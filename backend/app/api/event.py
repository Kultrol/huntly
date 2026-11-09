"""Authenticated event endpoints authorize access through the parent role."""

from datetime import date, datetime
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

from app.api.ownership import require_owned_event, require_owned_resource
from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.tracked_role.event import TrackedRoleEvent
from app.models.tracked_role.tracked_role import TrackedRole
from app.models.user import User
from app.schemas.event import EventCreate, EventRead, EventUpdate, UpcomingEventsRead
from app.services.event import EventService
from app.services.exceptions.event import EventNotFoundError, EventServiceError
from app.services.exceptions.tracked_role import TrackedRoleNotFoundError

router: APIRouter = APIRouter(prefix="/events", tags=["events"])


@router.get("/", response_model=list[EventRead])
async def get_events(
    tracked_role_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[TrackedRoleEvent]:
    """List a role's events after verifying that the signed-in user owns the role."""
    async with db.begin():
        await require_owned_resource(db, TrackedRole, tracked_role_id, current_user.id)
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


@router.get("/upcoming", response_model=UpcomingEventsRead)
async def get_upcoming_events(
    from_date: date,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> UpcomingEventsRead:
    """List the signed-in user's next five interviews, deadlines, and follow-ups."""
    async with db.begin():
        try:
            events = await EventService(db).get_upcoming_events(
                current_user.id, from_date
            )
        except EventServiceError as exc:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
            ) from exc
        return UpcomingEventsRead.model_validate(
            {"user_id": current_user.id, "events": events}
        )


@router.get("/{id}", response_model=EventRead)
async def get_event(
    id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TrackedRoleEvent:
    """Retrieve an event after checking ownership through its parent role."""
    async with db.begin():
        await require_owned_event(db, id, current_user.id)
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
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    occurred_at: datetime | None = None,
) -> TrackedRoleEvent:
    """Create an event and its initial history for a role the signed-in user owns.

    The optional occurred_at query parameter timestamps history independently of the
    scheduled activity; it defaults to the current UTC time.
    """
    async with db.begin():
        await require_owned_resource(
            db, TrackedRole, new_event.tracked_role_id, current_user.id
        )
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
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    occurred_at: datetime | None = None,
) -> TrackedRoleEvent:
    """Apply supplied changes and record actual status transitions.

    Omitted fields remain unchanged; the resulting type and custom label must be valid
    together. The optional occurred_at query parameter timestamps a new transition and
    defaults to the current UTC time.
    """
    async with db.begin():
        await require_owned_event(db, id, current_user.id)
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
async def delete_event(
    id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    """Delete an event and its status history while retaining its parent role."""
    async with db.begin():
        await require_owned_event(db, id, current_user.id)
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
