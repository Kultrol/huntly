from enum import StrEnum

from sqlalchemy import Enum as SQLAlchemyEnum


def enum_type(enum_class: type[StrEnum], name: str) -> SQLAlchemyEnum:
    """Store canonical enum values and constrain them in the database."""
    return SQLAlchemyEnum(
        enum_class,
        name=name,
        values_callable=lambda members: [member.value for member in members],
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
    )


class TrackedRoleType(StrEnum):
    """How the role is structured (full-time, contract, etc.)."""

    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    TEMPORARY = "temporary"
    OTHER = "other"


class Priority(StrEnum):
    """The user's perceived importance of a tracked opportunity."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TrackedRoleStatus(StrEnum):
    """The current lifecycle stage of a tracked opportunity."""

    SAVED = "saved"  # Saved / interested, not submitted yet
    APPLIED = "applied"  # Application submitted
    SCREENING = "screening"  # Recruiter or automated screen
    INTERVIEW = "interview"  # Active interview loop
    OFFER = "offer"  # Offer received
    REJECTED = "rejected"  # Company passed (or you were rejected)
    ACCEPTED = "accepted"  # You accepted an offer
    WITHDRAWN = "withdrawn"  # You withdrew the application


class EventStatus(StrEnum):
    """Status of an event (scheduled, completed, cancelled, etc.)."""

    PENDING = "pending"
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    MISSED = "missed"


class EventType(StrEnum):
    """The canonical kind of a dated activity or deadline."""

    INTERVIEW = "interview"
    RECRUITER_SCREEN = "recruiter_screen"
    ASSESSMENT = "assessment"
    FOLLOW_UP = "follow_up"
    APPLICATION_DEADLINE = "application_deadline"
    OFFER_DEADLINE = "offer_deadline"
    NETWORKING = "networking"
    CUSTOM = "custom"


class RelationshipType(StrEnum):
    """Type of relationship between a tracked role and a contact."""

    RECRUITER = "recruiter"
    HIRING_MANAGER = "hiring_manager"
    INTERVIEWER = "interviewer"
    REFERRAL = "referral"
    TEAM_MEMBER = "team_member"
    OTHER = "other"
