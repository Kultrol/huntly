from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    db_name: str
    db_user: str
    db_url: str

    model_config = SettingsConfigDict(env_file=".env", env_file_depth=2)  # pyright:ignore[reportCallIssue]


settings = Settings()  # pyright:ignore[reportCallIssue]
