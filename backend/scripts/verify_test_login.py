#!/usr/bin/env python3
"""Verify a protected TEST owner credential without printing it or its token."""
from __future__ import annotations

import argparse
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def verify(base_url: str, email: str, password: str) -> None:
    body = json.dumps({"email": email, "password": password}).encode("utf-8")
    request = Request(
        f"{base_url.rstrip('/')}/auth/login",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=20) as response:
            payload = json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f"TEST owner authentication failed with HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError("TEST owner authentication endpoint is unavailable") from exc

    user = payload.get("user") if isinstance(payload, dict) else None
    if not isinstance(user, dict) or not payload.get("access_token"):
        raise RuntimeError("TEST owner authentication returned an invalid response")
    if user.get("role") != "OWNER" or user.get("is_active") is not True or not user.get("store_id"):
        raise RuntimeError("TEST owner account is not active, owner-scoped, and store-assigned")
    print("TEST owner authentication: PASS (role=OWNER, store_assigned=true)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a protected TEST owner login.")
    parser.add_argument("--base-url", required=True)
    args = parser.parse_args()
    email = os.environ.get("TEST_OWNER_EMAIL", "").strip()
    password = os.environ.get("TEST_OWNER_PASSWORD", "")
    if not email or not password:
        raise RuntimeError("TEST owner credentials are not available to the deployment runner")
    verify(args.base_url, email, password)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
