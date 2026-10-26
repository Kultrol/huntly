from datetime import UTC, datetime
from uuid import UUID

CONTACT_ID = UUID("11111111-1111-4111-8111-111111111111")
USER_ID = UUID("22222222-2222-4222-8222-222222222222")
COMPANY_ID = UUID("33333333-3333-4333-8333-333333333333")
CREATED_AT = datetime(2026, 10, 12, 12, 0, tzinfo=UTC)
UPDATED_AT = datetime(2026, 10, 12, 13, 0, tzinfo=UTC)
CREATE_CONTACT_DATA = {"user_id": USER_ID, "name": "Kevin"}
NULL_DETAILS = {
    "company_id": None,
    "phone_number": None,
    "role": None,
    "email": None,
    "linkedin_url": None,
    "notes": None,
}
POPULATED_DETAILS = {
    "company_id": COMPANY_ID,
    "phone_number": "555-0100",
    "role": "Recruiter",
    "email": "kevin@example.com",
    "linkedin_url": "https://www.linkedin.com/in/kevin/",
    "notes": "Met at a career fair.",
}
READ_CONTACT_DATA = {
    "id": CONTACT_ID,
    **CREATE_CONTACT_DATA,
    **NULL_DETAILS,
    "created_at": CREATED_AT,
    "updated_at": UPDATED_AT,
}
