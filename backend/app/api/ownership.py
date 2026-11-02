"""Owner-scoped resource lookups within the route's transaction."""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Company, Contact, TrackedRole, TrackedRoleEvent


async def require_owned_resource(
    db: AsyncSession,
    model: type[Company | Contact | TrackedRole],
    resource_id: UUID,
    user_id: UUID,
) -> None:
    """Require an owned record within the caller's transaction.

    Missing and foreign records both return 404 so a caller cannot discover
    whether another user's record exists.
    """
    resource = await db.scalar(
        select(model.id).where(model.id == resource_id, model.user_id == user_id)
    )
    if resource is None:
        label = {Company: "Company", Contact: "Contact", TrackedRole: "Tracked role"}[
            model
        ]
        raise HTTPException(
            status_code=404, detail=f"{label} with id {resource_id} not found."
        )


async def require_owned_event(db: AsyncSession, event_id: UUID, user_id: UUID) -> None:
    """Check the parent role's owner because events have no separate owner field.

    As with other resources, foreign and missing events share a 404 response.
    """
    event = await db.scalar(
        select(TrackedRoleEvent.id)
        .join(TrackedRole, TrackedRoleEvent.tracked_role_id == TrackedRole.id)
        .where(TrackedRoleEvent.id == event_id, TrackedRole.user_id == user_id)
    )
    if event is None:
        raise HTTPException(
            status_code=404, detail=f"Event with id {event_id} not found."
        )


def validate_supplied_owner(supplied_id: UUID | None, user_id: UUID) -> None:
    """Accept an omitted or matching legacy owner ID; the session supplies identity."""
    if supplied_id is not None and supplied_id != user_id:
        raise HTTPException(
            status_code=403, detail="Cannot create records for another user."
        )
