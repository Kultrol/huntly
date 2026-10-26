from datetime import datetime
from decimal import Decimal
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

from app.enums import Priority, TrackedRoleStatus, TrackedRoleType


class TrackedRoleRead(BaseModel):
    """Opportunity fields without embedded companies, contacts, events, or histories.

    Salary bounds may be one-sided. A null ``applied_at`` preserves an unknown
    application time; a null company link means unknown or unassigned.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    company_id: UUID | None
    title: str
    status: TrackedRoleStatus
    description: str | None
    role_type: TrackedRoleType | None
    location: str | None
    source: str | None
    listing_url: str | None
    priority: Priority | None
    notes: str | None
    salary_min: Decimal | None
    salary_max: Decimal | None
    salary_currency: str | None
    applied_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TrackedRoleCreate(BaseModel):
    """Opportunity input with an explicit status, including roles not yet applied to.

    Callers verify the supplied owner. Salary bounds are nonnegative decimals and
    may be one-sided. Application dates are not inferred; status history and similar
    posting checks belong outside this schema.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    user_id: UUID
    company_id: UUID | None = Field(default=None)
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    status: TrackedRoleStatus
    description: str | None = Field(default=None)
    role_type: TrackedRoleType | None = Field(default=None)
    location: str | None = Field(default=None)
    source: str | None = Field(default=None)
    listing_url: str | None = Field(default=None)
    priority: Priority | None = Field(default=None)
    notes: str | None = Field(default=None)
    salary_min: Decimal | None = Field(default=None, ge=0)
    salary_max: Decimal | None = Field(default=None, ge=0)
    salary_currency: str | None = Field(default=None)
    applied_at: datetime | None = Field(default=None)

    @field_validator("listing_url", mode="before")
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        """Return a normalized HTTP(S) URL as plain text, or None; any host is allowed."""
        return str(HttpUrl(value)) if value is not None else None

    @model_validator(mode="after")
    def validate_salary_range(self) -> Self:
        """Reject an inverted salary range when both bounds are known."""
        if (
            self.salary_min is not None
            and self.salary_max is not None
            and self.salary_min > self.salary_max
        ):
            raise ValueError("Minimum salary cannot exceed maximum salary.")
        return self


class TrackedRoleUpdate(BaseModel):
    """Partial role input; dump with ``exclude_unset=True`` to preserve omissions.

    Explicit null may clear optional fields, but not title or status. Salary checks
    here see only supplied bounds; the service validates the merged saved range.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    company_id: UUID | None = Field(default=None)
    title: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)] | None
    ) = Field(default=None)
    status: TrackedRoleStatus | None = Field(default=None)
    description: str | None = Field(default=None)
    role_type: TrackedRoleType | None = Field(default=None)
    location: str | None = Field(default=None)
    source: str | None = Field(default=None)
    listing_url: str | None = Field(default=None)
    priority: Priority | None = Field(default=None)
    notes: str | None = Field(default=None)
    salary_min: Decimal | None = Field(default=None, ge=0)
    salary_max: Decimal | None = Field(default=None, ge=0)
    salary_currency: str | None = Field(default=None)
    applied_at: datetime | None = Field(default=None)

    @field_validator("listing_url", mode="before")
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        """Return a normalized HTTP(S) URL as plain text, or None; any host is allowed."""
        return str(HttpUrl(value)) if value is not None else None

    @model_validator(mode="before")
    @classmethod
    def reject_null_required_fields(cls, data: object) -> object:
        """Allow omitted title and status fields, but reject explicit nulls."""
        if isinstance(data, dict):
            for field in ("title", "status"):
                if field in data and data[field] is None:
                    raise ValueError(f"Tracked role {field} cannot be null.")
        return data

    @model_validator(mode="after")
    def validate_salary_range(self) -> Self:
        """Check salary ordering when both bounds appear in this update.

        The service checks omitted counterparts against saved values; the database
        constraint also protects the final range.
        """
        if (
            self.salary_min is not None
            and self.salary_max is not None
            and self.salary_min > self.salary_max
        ):
            raise ValueError("Minimum salary cannot exceed maximum salary.")
        return self
