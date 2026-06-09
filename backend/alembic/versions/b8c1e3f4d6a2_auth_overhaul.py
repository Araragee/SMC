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


def _inspect():
    return sa.inspect(op.get_bind())


def _has_table(name: str) -> bool:
    try:
        return name in _inspect().get_table_names()
    except Exception:
        return False


def _has_column(table: str, column: str) -> bool:
    try:
        return any(c["name"] == column for c in _inspect().get_columns(table))
    except Exception:
        return False


def upgrade() -> None:
    # users: new auth cols. Idempotent — 0001 baseline already adds them on
    # fresh installs.
    cols_to_add = []
    if not _has_column("users", "email_verified"):
        cols_to_add.append(sa.Column("email_verified", sa.Boolean(), nullable=False, server_default="0"))
    if not _has_column("users", "email_verification_token_hash"):
        cols_to_add.append(sa.Column("email_verification_token_hash", sa.String(), nullable=True))
    if not _has_column("users", "totp_secret"):
        cols_to_add.append(sa.Column("totp_secret", sa.String(), nullable=True))
    if not _has_column("users", "totp_enabled"):
        cols_to_add.append(sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default="0"))
    if cols_to_add:
        with op.batch_alter_table("users") as batch:
            for col in cols_to_add:
                batch.add_column(col)

    # refresh_tokens
    if _has_table("refresh_tokens"):
        return
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
