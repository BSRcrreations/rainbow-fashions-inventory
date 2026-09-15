"""Database reservation shared by financially important retryable actions."""
from hashlib import sha256
import json

from sqlalchemy.exc import IntegrityError

from app.core.exceptions import bad_request, conflict
from app.models.destructive_action import DestructiveIdempotencyRecord


def reserve(db, user, action, key, payload):
    if not key or not key.strip():
        raise bad_request("Please retry from the confirmation screen.")
    key = key.strip()
    if len(key) > 120:
        raise bad_request("This confirmation could not be identified. Please reload.")
    digest = sha256(json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()
    filters = dict(store_id=user.store_id, user_id=user.id, action=action, idempotency_key=key)
    existing = db.query(DestructiveIdempotencyRecord).filter_by(**filters).first()
    if not existing:
        record = DestructiveIdempotencyRecord(**filters, request_hash=digest, response_snapshot={})
        try:
            # Keep the enclosing business transaction intact on a simultaneous retry.
            with db.begin_nested():
                db.add(record)
                db.flush()
            return record, False
        except IntegrityError:
            existing = db.query(DestructiveIdempotencyRecord).filter_by(**filters).first()
            if not existing:
                raise
    if existing.request_hash != digest:
        raise conflict("This confirmation was already used for different details. Reload and review before saving.")
    if not existing.response_snapshot:
        raise conflict("This confirmation is being processed. Please wait a moment.")
    return existing, True
