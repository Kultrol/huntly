from typing import ClassVar

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Database and CORS settings loaded from the environment or ``.env``.

    Environment variables take precedence. Extra ``.env`` entries are ignored so
    this file can also hold Compose settings. Both settings are required.
    """

    database_url: str
    allowed_origins: list[str]

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=".env", extra="ignore"
    )


settings: Settings = Settings()  # pyright:ignore[reportCallIssue]
