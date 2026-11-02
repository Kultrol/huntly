"""Validate account inputs and expose only public account/session fields.

SecretStr masks passwords in representations and serialized models; it does not
encrypt them. Authentication code explicitly unwraps each value for hashing.
"""

from datetime import datetime
from typing import Annotated, ClassVar
from uuid import UUID

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
    field_validator,
)

from app.schemas.user import UserName


def validate_password_text(value: SecretStr) -> SecretStr:
    """Reject lone Unicode surrogates before the password hasher encodes the text.

    JSON can contain these invalid characters. Preserve valid Unicode and all
    whitespace so validation does not silently change the user's password.
    """
    try:
        value.get_secret_value().encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError("Password must contain valid Unicode text.") from exc
    return value


PasswordText = Annotated[SecretStr, AfterValidator(validate_password_text)]
# Check existing passwords without imposing today's minimum on an older account;
# newly chosen passwords must satisfy the stronger minimum. Both have a size cap.
LoginPassword = Annotated[PasswordText, Field(min_length=1, max_length=128)]
Password = Annotated[PasswordText, Field(min_length=12, max_length=128)]


class AuthInput(BaseModel):
    """Reject unexpected account fields instead of silently accepting them."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")


class LoginRequest(AuthInput):
    email: EmailStr = Field(max_length=254)
    password: LoginPassword

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        """Use the same trimmed, lowercase login key for signup and sign-in."""
        return value.strip().lower() if isinstance(value, str) else value


class RegisterRequest(LoginRequest):
    name: Annotated[UserName, Field(max_length=255)]
    password: Password


class PasswordChangeRequest(AuthInput):
    current_password: LoginPassword
    new_password: Password


class AuthUserRead(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: str | None


class AuthRead(BaseModel):
    """Restore browser identity and its CSRF token without exposing the cookie."""

    user: AuthUserRead
    csrf_token: str


class SessionRead(BaseModel):
    """List revocable session IDs and deadlines without disclosing token hashes."""

    id: UUID
    created_at: datetime
    expires_at: datetime
    current: bool
