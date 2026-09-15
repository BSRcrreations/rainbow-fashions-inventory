"""Optional real PostgreSQL regressions, isolated by an outer transaction.

Use only a migrated, disposable localhost database ending in _test. Application
commits release a savepoint; the fixture always rolls back the outer transaction.
"""
import os
from urllib.parse import urlparse

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.testing import assert_test_database


@pytest.fixture
def pg_db():
    url = os.environ.get("RAINBOW_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set RAINBOW_TEST_DATABASE_URL to a disposable migrated PostgreSQL database.")
    assert_test_database("testing", url)
    if urlparse(url).hostname not in {"127.0.0.1", "localhost", "postgres"}:
        pytest.fail("Database regressions must run on the isolated local/CI test database.")
    engine = create_engine(url)
    with engine.connect() as connection:
        outer = connection.begin()
        db = Session(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False)
        try:
            yield db
        finally:
            db.close()
            outer.rollback()
    engine.dispose()
