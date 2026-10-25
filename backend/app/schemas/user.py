from typing import Annotated, ClassVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

UserName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, pattern=r"^[^\x00]*$"),
]


class UserRead(BaseModel):
    """User identifier and display name, without credentials or ownership collections."""

    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    id: UUID
    name: str


class UserCreate(BaseModel):
    """A nonblank display name without authentication fields.

    Trim surrounding whitespace; preserve internal whitespace and allow duplicates.
    Null characters are rejected because PostgreSQL text cannot store them.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    name: UserName


class UserUpdate(BaseModel):
    """Partial display-name input; omission is allowed but explicit null is not.

    Dump with ``exclude_unset=True`` to avoid overwriting an omitted name with None.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    name: UserName | None = Field(default=None)

    @field_validator("name")
    @classmethod
    def reject_null_name(cls, value: str | None) -> str:
        """Allow omission of the name, but reject an explicit null."""
        if value is None:
            raise ValueError("User name cannot be null.")
        return value
