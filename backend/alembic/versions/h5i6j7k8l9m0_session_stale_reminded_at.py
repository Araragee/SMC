"""Add stale_reminded_at to sessions

Revision ID: h5i6j7k8l9m0
Revises: g4h5i6j7k8l9
Create Date: 2026-05-24

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'h5i6j7k8l9m0'
down_revision: str | None = 'g4h5i6j7k8l9'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(table: str, column: str) -> bool:
    try:
        return any(c["name"] == column for c in sa.inspect(op.get_bind()).get_columns(table))
    except Exception:
        return False


def upgrade() -> None:
    # Idempotent: 0001 baseline already adds this column on fresh installs.
    if _has_column("sessions", "stale_reminded_at"):
        return
    op.add_column(
        'sessions',
        sa.Column('stale_reminded_at', sa.DateTime(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('sessions', 'stale_reminded_at')
