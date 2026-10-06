"""ORM models package for Huntly.

Importing this package registers all ORM models with Base.metadata.
"""

from app.models.company import Company
from app.models.contact import Contact
from app.models.tracked_role.event import TrackedRoleEvent
from app.models.tracked_role.event_status_history import EventStatusHistory
from app.models.tracked_role.role_contact_association import (
    TrackedRoleContact,
    TrackedRoleContactAssociation,
)
from app.models.tracked_role.status_history import StatusHistory
from app.models.tracked_role.tracked_role import TrackedRole
from app.models.user import User

Event = TrackedRoleEvent
TrackedRoleStatusHistory = StatusHistory

__all__ = [
    "Company",
    "Contact",
    "Event",
    "EventStatusHistory",
    "StatusHistory",
    "TrackedRole",
    "TrackedRoleContact",
    "TrackedRoleContactAssociation",
    "TrackedRoleEvent",
    "TrackedRoleStatusHistory",
    "User",
]
