"""Merge deployment stock-import and repository-hardening migration heads."""

from __future__ import annotations


revision = "20260804_0040"
down_revision = ("20260803_0039", "20260804_0039")
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Merge-only revision; both parent schema changes remain intact."""


def downgrade() -> None:
    """Merge-only revision; Alembic traverses back to both parents."""
