from datetime import date
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import TrackedRole, TrackedRoleEvent
from app.schemas.event import EventCreate, EventUpdate
from app.services.event import EventService
from app.services.exceptions.event import (
    EventCreationError,
    EventDeletionError,
    EventFetchingError,
    EventUpdateError,
)

pytestmark = pytest.mark.anyio


# Event database failures must keep their cause and leave transaction control to the
# caller.
@pytest.mark.parametrize(
    "operation, failed_method, expected_error",
    [
        ("get", "get", EventFetchingError),
        ("list", "scalars", EventFetchingError),
        ("create", "flush", EventCreationError),
        ("update", "flush", EventUpdateError),
        ("delete", "flush", EventDeletionError),
        ("update", "refresh", EventUpdateError),
    ],
)
async def test_event_database_failures_preserve_operation_and_cause(
    operation, failed_method, expected_error
):
    role_id = uuid4()
    record_id = uuid4()
    record = TrackedRoleEvent(
        id=record_id,
        tracked_role_id=role_id,
        title="Interview",
        event_date=date(2026, 1, 1),
        event_type="interview",
        status="scheduled",
    )
    session = AsyncMock(spec=AsyncSession)
    parent = TrackedRole(id=role_id, user_id=uuid4(), title="Developer", status="saved")
    session.get.side_effect = lambda model, id: (
        parent if model is TrackedRole else record
    )
    database_error = SQLAlchemyError("Database unavailable")
    getattr(session, failed_method).side_effect = database_error
    service = EventService(session)
    with pytest.raises(expected_error) as exc_info:
        if operation == "get":
            await service.get_event(record_id)
        elif operation == "list":
            await service.get_all_events(role_id)
        elif operation == "create":
            await service.create_event(
                EventCreate.model_validate(
                    {
                        "tracked_role_id": role_id,
                        "title": "Interview",
                        "event_date": "2026-01-01",
                        "event_type": "interview",
                        "status": "scheduled",
                    }
                )
            )
        elif operation == "update":
            await service.update_event(
                record_id, EventUpdate(title="Updated interview")
            )
        else:
            await service.delete_event(record_id)
    assert exc_info.value.__cause__ is database_error
    session.commit.assert_not_awaited()
    session.rollback.assert_not_awaited()


# Unexpected coding errors must escape without becoming event service errors.
async def test_event_service_does_not_wrap_programming_errors():
    session = AsyncMock(spec=AsyncSession)
    session.get.side_effect = TypeError("Unexpected programming error")
    with pytest.raises(TypeError, match="Unexpected programming error"):
        await EventService(session).get_event(uuid4())
