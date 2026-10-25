from datetime import UTC, datetime
from uuid import UUID

COMPANY_ID = UUID("11111111-1111-4111-8111-111111111111")
USER_ID = UUID("22222222-2222-4222-8222-222222222222")
CREATED_AT = datetime(2026, 10, 12, 12, tzinfo=UTC)
UPDATED_AT = datetime(2026, 10, 12, 13, tzinfo=UTC)
CREATE_DATA = {"user_id": USER_ID, "name": "Kevin"}
NULL_DETAILS = {
    "website": None,
    "linkedin_url": None,
    "location": None,
    "notes": None,
}
READ_DATA = {
    "id": COMPANY_ID,
    **CREATE_DATA,
    "normalized_name": "kevin",
    **NULL_DETAILS,
    "created_at": CREATED_AT,
    "updated_at": UPDATED_AT,
}
