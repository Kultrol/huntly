from typing import ClassVar

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Database, browser access, and authentication settings."""

    database_url: str
    allowed_origins: list[str]
    session_cookie_name: str = Field(
        default="huntly_session", pattern=r"^[a-zA-Z0-9_-]+$"
    )
    # Local HTTP development overrides this; HTTPS deployments keep it enabled.
    session_cookie_secure: bool = True
    # This is an absolute lifetime: using a session does not extend its deadline.
    session_lifetime_seconds: int = Field(default=604800, ge=300, le=2592000)

    @field_validator("allowed_origins")
    @classmethod
    def require_explicit_origins(cls, value: list[str]) -> list[str]:
        """Accept exact browser origins for credentialed CORS and write checks.

        An origin is only a scheme, host, and optional port. Paths and wildcard
        hosts would not match the browser's Origin header reliably.
        """
        from urllib.parse import urlsplit

        for origin in value:
            parsed = urlsplit(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.username is not None
                or parsed.password is not None
                or parsed.path
                or parsed.query
                or parsed.fragment
                or "*" in origin
            ):
                raise ValueError(
                    "Allowed origins must be explicit HTTP(S) origins without paths."
                )
        return value

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=".env", extra="ignore"
    )


settings: Settings = Settings()  # pyright:ignore[reportCallIssue]
