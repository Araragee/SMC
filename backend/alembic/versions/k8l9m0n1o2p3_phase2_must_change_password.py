"""Phase 2: add users.must_change_password

Revision ID: k8l9m0n1o2p3
Revises: j7k8l9m0n1o2
Create Date: 2026-06-09

Adds a boolean flag that gates the SPA: when true the user is forced
into a /change-password flow before they can use any other view.

Set true by:
  - The default-admin seed in backend/main.py:_seed_defaults, so the
    very first login on a fresh deploy can't operate with the boot-time
    password baked into .env.
  - Admin-initiated password resets (future work).

The column is idempotent (skipped if 0001 already added it on a fresh
install) so this migration is safe to run from either lineage.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "k8l9m0n1o2p3"
down_revision: str | Sequence[str] | None = "j7k8l9m0n1o2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(table: str, column: str) -> bool:
    try:
        return any(c["name"] == column for c in sa.inspect(op.get_bind()).get_columns(table))
    except Exception:
        return False


def upgrade() -> None:
    if _has_column("users", "must_change_password"):
        return
    # batch_alter_table for SQLite compatibility (no native ADD COLUMN with
    # server_default on every dialect).
    with op.batch_alter_table("users") as batch:
        batch.add_column(
            sa.Column(
                "must_change_password",
                sa.Boolean(),
                nullable=False,
                server_default="0",
            )
        )


def downgrade() -> None:
    if not _has_column("users", "must_change_password"):
        return
    with op.batch_alter_table("users") as batch:
        batch.drop_column("must_change_password")
