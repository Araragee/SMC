"""Add composite index on notifications(user_id, is_read)

Revision ID: g4h5i6j7k8l9
Revises: f3a1b2c4d5e6
Create Date: 2026-05-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'g4h5i6j7k8l9'
down_revision: str | None = 'f3a1b2c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_index(table: str, index: str) -> bool:
    try:
        return any(ix.get("name") == index for ix in sa.inspect(op.get_bind()).get_indexes(table))
    except Exception:
        return False


def upgrade() -> None:
    # Idempotent: 0001 baseline already creates this index on fresh installs.
    if _has_index("notifications", "ix_notifications_user_unread"):
        return
    op.create_index(
        "ix_notifications_user_unread",
        "notifications",
        ["user_id", "is_read"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_user_unread", table_name="notifications")
