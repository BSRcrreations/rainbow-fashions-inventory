"""Read-only inventory reconciliation command. Run with an owner store user id."""
from __future__ import annotations

import argparse
import json
from uuid import UUID

from app.database.session import SessionLocal
from app.models.user import User
from app.services.inventory_reconciliation_service import InventoryReconciliationService


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only variant-stock reconciliation")
    parser.add_argument("--user-id", required=True, help="Owner or manager user UUID")
    args = parser.parse_args()
    db = SessionLocal()
    try:
        user = db.get(User, UUID(args.user_id))
        if not user or not user.is_active:
            raise SystemExit("Active user was not found")
        summary = InventoryReconciliationService(db).summary(user)
        print(json.dumps(summary.model_dump(), sort_keys=True))
        return 1 if summary.critical_mismatches else 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
