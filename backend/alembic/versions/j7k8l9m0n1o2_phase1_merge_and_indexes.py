"""Phase 1: merge multiple heads and add new indexes

Revision ID: j7k8l9m0n1o2
Revises: 0001, d1e2f3a4b5c6, i6j7k8l9m0n1
Create Date: 2026-06-09

Two things happen here:

1. **Merge migration.** Prior to this revision the migration graph had three
   heads, which made ``alembic upgrade head`` fail outright:
     - ``0001`` — fresh-install baseline snapshot (creates every table inline).
     - ``d1e2f3a4b5c6`` — tail of the auth/session-timestamps chain.
     - ``i6j7k8l9m0n1`` — tail of the shop/index chain.
   This revision lists all three as its ``down_revision`` so Alembic recognises
   it as a no-op merge that converges them into a single head.

2. **New indexes** introduced in Phase 1 of the foundation cleanup:
     - ``ix_sessions_status_end_time`` — the ``session_checker_task`` filters
       overdue sessions every minute by ``status = 'scheduled' AND end_time < now``;
       the existing ``ix_sessions_status_start_time`` doesn't help that query.
     - ``ix_notifications_created_at`` — supports the planned 90-day purge
       (Phase 4) and date-range filters in the notifications UI.

Both index creations are wrapped in idempotence checks because:
  - Fresh installs that start from ``0001`` already have the per-column indexes;
    the new compound + created_at indexes still need creating.
  - Existing installs that climbed the e0c69a chain have neither.
"""
from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import inspect

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "j7k8l9m0n1o2"
# Tuple form tells Alembic this is a merge across multiple parents.
# "phase1_helper" is the no-op idempotency-helpers script (also a child of 0001).
down_revision: tuple[str, ...] = ("phase1_helper", "d1e2f3a4b5c6", "i6j7k8l9m0n1")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _existing_indexes(table: str) -> set[str]:
    """Return the set of existing index names on a table.

    Lets us make this migration idempotent across the multiple migration
    chains it merges — each chain has created a different subset of indexes
    already, and we don't want a duplicate-name error to abort the merge.
    """
    bind = op.get_bind()
    insp = inspect(bind)
    try:
        return {ix["name"] for ix in insp.get_indexes(table) if ix.get("name")}
    except Exception:
        return set()


def upgrade() -> None:
    # ── sessions(status, end_time) ─────────────────────────────────────────
    existing = _existing_indexes("sessions")
    if "ix_sessions_status_end_time" not in existing:
        op.create_index(
            "ix_sessions_status_end_time",
            "sessions",
            ["status", "end_time"],
        )

    # ── notifications(created_at) ──────────────────────────────────────────
    existing = _existing_indexes("notifications")
    if "ix_notifications_created_at" not in existing:
        op.create_index(
            "ix_notifications_created_at",
            "notifications",
            ["created_at"],
        )


def downgrade() -> None:
    existing = _existing_indexes("notifications")
    if "ix_notifications_created_at" in existing:
        op.drop_index("ix_notifications_created_at", table_name="notifications")

    existing = _existing_indexes("sessions")
    if "ix_sessions_status_end_time" in existing:
        op.drop_index("ix_sessions_status_end_time", table_name="sessions")
