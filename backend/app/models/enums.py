from enum import StrEnum

# Values stored in the DB are the *right-hand* strings (e.g. "full_time"),
# not the member names (FULL_TIME). Models use values_callable so SQLAlchemy
# persists those values into VARCHAR columns.


class JobType(StrEnum):
    """How the role is structured (full-time, contract, etc.)."""

    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    TEMPORARY = "temporary"
    OTHER = "other"


class Priority(StrEnum):
    """How important this application is to you in the tracker."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ApplicationStatus(StrEnum):
    """Where an application sits in the hiring pipeline.

    Status history rows record these over time; the "current" status is
    usually the latest history row (or a denormalized field added later).
    """

    WISHLIST = "wishlist"  # Saved / interested, not submitted yet
    APPLIED = "applied"  # Application submitted
    SCREENING = "screening"  # Recruiter or automated screen
    INTERVIEW = "interview"  # Active interview loop
    OFFER = "offer"  # Offer received
    REJECTED = "rejected"  # Company passed (or you were rejected)
    ACCEPTED = "accepted"  # You accepted an offer
    WITHDRAWN = "withdrawn"  # You withdrew the application


class InterviewType(StrEnum):
    """Format / focus of a single interview event."""

    PHONE = "phone"
    VIDEO = "video"
    ONSITE = "onsite"
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    PANEL = "panel"
    OTHER = "other"


class InterviewOutcome(StrEnum):
    """Result of one interview (not the whole application)."""

    PENDING = "pending"  # Scheduled or completed, no decision yet
    PASSED = "passed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"
