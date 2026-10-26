import pytest
from fastapi.testclient import TestClient

from app.main import app


# The API documentation includes user, company, and contact CRUD contracts.
@pytest.mark.parametrize(
    "path, model",
    [
        ("/users", "User"),
        ("/companies", "Company"),
        ("/contacts", "Contact"),
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
