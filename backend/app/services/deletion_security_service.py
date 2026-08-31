from __future__ import annotations

from passlib.hash import argon2
from passlib.exc import MissingBackendError

from app.core.config import get_settings


class DeletePasswordConfigurationError(Exception):
    pass


class DeletePasswordInvalidError(Exception):
    pass


def hash_delete_password(password: str) -> str:
    """Create the only value that may be persisted for an Owner deletion password."""
    try:
        return argon2.hash(password)
    except MissingBackendError as exc:
        raise DeletePasswordConfigurationError("Deletion-password protection is unavailable.") from exc


def verify_delete_password_hash(submitted_password: str, stored_hash: str | None) -> None:
    """Verify a persisted Argon2 deletion-password hash without exposing it."""
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


def verify_delete_password(submitted_password: str) -> None:
    """Verify the legacy environment-managed deletion credential when configured."""
    verify_delete_password_hash(submitted_password, get_settings().delete_auth_password_hash)
