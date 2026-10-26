import pytest

from app.enums import EventType
from app.models import TrackedRoleEvent


@pytest.fixture
async def custom_event(sessions, saved_event):
    async with sessions.begin() as session:
        event = await session.get(TrackedRoleEvent, saved_event.id)
        assert event is not None
        event.event_type = EventType.CUSTOM
        event.custom_type_name = "Portfolio review"
    return event
