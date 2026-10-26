from datetime import datetime
from typing import Annotated, ClassVar
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    StringConstraints,
    field_validator,
)


class ContactRead(BaseModel):
    """Contact fields with identifiers instead of embedded companies and roles.

    ``role`` is a professional title. The optional company link is cleared if that
    company is deleted; opportunity-association collections are omitted.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    company_id: UUID | None
    name: str
    phone_number: str | None
    role: str | None
    email: str | None
    linkedin_url: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class ContactCreate(BaseModel):
    """Contact input; a company or opportunity is not required.

    Callers verify ownership and linked records. Email is length-limited text, not
    format-validated. This schema neither infers an employer nor detects duplicates.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    user_id: UUID
    company_id: UUID | None = Field(default=None)
    name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
    ]
    phone_number: str | None = Field(default=None, max_length=32)
    role: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    linkedin_url: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None)

    @field_validator("linkedin_url", mode="before")
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        """Return a normalized HTTP(S) URL as plain text, or None.

        Hosts are unrestricted; LinkedIn fields do not require a LinkedIn host.
        """
        return str(HttpUrl(value)) if value is not None else None


class ContactUpdate(BaseModel):
    """Partial contact input; dump with ``exclude_unset=True`` to preserve omissions.

    Explicit null may clear the company link or optional details, but not the name.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    company_id: UUID | None = Field(default=None)
    name: (
        Annotated[
            str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
        ]
        | None
    ) = Field(default=None)
    phone_number: str | None = Field(default=None, max_length=32)
    role: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    linkedin_url: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None)

    @field_validator("linkedin_url", mode="before")
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        """Return a normalized HTTP(S) URL as plain text, or None.

        Hosts are unrestricted; LinkedIn fields do not require a LinkedIn host.
        """
        return str(HttpUrl(value)) if value is not None else None

    @field_validator("name", mode="before")
    @classmethod
    def reject_null_name(cls, value: str | None) -> object:
        """Allow omission of the name, but reject an explicit null."""
        if value is None:
            raise ValueError("Contact name cannot be null.")
        return value
