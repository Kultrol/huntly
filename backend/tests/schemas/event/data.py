from datetime import UTC, date, datetime, time, timedelta, timezone
from uuid import UUID

from app.enums import EventStatus, EventType

EVENT_ID = UUID("00000000-0000-0000-0000-000000000001")
ROLE_ID = UUID("00000000-0000-0000-0000-000000000002")
EVENT_DATE = date(2026, 10, 12)
EVENT_TIME = time(14, 30, tzinfo=timezone(timedelta(hours=-4)))
CREATED_AT = datetime(2026, 10, 10, 12, tzinfo=UTC)
UPDATED_AT = datetime(2026, 10, 11, 12, tzinfo=UTC)
READ_DATA = {
    "id": EVENT_ID,
    "tracked_role_id": ROLE_ID,
    "title": "Technical interview",
    "event_type": EventType.INTERVIEW,
    "custom_type_name": None,
    "event_date": EVENT_DATE,
    "event_time": None,
    "status": EventStatus.SCHEDULED,
    "notes": None,
    "url": None,
    "location": None,
    "created_at": CREATED_AT,
    "updated_at": UPDATED_AT,
}
CREATE_DATA = {
    "tracked_role_id": ROLE_ID,
    "title": "Technical interview",
    "event_type": EventType.INTERVIEW,
    "event_date": EVENT_DATE,
    "status": EventStatus.SCHEDULED,
}
