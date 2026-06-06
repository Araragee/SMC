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


def upgrade() -> None:
    op.create_index(
        "ix_notifications_user_unread",
        "notifications",
        ["user_id", "is_read"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_user_unread", table_name="notifications")
