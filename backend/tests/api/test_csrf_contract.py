import pytest

pytestmark = pytest.mark.anyio


async def test_documented_csrf_header_supports_profile_write_and_logout(api_client):
    # Read the header name from OpenAPI to exercise the contract Swagger uses.
    api_client.headers.pop("X-CSRF-Token")
    response = await api_client.get("/auth/me")
    assert response.status_code == 200
    csrf_token = response.json()["csrf_token"]
    schema = (await api_client.get("/openapi.json")).json()

    response = await api_client.patch("/users/me", json={"name": "Changed"})
    assert response.status_code == 403
    header = next(
        parameter["name"]
        for parameter in schema["paths"]["/users/me"]["patch"]["parameters"]
        if parameter["in"] == "header"
    )
    response = await api_client.patch(
        "/users/me", json={"name": "Changed"}, headers={header: csrf_token}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Changed"

    for token in (None, "incorrect-token"):
        response = await api_client.post(
            "/auth/logout", headers={header: token} if token is not None else {}
        )
        assert response.status_code == 403
        assert (await api_client.get("/auth/me")).status_code == 200

    logout_header = next(
        parameter["name"]
        for parameter in schema["paths"]["/auth/logout"]["post"]["parameters"]
        if parameter["in"] == "header"
    )
    response = await api_client.post(
        "/auth/logout", headers={logout_header: csrf_token}
    )
    assert response.status_code == 204
    assert (await api_client.get("/auth/me")).status_code == 401
    assert (await api_client.post("/auth/logout")).status_code == 204
