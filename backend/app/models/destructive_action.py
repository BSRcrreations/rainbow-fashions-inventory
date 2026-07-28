from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database.base import Base


class StoreSecuritySetting(Base):
    __tablename__ = "store_security_settings"

    store_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), primary_key=True)
    delete_password_hash: Mapped[Optional[str]] = mapped_column(String)
    require_password_for_sale_delete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    require_password_for_purchase_delete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_by: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class DeletePasswordAttempt(Base):
    __tablename__ = "delete_password_attempts"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    store_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)


class DestructiveActionAudit(Base):
    __tablename__ = "destructive_action_audits"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    store_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("stores.id", ondelete="RESTRICT"), nullable=False, index=True)
    user_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True)
    user_role: Mapped[Optional[str]] = mapped_column(String(32))
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    entity_type: Mapped[Optional[str]] = mapped_column(String(32))
    entity_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), index=True)
    reference: Mapped[Optional[str]] = mapped_column(String(180))
    original_status: Mapped[Optional[str]] = mapped_column(String(40))
    final_action: Mapped[Optional[str]] = mapped_column(String(40))
    record_counts: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    reversal_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    request_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    client_ip: Mapped[Optional[str]] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class DestructiveIdempotencyRecord(Base):
    __tablename__ = "destructive_idempotency_records"
    __table_args__ = (UniqueConstraint("store_id", "user_id", "action", "idempotency_key", name="uq_destructive_idempotency"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    store_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(120), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    response_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
