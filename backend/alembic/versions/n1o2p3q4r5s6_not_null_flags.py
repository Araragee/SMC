"""Make enrollments.is_active and sessions.counter_count NOT NULL

Revision ID: n1o2p3q4r5s6
Revises: m0n1o2p3q4r5
Create Date: 2026-08-21

The models declare both columns NOT NULL, but the migrations that introduced
them left the database nullable — ``alembic check`` reported the drift. A NULL
in either column breaks code that treats them as a plain bool/int, so backfill
the existing rows and tighten the constraint to match the model.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "n1o2p3q4r5s6"
down_revision: str | Sequence[str] | None = "m0n1o2p3q4r5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUMNS = (
    ("enrollments", "is_active", sa.Boolean(), "true", "false"),
    ("sessions", "counter_count", sa.Integer(), "0", "0"),
)


def _has_column(table: str, column: str) -> bool:
    try:
        return any(c["name"] == column for c in sa.inspect(op.get_bind()).get_columns(table))
    except Exception:
        return False


def upgrade() -> None:
    for table, column, type_, default, _ in _COLUMNS:
        if not _has_column(table, column):
            continue
        op.execute(f"UPDATE {table} SET {column} = {default} WHERE {column} IS NULL")
        op.alter_column(table, column, existing_type=type_, nullable=False)


def downgrade() -> None:
    for table, column, type_, _, _unused in _COLUMNS:
        if not _has_column(table, column):
            continue
        op.alter_column(table, column, existing_type=type_, nullable=True)
