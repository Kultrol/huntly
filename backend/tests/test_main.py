import pytest
from fastapi.testclient import TestClient

from app.main import app


# The API documentation includes the registered resource CRUD contracts.
@pytest.mark.parametrize(
    "path, model",
    [
        ("/users", "User"),
        ("/companies", "Company"),
        ("/contacts", "Contact"),
        ("/tracked-roles", "TrackedRole"),
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
@pytest.mark.parametrize("path", ["/tracked-roles/"])
def test_occurrence_time_is_a_query_parameter(path):
    operation = app.openapi()["paths"][path]["post"]
    parameter = next(
        item for item in operation["parameters"] if item["name"] == "occurred_at"
    )
    assert parameter["in"] == "query"
    assert parameter["required"] is False
