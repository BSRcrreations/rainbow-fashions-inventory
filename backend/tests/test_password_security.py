from __future__ import annotations

import secrets
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.security import hash_password, verify_password
from app.schemas.auth import LoginRequest


def _generated_password() -> str:
    return f"Test!{secrets.token_urlsafe(24)}9a"


def test_password_hashes_verify_without_exposing_plaintext():
    password = _generated_password()
    password_hash = hash_password(password)

    assert password_hash != password
    assert verify_password(password, password_hash)
    assert not verify_password(_generated_password(), password_hash)


def test_password_hashes_use_unique_salts():
    password = _generated_password()

    first_hash = hash_password(password)
    second_hash = hash_password(password)

    assert first_hash != second_hash
    assert verify_password(password, first_hash)
    assert verify_password(password, second_hash)


def test_empty_password_follows_login_request_validation():
    with pytest.raises(ValidationError):
        LoginRequest(email=f"user-{uuid4().hex}@example.test", password="")
