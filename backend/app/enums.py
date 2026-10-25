"""Domain choices shared by schemas, services, and ORM models."""

from enum import StrEnum


class TrackedRoleType(StrEnum):
    """Employment arrangements, independent of an opportunity's lifecycle stage."""

    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    TEMPORARY = "temporary"
    OTHER = "other"


class Priority(StrEnum):
    """User-assigned importance; a nullable field represents unassigned priority."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TrackedRoleStatus(StrEnum):
    """Broad opportunity stages; membership does not impose a transition graph."""

    SAVED = "saved"
    APPLIED = "applied"
    SCREENING = "screening"
    INTERVIEW = "interview"
    OFFER = "offer"
    REJECTED = "rejected"
    ACCEPTED = "accepted"
    WITHDRAWN = "withdrawn"


class EventStatus(StrEnum):
    """Explicit activity outcomes, independent of whether the event date has passed."""

    PENDING = "pending"
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    MISSED = "missed"


class EventType(StrEnum):
    """Canonical activity categories, with CUSTOM reserved for a user-defined label."""

    INTERVIEW = "interview"
    RECRUITER_SCREEN = "recruiter_screen"
    ASSESSMENT = "assessment"
    FOLLOW_UP = "follow_up"
    APPLICATION_DEADLINE = "application_deadline"
    OFFER_DEADLINE = "offer_deadline"
    NETWORKING = "networking"
    CUSTOM = "custom"


class RelationshipType(StrEnum):
    """A person's connection to one opportunity, distinct from their job title."""

    RECRUITER = "recruiter"
    HIRING_MANAGER = "hiring_manager"
    INTERVIEWER = "interviewer"
    REFERRAL = "referral"
    TEAM_MEMBER = "team_member"
    OTHER = "other"
