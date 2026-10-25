import pytest
from pydantic import ValidationError
from pydantic_settings import SettingsError

from app.core.config import Settings

# Pydantic's generated signature omits inherited _env_file support and cannot
# account for required fields supplied by environment variables.


@pytest.fixture
def clean_settings_environment(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)


# Configuration fails when either required setting is absent from both input and environment.
@pytest.mark.parametrize("missing_field", ["database_url", "allowed_origins"])
def test_settings_require_database_and_allowed_origins(
    clean_settings_environment, missing_field
):
    fields = {
        "database_url": "postgresql+psycopg://example.invalid/test",
        "allowed_origins": [],
    }
    fields.pop(missing_field)
    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None, **fields)  # pyright: ignore[reportCallIssue]
    assert any(
        error["loc"] == (missing_field,) and error["type"] == "missing"
        for error in exc_info.value.errors()
    )


# Configuration accepts an empty browser-origin list or a list of origin strings.
@pytest.mark.parametrize(
    "origins",
    [[], ["http://localhost:5173"], ["https://one.example", "https://two.example"]],
)
def test_settings_accept_origin_lists(clean_settings_environment, origins):
    settings = Settings(
        _env_file=None,  # pyright: ignore[reportCallIssue]
        database_url="postgresql+psycopg://example.invalid/test",
        allowed_origins=origins,
    )
    assert settings.allowed_origins == origins


# Configuration rejects browser origins supplied in the wrong format or with non-text entries.
@pytest.mark.parametrize("origins", ["http://localhost:5173", [1], None])
def test_settings_reject_invalid_origin_types(clean_settings_environment, origins):
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            _env_file=None,  # pyright: ignore[reportCallIssue]
            database_url="postgresql+psycopg://example.invalid/test",
            allowed_origins=origins,
        )
    assert exc_info.value.errors()[0]["loc"][0] == "allowed_origins"


# Environment variables override the settings file, and explicit inputs override the
# environment.
def test_settings_environment_overrides_dotenv_and_constructor_overrides_environment(
    monkeypatch, tmp_path
):
    env_file = tmp_path / "test.env"
    env_file.write_text(
        'DATABASE_URL=postgresql+psycopg://file.invalid/test\nALLOWED_ORIGINS=["https://file.example"]\nIGNORED=value\n'
    )
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://environment.invalid/test")
    monkeypatch.setenv("ALLOWED_ORIGINS", '["https://environment.example"]')
    settings = Settings(_env_file=env_file)  # pyright: ignore[reportCallIssue]
    assert settings.database_url == "postgresql+psycopg://environment.invalid/test"
    assert settings.allowed_origins == ["https://environment.example"]
    explicit = Settings(
        _env_file=env_file,  # pyright: ignore[reportCallIssue]
        database_url="postgresql+psycopg://explicit.invalid/test",
        allowed_origins=[],
    )
    assert explicit.database_url == "postgresql+psycopg://explicit.invalid/test"
    assert explicit.allowed_origins == []


# Configuration rejects an environment origin list that is not valid JSON.
def test_settings_reject_malformed_environment_origin_json(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://example.invalid/test")
    monkeypatch.setenv("ALLOWED_ORIGINS", "not-json")
    with pytest.raises(SettingsError, match="allowed_origins"):
        Settings(_env_file=None)  # pyright: ignore[reportCallIssue]
