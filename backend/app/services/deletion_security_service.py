from __future__ import annotations

from passlib.hash import argon2
from passlib.exc import MissingBackendError

from app.core.config import get_settings


class DeletePasswordConfigurationError(Exception):
    pass


class DeletePasswordInvalidError(Exception):
    pass


def verify_delete_password(submitted_password: str) -> None:
    """Verify the environment-managed deletion credential without exposing it."""
    stored_hash = get_settings().delete_auth_password_hash
    if not stored_hash:
        raise DeletePasswordConfigurationError("Deletion-password protection is not configured.")
    if not submitted_password:
        raise DeletePasswordInvalidError("The deletion password is required.")
    try:
        password_matches = argon2.verify(submitted_password, stored_hash)
    except (MissingBackendError, TypeError, ValueError) as exc:
        raise DeletePasswordConfigurationError("The configured deletion-password hash is invalid.") from exc
    if not password_matches:
        raise DeletePasswordInvalidError("The deletion password is incorrect.")
