from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    db_name: str
    postgres_user: str
    postgres_password: str
    db_url: str

    model_config = SettingsConfigDict(env_file=".env", env_file_depth=2)  # pyright:ignore[reportCallIssue]


settings = Settings()  # pyright:ignore[reportCallIssue]
