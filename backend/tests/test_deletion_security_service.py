from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.core.config import Settings
from app.services.deletion_security_service import DeletePasswordConfigurationError, DeletePasswordInvalidError, verify_delete_password
from passlib.hash import argon2


class DeletionSecurityServiceTests(unittest.TestCase):
    def test_argon2_hash_is_accepted(self) -> None:
        settings = Settings(delete_auth_password_hash="$argon2id$v=19$m=65536,t=3,p=4$c2FsdHNhbHQ$VWE7xMBbrFi9JpZY10MCkw")
        self.assertTrue(settings.delete_auth_password_hash.startswith("$argon2"))

    def test_plain_text_hash_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            Settings(delete_auth_password_hash="not-a-password-hash")

    def test_missing_hash_is_a_safe_configuration_error(self) -> None:
        with patch("app.services.deletion_security_service.get_settings", return_value=SimpleNamespace(delete_auth_password_hash=None)):
            with self.assertRaises(DeletePasswordConfigurationError):
                verify_delete_password("anything")

    def test_empty_password_is_rejected_without_exposing_hash(self) -> None:
        with patch("app.services.deletion_security_service.get_settings", return_value=SimpleNamespace(delete_auth_password_hash="$argon2id$redacted")):
            with self.assertRaises(DeletePasswordInvalidError) as context:
                verify_delete_password("")
        self.assertNotIn("argon2", str(context.exception).lower())

    def test_correct_argon2_password_succeeds_and_wrong_password_fails(self) -> None:
        password_hash = argon2.hash("test-delete-password")
        with patch("app.services.deletion_security_service.get_settings", return_value=SimpleNamespace(delete_auth_password_hash=password_hash)):
            verify_delete_password("test-delete-password")
            with self.assertRaises(DeletePasswordInvalidError):
                verify_delete_password("wrong-password")
