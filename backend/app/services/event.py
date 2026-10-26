from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.engine import ScalarResult
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import EventStatus
from app.models.tracked_role.event import TrackedRoleEvent
from app.models.tracked_role.event_status_history import EventStatusHistory
from app.models.tracked_role.tracked_role import TrackedRole
from app.schemas.event import EventCreate, EventUpdate
from app.services.exceptions.event import (
    EventCreationError,
    EventDeletionError,
    EventFetchingError,
    EventNotFoundError,
    EventUpdateError,
)
from app.services.exceptions.tracked_role import TrackedRoleNotFoundError


class EventService:
    """Manage role events and their status histories.

    Mutations flush without committing; the caller owns commit and rollback. Events
    inherit ownership from their role, but these methods do not authorize access.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db: AsyncSession = db

    async def get_event(self, event_id: UUID) -> TrackedRoleEvent:
        """Fetch an event by ID; raise EventNotFoundError if absent."""
        try:
            event: TrackedRoleEvent | None = await self.db.get(
                TrackedRoleEvent, event_id
            )
            if event is None:
                raise EventNotFoundError(f"Event with id {event_id} not found.")
            return event
        except SQLAlchemyError as exc:
            raise EventFetchingError(f"Failed to get event: {event_id}") from exc

    async def get_all_events(self, tracked_role_id: UUID) -> list[TrackedRoleEvent]:
        """List an existing role's events without guaranteed ordering.

        A missing parent raises TrackedRoleNotFoundError; an existing role can have no
        events.
        """
        try:
            tracked_role: TrackedRole | None = await self.db.get(
                TrackedRole, tracked_role_id
            )
            if tracked_role is None:
                raise TrackedRoleNotFoundError(
                    f"Tracked role with id {tracked_role_id} not found."
                )
            stmt: Select[tuple[TrackedRoleEvent]] = select(TrackedRoleEvent).where(
                TrackedRoleEvent.tracked_role_id == tracked_role_id
            )
            events: ScalarResult[TrackedRoleEvent] = await self.db.scalars(stmt)
            return list(events)
        except SQLAlchemyError as exc:
            raise EventFetchingError("Failed to get events") from exc

    async def create_event(
        self,
        new_event: EventCreate,
        *,
        occurred_at: datetime | None = None,
    ) -> TrackedRoleEvent:
        """Create an event and its initial history entry in the caller's transaction.

        The initial from_status is null. occurred_at timestamps history independently of
        the scheduled activity and defaults to the current UTC time. The caller must
        authorize the parent role.
        """
        try:
            tracked_role: TrackedRole | None = await self.db.get(
                TrackedRole, new_event.tracked_role_id
            )
            if tracked_role is None:
                raise TrackedRoleNotFoundError(
                    f"Tracked role with id {new_event.tracked_role_id} not found."
                )

            event: TrackedRoleEvent = TrackedRoleEvent(**new_event.model_dump())
            self.db.add(event)
            await self.db.flush()

            history: EventStatusHistory = EventStatusHistory(
                event_id=event.id,
                from_status=None,
                to_status=event.status,
                occurred_at=occurred_at or datetime.now(UTC),
            )
            self.db.add(history)
            await self.db.flush()
            return event
        except SQLAlchemyError as exc:
            raise EventCreationError("Failed to create event") from exc

    async def update_event(
        self,
        event_id: UUID,
        event_update: EventUpdate,
        *,
        occurred_at: datetime | None = None,
    ) -> TrackedRoleEvent:
        """Apply a patch validated against the complete resulting event.

        Omitted fields remain unchanged; explicit null clears nullable fields. The
        type and custom label must remain valid together. Only actual status changes
        append history, using occurred_at or the current UTC time.
        """
        event: TrackedRoleEvent = await self.get_event(event_id)
        try:
            updated_data: dict[str, Any] = event_update.model_dump(exclude_unset=True)

            # A type-only patch may conflict with a stored custom name, so the
            # domain rule must be checked against the complete resulting event.
            current_data: dict[str, Any] = EventCreate.model_validate(
                event
            ).model_dump()
            current_data.update(updated_data)
            EventCreate.model_validate(current_data)

            previous_status: EventStatus = event.status
            for field, value in updated_data.items():
                setattr(event, field, value)

            if event.status != previous_status:
                history: EventStatusHistory = EventStatusHistory(
                    event_id=event.id,
                    from_status=previous_status,
                    to_status=event.status,
                    occurred_at=occurred_at or datetime.now(UTC),
                )
                self.db.add(history)

            await self.db.flush()
            await self.db.refresh(event)
            return event
        except SQLAlchemyError as exc:
            raise EventUpdateError(f"Failed to update event: {event_id}") from exc

    async def delete_event(self, event_id: UUID) -> None:
        """Delete an event and its status history while retaining its parent role."""
        event: TrackedRoleEvent = await self.get_event(event_id)
        try:
            await self.db.delete(event)
            await self.db.flush()
        except SQLAlchemyError as exc:
            raise EventDeletionError(f"Failed to delete event: {event_id}") from exc
