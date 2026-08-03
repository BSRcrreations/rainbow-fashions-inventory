from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database.base import Base


class StockImport(Base):
    __tablename__ = "stock_imports"
    __table_args__ = (UniqueConstraint("store_id", "idempotency_key", name="uq_stock_import_store_idempotency"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    store_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("stores.id", ondelete="RESTRICT"), nullable=False, index=True)
    import_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True, default="OPENING_STOCK")
    status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    source_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    uploaded_by: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    confirmed_by: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    request_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    summary: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    failure_details: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class StockImportRow(Base):
    __tablename__ = "stock_import_rows"
    __table_args__ = (UniqueConstraint("stock_import_id", "row_number", name="uq_stock_import_row_number"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    stock_import_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("stock_imports.id", ondelete="CASCADE"), nullable=False, index=True)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    sku: Mapped[Optional[str]] = mapped_column(String(80))
    barcode: Mapped[Optional[str]] = mapped_column(String(80))
    quantity: Mapped[Optional[int]] = mapped_column(Integer)
    product_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), index=True)
    product_variant_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("product_variants.id", ondelete="RESTRICT"), index=True)
    validation_errors: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    normalized_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    opening_stock_movement_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("stock_history.id", ondelete="SET NULL"), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class StockImportBackup(Base):
    __tablename__ = "stock_import_backups"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    stock_import_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("stock_imports.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    backup_path: Mapped[Optional[str]] = mapped_column(String(1000))
    sha256: Mapped[Optional[str]] = mapped_column(String(64))
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer)
    backup_metadata: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    error_code: Mapped[Optional[str]] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class StockImportRollback(Base):
    __tablename__ = "stock_import_rollbacks"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    stock_import_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("stock_imports.id", ondelete="RESTRICT"), nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    requested_by: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    completed_by: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    conflict_report: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    request_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
