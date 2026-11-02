import pytest

from app.core.security import (
    csrf_token_for_session,
    digest_token,
    hash_password,
    verify_password,
)


def test_password_hashes_use_argon2_and_random_salts():
    password = "A long test password 42!"
    first = hash_password(password)
    second = hash_password(password)
    assert first.startswith("$argon2id$")
    assert first != second
    assert verify_password(password, first)
    assert not verify_password("Different password 42!", first)


def test_password_whitespace_is_significant():
    password = "  A long test password 42!  "
    encoded = hash_password(password)
    assert verify_password(password, encoded)
    assert not verify_password(password.strip(), encoded)


@pytest.mark.parametrize(
    "encoded",
    [
        "",
        "invalid-hash",
        "$argon2id$",
        "$argon2id$v=19$m=abc,t=1,p=1$saltsalt$hashhash",
        "$argon2id$v=19$m=65536,t=3,p=4$c2FsdA$aW52YWxpZA",
        "$2b$12$invalidhash",
    ],
)
def test_malformed_password_hash_fails_closed(encoded):
    assert not verify_password("A long test password 42!", encoded)


def test_token_digests_are_stable_and_do_not_store_the_token():
    token = "a-random-session-token"
    assert len(digest_token(token)) == 64
    assert digest_token(token) == digest_token(token)
    assert digest_token(token) != digest_token(token + "other")
    assert token not in digest_token(token)


def test_csrf_token_is_bound_to_its_session_and_domain_separated():
    token = "a-random-session-token"
    csrf = csrf_token_for_session(token)
    assert len(csrf) == 64
    assert csrf == csrf_token_for_session(token)
    assert csrf != csrf_token_for_session(token + "other")
    assert csrf != digest_token(token)
    assert csrf != token
