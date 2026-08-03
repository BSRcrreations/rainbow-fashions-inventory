from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database.base import Base


class ProductUpdateAudit(Base):
    """An immutable record of catalogue-only product edits.

    Stock is deliberately absent: changes to stock must be represented by a
    stock movement, not a product update.
    """

    __tablename__ = "product_update_audits"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    store_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("stores.id", ondelete="RESTRICT"), nullable=False, index=True)
    product_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    changed_by: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True)
    changed_by_role: Mapped[Optional[str]] = mapped_column(String(40))
    request_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    change_source: Mapped[str] = mapped_column(String(40), nullable=False)
    before_values: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    after_values: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
