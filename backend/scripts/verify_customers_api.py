"""Exercise the authenticated Customers list route against the active database.

This TEST/verification helper makes a read-only request with an explicit
reference ID. It prints only the safe API response supplied to a client.
"""

from __future__ import annotations

import json
import sys

from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.database.session import SessionLocal
from app.main import app
from app.models.user import User


REQUEST_ID = "test-customers-api-verification"


def main() -> int:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.store_id.is_not(None)).first()
    finally:
        db.close()
    if user is None:
        raise RuntimeError("TEST customer verification requires a store-assigned user")

    app.dependency_overrides[get_current_user] = lambda: user
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/api/v1/customers?search=", headers={"X-Request-ID": REQUEST_ID})
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    print(json.dumps({
        "endpoint": "GET /api/v1/customers?search=",
        "http_status": response.status_code,
        "request_id": response.headers.get("X-Request-ID"),
        "response": response.json(),
    }, sort_keys=True))
    return 0 if response.status_code == 200 else 1


if __name__ == "__main__":
    sys.exit(main())
