"""Add created_at and updated_at to Session

Revision ID: d1e2f3a4b5c6
Revises: c9d2f5a7e8b3
Create Date: 2026-05-23 00:00:00.000000

Adds two timestamp columns to the ``sessions`` table:
  - ``created_at``: set to the current UTC time on insert (backfilled for
    existing rows using the session's ``start_time`` as a reasonable proxy).
  - ``updated_at``: same as ``created_at`` on insert; the ORM ``onupdate``
    hook keeps it current on every subsequent write.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d1e2f3a4b5c6"
down_revision = "c9d2f5a7e8b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("sessions") as batch:
        batch.add_column(
            sa.Column("created_at", sa.DateTime(), nullable=True)
        )
        batch.add_column(
            sa.Column("updated_at", sa.DateTime(), nullable=True)
        )

    # Backfill existing rows: use start_time as a reasonable proxy for
    # when the session record was originally created/last modified.
    op.execute(
        "UPDATE sessions SET created_at = start_time WHERE created_at IS NULL"
    )
    op.execute(
        "UPDATE sessions SET updated_at = start_time WHERE updated_at IS NULL"
    )


def downgrade() -> None:
    with op.batch_alter_table("sessions") as batch:
        batch.drop_column("updated_at")
        batch.drop_column("created_at")
