"""Hash passwords and derive the token digests used by authentication sessions."""

import hashlib
import hmac

from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

# Passwords can be guessed, so salted Argon2id hashes deliberately cost time to check.
password_hasher = PasswordHash.recommended()
# Unknown emails still pay the same verification cost as existing accounts.
DUMMY_PASSWORD_HASH = password_hasher.hash("huntly-unused-dummy-password")


def hash_password(password: str) -> str:
    """Return a salted password hash for storage; never store the raw password."""
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Check a password; an invalid stored hash counts as failed verification."""
    try:
        return password_hasher.verify(password, password_hash)
    except UnknownHashError, ValueError:
        return False


def digest_token(token: str) -> str:
    """Make the lookup digest stored in place of a raw session or CSRF token.

    Session tokens have 256 bits of randomness, so they do not need the slow
    password-hashing process used to resist guesses at human-chosen passwords.
    """
    return hashlib.sha256(token.encode()).hexdigest()


def csrf_token_for_session(token: str) -> str:
    """Recreate a separate CSRF token from the secret cookie.

    The fixed label separates this value from the session-token digest. The
    same cookie always yields the same CSRF token, so GET /auth/me can return
    it without storing the raw CSRF token in the database.
    """
    return hmac.new(token.encode(), b"huntly-csrf-v1", hashlib.sha256).hexdigest()
