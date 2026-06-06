"""Add stale_reminded_at to sessions

Revision ID: h5i6j7k8l9m0
Revises: g4h5i6j7k8l9
Create Date: 2026-05-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'h5i6j7k8l9m0'
down_revision: str | None = 'g4h5i6j7k8l9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'sessions',
        sa.Column('stale_reminded_at', sa.DateTime(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('sessions', 'stale_reminded_at')
