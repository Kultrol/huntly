import re
from datetime import date, datetime, time
from typing import Annotated, ClassVar, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.enums import EventStatus, EventType


class EventRead(BaseModel):
    """Event fields with a parent identifier and no embedded status history.

    A null time preserves a date-only event. A custom label accompanies CUSTOM and
    is otherwise null.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    id: UUID
    tracked_role_id: UUID
    title: str
    event_type: EventType
    custom_type_name: str | None
    event_date: date
    event_time: time | None
    status: EventStatus
    notes: str | None
    url: str | None
    location: str | None
    created_at: datetime
    updated_at: datetime


class EventCreate(BaseModel):
    """Event input with a required date, category, and explicit status.

    Past dates are valid, missing times stay unknown, and status is not inferred.
    CUSTOM requires a label; other categories forbid one. Callers verify the parent
    role and its owner, then create the event and initial history.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    tracked_role_id: UUID
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    event_type: EventType
    custom_type_name: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None
    ) = Field(default=None)
    event_date: date
    event_time: time | None = Field(default=None)
    status: EventStatus
    notes: str | None = Field(default=None)
    url: str | None = Field(default=None)
    location: str | None = Field(default=None)

    @field_validator("url", mode="before")
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        """Return a normalized HTTP(S) URL as plain text, or None; any host is allowed."""
        return str(HttpUrl(value)) if value is not None else None

    @field_validator("custom_type_name")
    @classmethod
    def validate_custom_type_name(cls, value: str | None) -> str | None:
        """Reject labels matching canonical categories, including CUSTOM itself.

        Comparison ignores case and treats hyphens and underscores as spaces.
        Display whitespace is collapsed; other separators are preserved.
        """
        if value is None:
            return None
        normalized_name: str = re.sub(r"[\s_-]+", " ", value).strip().casefold()
        if normalized_name == "":
            raise ValueError("Custom event type name must not be empty/blank.")
        canonical_names: set[str] = {
            member.value.replace("_", " ") for member in EventType
        }
        if normalized_name in canonical_names:
            raise ValueError(
                "Custom event type name must not reproduce a canonical type."
            )
        return " ".join(value.split())

    @model_validator(mode="after")
    def validate_custom_type(self) -> Self:
        """Require a custom label for CUSTOM and forbid one for other categories."""
        if self.event_type == EventType.CUSTOM and self.custom_type_name is None:
            raise ValueError("Custom events require a custom type name.")
        if self.event_type != EventType.CUSTOM and self.custom_type_name is not None:
            raise ValueError("Only custom events may have a custom type name.")
        return self


class EventUpdate(BaseModel):
    """Partial event input; dump with ``exclude_unset=True`` to preserve omissions.

    Explicit null clears optional fields, but not title, category, date, or status.
    The service validates category/label pairing on the merged saved record, and
    the ORM rechecks it before persistence.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    title: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None
    ) = Field(default=None)
    event_type: EventType | None = Field(default=None)
    custom_type_name: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None
    ) = Field(default=None)
    event_date: date | None = Field(default=None)
    event_time: time | None = Field(default=None)
    status: EventStatus | None = Field(default=None)
    notes: str | None = Field(default=None)
    url: str | None = Field(default=None)
    location: str | None = Field(default=None)

    @field_validator("url", mode="before")
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        """Return a normalized HTTP(S) URL as plain text, or None; any host is allowed."""
        return str(HttpUrl(value)) if value is not None else None

    @field_validator("custom_type_name")
    @classmethod
    def validate_custom_type_name(cls, value: str | None) -> str | None:
        """Check label content without requiring the event category in this update.

        Comparison ignores case and treats hyphens and underscores as spaces; display
        separators are preserved. The service checks pairing on the merged record.
        """
        if value is None:
            return None
        normalized_name: str = re.sub(r"[\s_-]+", " ", value).strip().casefold()
        if normalized_name == "":
            raise ValueError("Custom event type name must not be empty.")
        canonical_names: set[str] = {
            member.value.replace("_", " ") for member in EventType
        }
        if normalized_name in canonical_names:
            raise ValueError(
                "Custom event type name must not reproduce a canonical type."
            )
        return " ".join(value.split())

    @model_validator(mode="before")
    @classmethod
    def reject_null_required_fields(cls, data: object) -> object:
        """Allow omitted title, category, date, and status fields; reject explicit nulls."""
        if isinstance(data, dict):
            for field in ("title", "event_type", "event_date", "status"):
                if field in data and data[field] is None:
                    raise ValueError(f"Event {field} cannot be null.")
        return data
