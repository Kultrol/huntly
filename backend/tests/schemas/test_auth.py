import pytest
from pydantic import ValidationError

from app.schemas.auth import LoginRequest, PasswordChangeRequest, RegisterRequest


@pytest.mark.parametrize("model", [RegisterRequest, LoginRequest])
def test_auth_email_is_trimmed_and_normalized(model):
    data = model.model_validate(
        {
            "email": "  JANE@EXAMPLE.COM  ",
            "password": "A strong password 42!",
            **({"name": "Jane"} if model is RegisterRequest else {}),
        }
    )
    assert data.email == "jane@example.com"


def test_registration_name_is_trimmed_and_password_whitespace_is_preserved():
    data = RegisterRequest(
        name="  Jane Doe  ",
        email="jane@example.com",
        password="  A strong password 42!  ",
    )
    assert data.name == "Jane Doe"
    assert data.password.get_secret_value() == "  A strong password 42!  "
    assert "A strong password" not in repr(data)
    assert "A strong password" not in data.model_dump_json()


@pytest.mark.parametrize("password", ["x" * 12, "x" * 128])
def test_registration_accepts_password_length_boundaries(password):
    data = RegisterRequest(name="Jane", email="jane@example.com", password=password)
    assert data.password.get_secret_value() == password


@pytest.mark.parametrize("password", ["", "x" * 11, "x" * 129, None, 12345])
def test_registration_rejects_invalid_passwords(password):
    with pytest.raises(ValidationError) as exc_info:
        RegisterRequest(name="Jane", email="jane@example.com", password=password)
    assert any(error["loc"] == ("password",) for error in exc_info.value.errors())


@pytest.mark.parametrize(
    "email", ["invalid", "@example.com", None, 12345, "jane\x00@example.com"]
)
def test_registration_rejects_invalid_email(email):
    with pytest.raises(ValidationError) as exc_info:
        RegisterRequest(name="Jane", email=email, password="A strong password 42!")
    assert any(error["loc"] == ("email",) for error in exc_info.value.errors())


@pytest.mark.parametrize("name", ["", " ", "Jane\x00Doe", "x" * 256, None])
def test_registration_rejects_invalid_name(name):
    with pytest.raises(ValidationError) as exc_info:
        RegisterRequest(
            name=name, email="jane@example.com", password="A strong password 42!"
        )
    assert any(error["loc"] == ("name",) for error in exc_info.value.errors())


@pytest.mark.parametrize(
    "model, payload",
    [
        (
            RegisterRequest,
            {
                "name": "Jane",
                "email": "jane@example.com",
                "password": "A strong password 42!",
                "user_id": "override",
            },
        ),
        (
            LoginRequest,
            {
                "email": "jane@example.com",
                "password": "A strong password 42!",
                "admin": True,
            },
        ),
        (
            PasswordChangeRequest,
            {
                "current_password": "A strong password 42!",
                "new_password": "A stronger password 99!",
                "email": "other@example.com",
            },
        ),
    ],
)
def test_auth_inputs_reject_unexpected_fields(model, payload):
    with pytest.raises(ValidationError) as exc_info:
        model.model_validate(payload)
    assert any(error["type"] == "extra_forbidden" for error in exc_info.value.errors())


def test_login_accepts_existing_short_password_for_verification():
    data = LoginRequest(email="jane@example.com", password="old")
    assert data.password.get_secret_value() == "old"


@pytest.mark.parametrize("new_password", ["x" * 11, "x" * 129])
def test_password_change_enforces_new_password_length(new_password):
    with pytest.raises(ValidationError) as exc_info:
        PasswordChangeRequest(current_password="old", new_password=new_password)
    assert any(error["loc"] == ("new_password",) for error in exc_info.value.errors())


@pytest.mark.parametrize("surrogate", [chr(0xD800), chr(0xDFFF)], ids=["high", "low"])
@pytest.mark.parametrize(
    "model, field",
    [
        (RegisterRequest, "password"),
        (LoginRequest, "password"),
        (PasswordChangeRequest, "current_password"),
        (PasswordChangeRequest, "new_password"),
    ],
)
def test_auth_rejects_passwords_that_cannot_be_encoded_as_utf8(model, field, surrogate):
    payload = (
        {
            "current_password": "An existing password 42!",
            "new_password": "A stronger password 99!",
        }
        if model is PasswordChangeRequest
        else {
            "email": "jane@example.com",
            "password": "An existing password 42!",
            **({"name": "Jane"} if model is RegisterRequest else {}),
        }
    )
    payload[field] = "A password with " + surrogate

    with pytest.raises(ValidationError) as exc_info:
        model.model_validate(payload)

    errors = exc_info.value.errors()
    assert errors[0]["loc"] == (field,)
    assert errors[0]["type"] == "value_error"
    assert errors[0]["msg"] == "Value error, Password must contain valid Unicode text."


@pytest.mark.parametrize(
    "password", ["  密碼 café 🔐  ", "A combining e\u0301 password 🔑"]
)
def test_auth_preserves_valid_unicode_passwords_and_redacts_them(password):
    registration = RegisterRequest(
        name="Jane", email="jane@example.com", password=password
    )
    login = LoginRequest(email="jane@example.com", password=password)
    change = PasswordChangeRequest(current_password=password, new_password=password)

    for data, fields in (
        (registration, ["password"]),
        (login, ["password"]),
        (change, ["current_password", "new_password"]),
    ):
        for field in fields:
            assert getattr(data, field).get_secret_value() == password
        assert password not in repr(data)
        assert password not in data.model_dump_json()
