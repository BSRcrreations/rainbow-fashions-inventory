from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database.base import Base


class CatalogMigrationImport(Base):
    """Server-side evidence and idempotency guard for a TEST catalog package."""

    __tablename__ = "catalog_migration_imports"
    __table_args__ = (
        UniqueConstraint("store_id", "package_id", name="uq_catalog_migration_import_store_package"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    store_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("stores.id", ondelete="RESTRICT"), nullable=False, index=True)
    package_id: Mapped[str] = mapped_column(String(80), nullable=False)
    package_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    mode: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source_database: Mapped[str] = mapped_column(String(120), nullable=False)
    source_git_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    executed_by: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    manifest_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    summary_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    failure_details: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
