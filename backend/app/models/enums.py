from enum import StrEnum

from sqlalchemy import Enum as SQLAlchemyEnum


def enum_type(enum_class: type[StrEnum], name: str) -> SQLAlchemyEnum:
    """Store enum values (e.g. full_time) and reject unlisted values."""
    return SQLAlchemyEnum(
        enum_class,
        name=name,
        values_callable=lambda members: [member.value for member in members],
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
    )


class TrackedRoleType(StrEnum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    TEMPORARY = "temporary"
    OTHER = "other"


class Priority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TrackedRoleStatus(StrEnum):
    SAVED = "saved"
    APPLIED = "applied"
    SCREENING = "screening"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"
    ACCEPTED = "accepted"
    WITHDRAWN = "withdrawn"


class EventStatus(StrEnum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    MISSED = "missed"


class EventType(StrEnum):
    INTERVIEW = "interview"
    RECRUITER_SCREEN = "recruiter_screen"
    ASSESSMENT = "assessment"
    FOLLOW_UP = "follow_up"
    APPLICATION_DEADLINE = "application_deadline"
    OFFER_DEADLINE = "offer_deadline"
    NETWORKING = "networking"
    CUSTOM = "custom"


class RelationshipType(StrEnum):
    RECRUITER = "recruiter"
    HIRING_MANAGER = "hiring_manager"
    INTERVIEWER = "interviewer"
    REFERRAL = "referral"
    TEAM_MEMBER = "team_member"
    OTHER = "other"
