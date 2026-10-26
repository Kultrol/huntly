from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from app.enums import Priority, TrackedRoleStatus, TrackedRoleType

ROLE_ID = UUID("12345678-1234-5678-1234-567812345678")
USER_ID = UUID("22345678-1234-5678-1234-567812345678")
COMPANY_ID = UUID("32345678-1234-5678-1234-567812345678")
TIMESTAMP = datetime(2026, 10, 12, 14, 30, tzinfo=UTC)
CREATE_DATA = {
    "user_id": USER_ID,
    "title": "Backend Developer",
    "status": TrackedRoleStatus.SAVED,
}
NULL_DETAILS = {
    "company_id": None,
    "description": None,
    "role_type": None,
    "location": None,
    "source": None,
    "listing_url": None,
    "priority": None,
    "notes": None,
    "salary_min": None,
    "salary_max": None,
    "salary_currency": None,
    "applied_at": None,
}
POPULATED_DETAILS = {
    "company_id": COMPANY_ID,
    "description": "Build and maintain APIs.",
    "role_type": TrackedRoleType.FULL_TIME,
    "location": "Remote",
    "source": "Company website",
    "listing_url": "https://example.com/jobs/backend",
    "priority": Priority.HIGH,
    "notes": "Ask about the backend team.",
    "salary_min": Decimal("80000.50"),
    "salary_max": Decimal("100000.00"),
    "salary_currency": "USD",
    "applied_at": TIMESTAMP,
}
READ_DATA = {
    "id": ROLE_ID,
    **CREATE_DATA,
    **POPULATED_DETAILS,
    "created_at": TIMESTAMP,
    "updated_at": TIMESTAMP,
}
