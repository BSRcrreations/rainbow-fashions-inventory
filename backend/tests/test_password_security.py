from __future__ import annotations

import secrets
from unittest.mock import Mock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.security import hash_password, verify_password
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.auth import LoginRequest
from app.services.auth_service import AuthService


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


def test_login_normalizes_email_case_before_lookup():
    password = _generated_password()
    user = User(
        id=uuid4(),
        store_id=uuid4(),
        full_name="Test Owner",
        email="owner@rainbow-fashions.com",
        password_hash=hash_password(password),
        role=UserRole.OWNER,
        is_active=True,
    )
    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = user

    AuthService(db).login(LoginRequest(email="Owner@Rainbow-Fashions.com", password=password))

    comparison = db.query.return_value.filter.call_args.args[0]
    assert comparison.right.value == "owner@rainbow-fashions.com"
