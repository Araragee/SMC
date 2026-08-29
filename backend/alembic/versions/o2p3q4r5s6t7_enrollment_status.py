"""Add enrollments.status for student-initiated enrollment requests

Revision ID: o2p3q4r5s6t7
Revises: n1o2p3q4r5s6
Create Date: 2026-08-29

Enrollment used to exist only because an admin created it, so the row's
existence implied approval. Students can now request enrollment with a
teacher, which means a row can exist while still awaiting a decision.

``status`` carries that: pending | active | rejected. ``is_active`` stays as
the soft-delete flag it already was — a rejected or pending enrollment is not
active, but neither is a cancelled one, so the two answer different questions.

Existing rows predate requests and were all admin-created, so they backfill to
'active'.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "o2p3q4r5s6t7"
down_revision: str | Sequence[str] | None = "n1o2p3q4r5s6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(table: str, column: str) -> bool:
    try:
        return any(c["name"] == column for c in sa.inspect(op.get_bind()).get_columns(table))
    except Exception:
        return False


def upgrade() -> None:
    if _has_column("enrollments", "status"):
        return
    with op.batch_alter_table("enrollments") as batch:
        batch.add_column(
            sa.Column(
                "status",
                sa.String(),
                nullable=False,
                server_default="active",
            )
        )
    # Anything already on the books was created by an admin, so it is approved.
    op.execute("UPDATE enrollments SET status = 'active' WHERE status IS NULL")


def downgrade() -> None:
    if not _has_column("enrollments", "status"):
        return
    with op.batch_alter_table("enrollments") as batch:
        batch.drop_column("status")
