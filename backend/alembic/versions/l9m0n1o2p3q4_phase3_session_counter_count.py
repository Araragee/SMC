"""Phase 3: add sessions.counter_count

Revision ID: l9m0n1o2p3q4
Revises: k8l9m0n1o2p3
Create Date: 2026-06-09

Adds an integer field to track the number of counter-proposals on a session
before forcing admin mediation.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "l9m0n1o2p3q4"
down_revision: str | Sequence[str] | None = "k8l9m0n1o2p3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(table: str, column: str) -> bool:
    try:
        return any(c["name"] == column for c in sa.inspect(op.get_bind()).get_columns(table))
    except Exception:
        return False


def upgrade() -> None:
    if _has_column("sessions", "counter_count"):
        return
    with op.batch_alter_table("sessions") as batch:
        batch.add_column(
            sa.Column(
                "counter_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )


def downgrade() -> None:
    if not _has_column("sessions", "counter_count"):
        return
    with op.batch_alter_table("sessions") as batch:
        batch.drop_column("counter_count")
