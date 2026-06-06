"""push subscriptions table

Revision ID: c9d2f5a7e8b3
Revises: b8c1e3f4d6a2
Create Date: 2026-05-17
"""
from alembic import op
import sqlalchemy as sa


revision = "c9d2f5a7e8b3"
down_revision = "b8c1e3f4d6a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "push_subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("endpoint", sa.String(), nullable=False, unique=True),
        sa.Column("keys_p256dh", sa.String(), nullable=False),
        sa.Column("keys_auth", sa.String(), nullable=False),
        sa.Column("user_agent", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_push_subscriptions_user_id", "push_subscriptions", ["user_id"])
    op.create_index("ix_push_subscriptions_endpoint", "push_subscriptions", ["endpoint"])


def downgrade() -> None:
    op.drop_index("ix_push_subscriptions_endpoint", table_name="push_subscriptions")
    op.drop_index("ix_push_subscriptions_user_id", table_name="push_subscriptions")
    op.drop_table("push_subscriptions")
