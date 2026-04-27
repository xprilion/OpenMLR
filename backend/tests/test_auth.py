"""Tests for openmlr.auth.security — password hashing and JWT tokens."""

from datetime import UTC

import pytest
from jose import jwt

from openmlr.auth.security import (
    ALGORITHM,
    SECRET_KEY,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


# Override the autouse DB fixture from conftest — these tests are pure unit tests.
@pytest.fixture(autouse=True)
def _setup_db():
    yield


# ── hash_password ──────────────────────────────────────────────────────────


class TestHashPassword:
    def test_returns_valid_bcrypt_hash(self):
        hashed = hash_password("my_secret")
        # bcrypt hashes start with $2b$ (or $2a$/$2y$) and are 60 chars
        assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
        assert len(hashed) == 60

    def test_different_calls_produce_different_hashes(self):
        h1 = hash_password("same_password")
        h2 = hash_password("same_password")
        assert h1 != h2  # different salts each time


# ── verify_password ────────────────────────────────────────────────────────


class TestVerifyPassword:
    def test_correct_password_returns_true(self):
        hashed = hash_password("correct_horse")
        assert verify_password("correct_horse", hashed) is True

    def test_wrong_password_returns_false(self):
        hashed = hash_password("correct_horse")
        assert verify_password("wrong_horse", hashed) is False

    def test_empty_password(self):
        hashed = hash_password("")
        assert verify_password("", hashed) is True
        assert verify_password("notempty", hashed) is False


# ── create_access_token ────────────────────────────────────────────────────


class TestCreateAccessToken:
    def test_returns_string(self):
        token = create_access_token(user_id=1, username="alice")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_token_is_valid_jwt(self):
        token = create_access_token(user_id=42, username="bob")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "42"
        assert payload["username"] == "bob"
        assert "exp" in payload

    def test_user_id_stored_as_string(self):
        token = create_access_token(user_id=999, username="carol")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "999"


# ── decode_access_token ────────────────────────────────────────────────────


class TestDecodeAccessToken:
    def test_decodes_valid_token(self):
        token = create_access_token(user_id=7, username="dave")
        result = decode_access_token(token)
        assert result is not None
        assert result["sub"] == "7"
        assert result["username"] == "dave"

    def test_returns_none_for_garbage_token(self):
        assert decode_access_token("not.a.jwt") is None

    def test_returns_none_for_empty_string(self):
        assert decode_access_token("") is None

    def test_returns_none_for_wrong_secret(self):
        # Encode with a different secret
        payload = {"sub": "1", "username": "eve"}
        bad_token = jwt.encode(payload, "wrong-secret-key", algorithm=ALGORITHM)
        assert decode_access_token(bad_token) is None

    def test_returns_none_for_expired_token(self):
        from datetime import datetime, timedelta

        expired_payload = {
            "sub": "1",
            "username": "frank",
            "exp": datetime.now(UTC) - timedelta(hours=1),
        }
        expired_token = jwt.encode(expired_payload, SECRET_KEY, algorithm=ALGORITHM)
        assert decode_access_token(expired_token) is None
