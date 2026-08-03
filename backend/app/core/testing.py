"""Safety checks shared by test-only data tooling.

This deliberately lives outside production business services so the guard can be
used before a script opens a SQLAlchemy session.
"""
from __future__ import annotations

from urllib.parse import urlparse


class UatEnvironmentError(RuntimeError):
    """Raised when a destructive UAT command targets a non-test database."""


def assert_test_database(app_env: str, database_url: str) -> str:
    if app_env.strip().lower() != "testing":
        raise UatEnvironmentError("Refusing test-data operation because APP_ENV is not testing.")

    parsed = urlparse(database_url)
    database_name = parsed.path.rsplit("/", 1)[-1]
    host = (parsed.hostname or "").lower()
    if not database_name.endswith("_test"):
        raise UatEnvironmentError("Refusing test-data operation because database name does not end with _test.")
    blocked_host_fragments = ("178.238.237.182", "contaboserver", "rainbow-fashions.in", "production", "prod-db")
    if any(fragment in host for fragment in blocked_host_fragments):
        raise UatEnvironmentError("Refusing test-data operation because the database host looks like production.")
    return database_name
