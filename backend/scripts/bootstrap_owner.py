#!/usr/bin/env python3
"""Create the first owner account without embedding credentials in source."""
from __future__ import annotations

import argparse
import getpass
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.database.session import SessionLocal
from app.models.enums import UserRole
from app.models.store import Store
from app.models.user import User


class BootstrapInputError(ValueError):
    """Raised when owner bootstrap input is missing or unsafe."""


@dataclass(frozen=True)
class BootstrapResult:
    created: bool
    message: str


def _required(value: str | None, label: str) -> str:
    value = (value or "").strip()
    if not value:
        raise BootstrapInputError(f"{label} is required.")
    return value


def validate_owner_email(email: str | None) -> str:
    email = _required(email, "Owner email")
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise BootstrapInputError("Owner email is invalid.")
    return email.lower()


def validate_password(password: str | None) -> str:
    password = _required(password, "Owner password")
    if len(password) < 12:
        raise BootstrapInputError("Owner password must be at least 12 characters.")
    if not re.search(r"[a-z]", password) or not re.search(r"[A-Z]", password):
        raise BootstrapInputError("Owner password must include upper- and lower-case letters.")
    if not re.search(r"\d", password) or not re.search(r"[^A-Za-z0-9]", password):
        raise BootstrapInputError("Owner password must include a number and a symbol.")
    return password


def bootstrap_owner(
    db: Session,
    *,
    email: str,
    password: str,
    store_name: str,
    store_code: str,
    owner_name: str = "Owner",
    update_existing: bool = False,
) -> BootstrapResult:
    """Create an owner once, or update it only when explicitly requested."""
    email = validate_owner_email(email)
    password = validate_password(password)
    store_name = _required(store_name, "Store name")
    store_code = _required(store_code, "Store code").upper()
    owner_name = _required(owner_name, "Owner name")

    existing_user = db.scalar(select(User).where(User.email == email))
    if existing_user is not None and not update_existing:
        return BootstrapResult(False, "Owner already exists; no changes made.")

    store = db.scalar(select(Store).where(Store.code == store_code))
    if store is None:
        store = Store(name=store_name, code=store_code, is_active=True)
        db.add(store)
        db.flush()
    else:
        store.is_active = True

    if existing_user is None:
        db.add(
            User(
                store_id=store.id,
                full_name=owner_name,
                email=email,
                password_hash=hash_password(password),
                role=UserRole.OWNER,
                is_active=True,
            )
        )
        db.commit()
        return BootstrapResult(True, "Owner bootstrap complete.")

    existing_user.store_id = store.id
    existing_user.full_name = owner_name
    existing_user.password_hash = hash_password(password)
    existing_user.role = UserRole.OWNER
    existing_user.is_active = True
    db.commit()
    return BootstrapResult(False, "Existing owner updated.")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create the initial owner account.")
    parser.add_argument("--email")
    parser.add_argument("--store-name")
    parser.add_argument("--store-code")
    parser.add_argument("--owner-name")
    parser.add_argument("--update-existing", action="store_true")
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    session_factory: Callable[[], Session] = SessionLocal,
    password_prompt: Callable[[str], str] = getpass.getpass,
    emit: Callable[[str], None] = print,
) -> int:
    args = _parser().parse_args(argv)
    environment = os.environ if environ is None else environ
    password = environment.get("OWNER_PASSWORD")
    if password is None:
        password = password_prompt("Owner password (input hidden): ")

    db: Session | None = None
    try:
        db = session_factory()
        result = bootstrap_owner(
            db,
            email=args.email or environment.get("OWNER_EMAIL"),
            password=password,
            store_name=args.store_name or environment.get("OWNER_STORE_NAME"),
            store_code=args.store_code or environment.get("OWNER_STORE_CODE"),
            owner_name=args.owner_name or environment.get("OWNER_NAME", "Owner"),
            update_existing=args.update_existing,
        )
    except BootstrapInputError as exc:
        emit(f"Owner bootstrap failed: {exc}")
        return 2
    except Exception:
        if db is not None:
            db.rollback()
        emit("Owner bootstrap failed; transaction rolled back.")
        return 1
    finally:
        if db is not None:
            db.close()

    emit(result.message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
