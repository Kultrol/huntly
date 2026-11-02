"""HTTP create inputs derive ownership from the authenticated session.

The optional user_id keeps older clients compatible. Routes reject a conflicting
ID and supply the authenticated owner's ID to the internal service schemas.
"""

from uuid import UUID

from app.schemas.company import CompanyCreate
from app.schemas.contact import ContactCreate
from app.schemas.tracked_role import TrackedRoleCreate


class CompanyCreateRequest(CompanyCreate):
    user_id: UUID | None = None


class ContactCreateRequest(ContactCreate):
    user_id: UUID | None = None


class TrackedRoleCreateRequest(TrackedRoleCreate):
    user_id: UUID | None = None
