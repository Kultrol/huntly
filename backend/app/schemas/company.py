from datetime import datetime
from typing import Annotated, ClassVar

from pydantic import (
    UUID4,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    StringConstraints,
    field_validator,
)


class CompanyRead(BaseModel):
    """Company fields without related collections to avoid recursive responses.

    ``normalized_name`` is the system-derived duplicate key. Timestamps describe
    storage writes, with ``updated_at`` refreshed by SQLAlchemy-managed updates.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    id: UUID4
    user_id: UUID4
    name: str
    normalized_name: str
    website: str | None
    linkedin_url: str | None
    location: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class CompanyCreate(BaseModel):
    """Company input with a nonblank name and optional metadata.

    Callers verify the supplied owner. The model derives the user-scoped duplicate
    key and enforces uniqueness; this schema performs no database lookup.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    user_id: UUID4
    name: Annotated[
        str, StringConstraints(max_length=255, strip_whitespace=True, min_length=1)
    ]
    website: str | None = Field(default=None, max_length=255)
    linkedin_url: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None)

    @field_validator("website", "linkedin_url", mode="before")
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        """Return a normalized HTTP(S) URL as plain text for SQL string columns.

        Hosts are unrestricted, including single-label hosts such as ``https://example``.
        LinkedIn fields do not require a LinkedIn host. None remains None.
        """
        return str(HttpUrl(value)) if value is not None else None


class CompanyUpdate(BaseModel):
    """Partial company input; dump with ``exclude_unset=True`` to preserve omissions.

    Explicit null clears optional metadata but cannot clear the name. The model
    maintains the normalized duplicate key.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    name: (
        Annotated[
            str, StringConstraints(max_length=255, strip_whitespace=True, min_length=1)
        ]
        | None
    ) = Field(default=None)
    website: str | None = Field(default=None, max_length=255)
    linkedin_url: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None)

    @field_validator("name", mode="before")
    @classmethod
    def reject_null_name(cls, value: str | None) -> object:
        """Allow omission of the name, but reject an explicit null."""
        if value is None:
            raise ValueError("Company name cannot be null.")
        return value

    @field_validator("website", "linkedin_url", mode="before")
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        """Return a normalized HTTP(S) URL as plain text, or None.

        Hosts are unrestricted; LinkedIn fields do not require a LinkedIn host.
        """
        return str(HttpUrl(value)) if value is not None else None
