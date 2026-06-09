"""Initial migration

Revision ID: e0c69a750bfa
Revises: 
Create Date: 2026-04-11 22:20:19.262980

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e0c69a750bfa'
# Rebased onto the 0001 baseline. Originally this migration was a no-op
# placeholder that ran against tables created at app boot by
# ``Base.metadata.create_all()``. Now that 0001 provides a complete
# baseline, this chain runs AFTER it; every step in the chain is
# wrapped in idempotency checks so it skips work already done by 0001.
down_revision: str | Sequence[str] | None = '0001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """No-op: tables are created by the 0001 baseline; this placeholder
    exists only for historical continuity with the legacy chain."""
    return None


def downgrade() -> None:
    return None
