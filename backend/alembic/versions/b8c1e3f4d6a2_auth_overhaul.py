"""auth overhaul: refresh tokens, password reset, email verify, 2FA

Revision ID: b8c1e3f4d6a2
Revises: a7b9c2d4e8f1
Create Date: 2026-05-17
"""
import sqlalchemy as sa

from alembic import op

revision = "b8c1e3f4d6a2"
down_revision = "a7b9c2d4e8f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # users: new auth cols
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("email_verified", sa.Boolean(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("email_verification_token_hash", sa.String(), nullable=True))
        batch.add_column(sa.Column("totp_secret", sa.String(), nullable=True))
        batch.add_column(sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default="0"))

    # refresh_tokens
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"])

    # password_reset_tokens
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])
    op.create_index("ix_password_reset_tokens_token_hash", "password_reset_tokens", ["token_hash"])


def downgrade() -> None:
    op.drop_index("ix_password_reset_tokens_token_hash", table_name="password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_user_id", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
    op.drop_index("ix_refresh_tokens_token_hash", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("totp_enabled")
        batch.drop_column("totp_secret")
        batch.drop_column("email_verification_token_hash")
        batch.drop_column("email_verified")
