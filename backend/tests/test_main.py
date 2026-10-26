from pathlib import Path
from runpy import run_path

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


# The application's root endpoint returns the expected greeting.
def test_root_greeting():
    response = TestClient(app).get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello world! From backend."}


# The API documentation includes each resource's create, read, update, and delete contracts.
@pytest.mark.parametrize(
    "path, model",
    [
        ("/users", "User"),
        ("/companies", "Company"),
        ("/contacts", "Contact"),
        ("/tracked-roles", "TrackedRole"),
        ("/events", "Event"),
    ],
)
def test_openapi_registers_crud_routes_and_schemas(path, model):
    response = TestClient(app).get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    collection = schema["paths"][f"{path}/"]
    detail = schema["paths"][f"{path}/{{id}}"]
    assert set(collection) == {"get", "post"}
    assert set(detail) == {"get", "patch", "delete"}
    assert (
        collection["post"]["requestBody"]["content"]["application/json"]["schema"][
            "$ref"
        ]
        == f"#/components/schemas/{model}Create"
    )
    assert (
        collection["post"]["responses"]["201"]["content"]["application/json"]["schema"][
            "$ref"
        ]
        == f"#/components/schemas/{model}Read"
    )
    assert (
        detail["patch"]["requestBody"]["content"]["application/json"]["schema"]["$ref"]
        == f"#/components/schemas/{model}Update"
    )
    assert "content" not in detail["delete"]["responses"]["204"]


# The API accepts the effective status-change time as an optional query value.
@pytest.mark.parametrize("path", ["/tracked-roles/", "/events/"])
def test_occurrence_time_is_a_query_parameter(path):
    operation = app.openapi()["paths"][path]["post"]
    parameter = next(
        item for item in operation["parameters"] if item["name"] == "occurred_at"
    )
    assert parameter["in"] == "query"
    assert parameter["required"] is False


# Browser preflight requests are allowed only for configured origins and do not allow
# credentials.
@pytest.mark.parametrize(
    "origin, allowed",
    [("https://allowed.example", True), ("https://blocked.example", False)],
)
def test_cors_preflight_allows_only_configured_origins(monkeypatch, origin, allowed):
    monkeypatch.setattr(settings, "allowed_origins", ["https://allowed.example"])
    configured_app = run_path(
        str(Path(__file__).resolve().parents[1] / "app" / "main.py")
    )["app"]
    response = TestClient(configured_app).options(
        "/companies/",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert response.status_code == (200 if allowed else 400)
    if allowed:
        assert response.headers["access-control-allow-origin"] == origin
        assert "POST" in response.headers["access-control-allow-methods"]
    else:
        assert "access-control-allow-origin" not in response.headers
    assert "access-control-allow-credentials" not in response.headers
