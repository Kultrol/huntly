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
    model_validator,
)


class CompanyRead(BaseModel):
    """Flat persisted company data, including the system-controlled name key.

    Attributes:
        normalized_name: User-scoped duplicate key derived from the display name.
        created_at: Storage creation timestamp.
        updated_at: Timestamp of the latest SQLAlchemy-managed write.

    Notes:
        Related contacts and opportunities are omitted to keep the response from
        recursively embedding their company relationships.
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
    """Company creation input with a meaningful name and optional metadata.

    Attributes:
        user_id: Intended owner; callers must verify the ownership context.
        name: Display name, trimmed and limited to 255 characters.
        website: Optional HTTP(S) URL returned by validation as a plain string.
        linkedin_url: Optional HTTP(S) URL without a LinkedIn-only host restriction.

    Notes:
        The persistence model derives ``normalized_name`` and enforces uniqueness
        within one user's workspace; this schema performs no duplicate lookup.
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
        """Validate an HTTP(S) reference and keep it compatible with string columns.

        Args:
            value: URL text, or None when the reference is unknown or cleared.

        Returns:
            Pydantic's normalized URL as a plain string, or None.

        Raises:
            ValueError: If the value is not a valid HTTP(S) URL.

        Notes:
            Host names are unrestricted; a LinkedIn field does not require a
            LinkedIn host. Returning text avoids passing a HttpUrl object to SQL.


            https://* - where * represents any string character, though not a space, is considered a valid HttpUrl, so "https://something" is considered to be valid.
        """
        return str(HttpUrl(value)) if value is not None else None


class CompanyUpdate(BaseModel):
    """Partial company input that distinguishes omission from explicit clearing.

    Notes:
        Callers must use ``model_dump(exclude_unset=True)`` to retain omitted
        values. Explicit null clears nullable metadata but cannot clear the name.
        The normalized duplicate key is maintained by the persistence model.
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
        """Validate a provided name to ensure it is not explicitly set to None.

        Args:
            value: name provided.

        Returns:
            The provided name if it is not None.

        Raises:
            ValueError: If value is None.
        """
        if value is None:
            raise ValueError("Company name cannot be null.")
        return value

    @field_validator("website", "linkedin_url", mode="before")
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        """Validate an HTTP(S) reference and keep it compatible with string columns.

        Args:
            value: URL text, or None when the reference is unknown or cleared.

        Returns:
            Pydantic's normalized URL as a plain string, or None.

        Raises:
            ValueError: If the value is not a valid HTTP(S) URL.

        Notes:
            Host names are unrestricted; a LinkedIn field does not require a
            LinkedIn host. Returning text avoids passing a HttpUrl object to SQL.
        """
        return str(HttpUrl(value)) if value is not None else None
