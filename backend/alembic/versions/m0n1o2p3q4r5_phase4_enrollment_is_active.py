"""Phase 4: add enrollments.is_active

Revision ID: m0n1o2p3q4r5
Revises: l9m0n1o2p3q4
Create Date: 2026-06-09

Adds a boolean flag to track whether an enrollment is active (for soft-deletes).
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "m0n1o2p3q4r5"
down_revision: str | Sequence[str] | None = "l9m0n1o2p3q4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(table: str, column: str) -> bool:
    try:
        return any(c["name"] == column for c in sa.inspect(op.get_bind()).get_columns(table))
    except Exception:
        return False


def upgrade() -> None:
    if _has_column("enrollments", "is_active"):
        return
    with op.batch_alter_table("enrollments") as batch:
        batch.add_column(
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default="1",
            )
        )


def downgrade() -> None:
    if not _has_column("enrollments", "is_active"):
        return
    with op.batch_alter_table("enrollments") as batch:
        batch.drop_column("is_active")
