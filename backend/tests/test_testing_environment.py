import pytest

from app.core.testing import UatEnvironmentError, assert_test_database


def test_test_database_guard_accepts_isolated_test_database():
    assert assert_test_database(
        "testing",
        "postgresql+psycopg://rainbow_test_user:test@127.0.0.1:5433/rainbow_inventory_test",
    ) == "rainbow_inventory_test"


@pytest.mark.parametrize(
    ("app_env", "database_url"),
    [
        ("production", "postgresql+psycopg://user:password@127.0.0.1:5433/rainbow_inventory_test"),
        ("testing", "postgresql+psycopg://user:password@127.0.0.1:5433/rainbow_inventory"),
        ("testing", "postgresql+psycopg://user:password@178.238.237.182:5432/rainbow_inventory_test"),
    ],
)
def test_test_database_guard_rejects_non_isolated_targets(app_env: str, database_url: str):
    with pytest.raises(UatEnvironmentError):
        assert_test_database(app_env, database_url)
