"""Add FK indexes and Session.version for optimistic locking

Revision ID: a7b9c2d4e8f1
Revises: f3a1b2c4d5e6
Create Date: 2026-05-16 00:00:00.000000

This migration:
  1. Adds an integer ``version`` column to ``sessions`` for optimistic locking
     (managed via SQLAlchemy ``version_id_col``).
  2. Adds indexes on every ForeignKey column that did not already carry one,
     to speed up the joins/filter patterns hit by the per-user session and
     payment queries.

NOTE: the brute-force lockout fields (``failed_login_count`` / ``locked_until``)
on ``users`` are added in a separate migration owned by the auth-hardening
agent. They are NOT touched here.
"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7b9c2d4e8f1"
down_revision: str | None = "f3a1b2c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# (table, column, index_name) tuples for FK indexes we want to add.
_FK_INDEXES: list[tuple[str, str, str]] = [
    ("user_instruments", "user_id", "ix_user_instruments_user_id"),
    ("user_instruments", "instrument_id", "ix_user_instruments_instrument_id"),
    ("teacher_students", "teacher_id", "ix_teacher_students_teacher_id"),
    ("teacher_students", "student_id", "ix_teacher_students_student_id"),
    ("users", "role_id", "ix_users_role_id"),
    ("sessions", "teacher_id", "ix_sessions_teacher_id"),
    ("sessions", "student_id", "ix_sessions_student_id"),
    ("sessions", "start_time", "ix_sessions_start_time"),
    ("sessions", "status", "ix_sessions_status"),
    ("sessions", "proposed_by", "ix_sessions_proposed_by"),
    ("sessions", "instrument_id", "ix_sessions_instrument_id"),
    ("enrollments", "student_id", "ix_enrollments_student_id"),
    ("enrollments", "teacher_id", "ix_enrollments_teacher_id"),
    ("homework", "session_id", "ix_homework_session_id"),
    ("session_proofs", "session_id", "ix_session_proofs_session_id"),
    ("session_proofs", "uploader_id", "ix_session_proofs_uploader_id"),
    ("payments", "student_id", "ix_payments_student_id"),
    ("notifications", "user_id", "ix_notifications_user_id"),
    ("instrument_products", "category_id", "ix_instrument_products_category_id"),
    ("orders", "approved_by", "ix_orders_approved_by"),
    ("order_items", "order_id", "ix_order_items_order_id"),
    ("order_items", "product_id", "ix_order_items_product_id"),
    ("conversation_participants", "conversation_id", "ix_conv_participants_conversation_id"),
    ("conversation_participants", "user_id", "ix_conv_participants_user_id"),
    ("messages", "conversation_id", "ix_messages_conversation_id"),
    ("messages", "sender_id", "ix_messages_sender_id"),
    ("activity_logs", "actor_id", "ix_activity_logs_actor_id"),
]


def upgrade() -> None:
    # 1. Optimistic locking column on sessions. batch_alter_table is used for
    #    SQLite compatibility (no native ADD COLUMN with server_default of an
    #    arbitrary expression on every dialect).
    with op.batch_alter_table("sessions") as batch:
        batch.add_column(
            sa.Column(
                "version",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )

    # 2. Foreign-key indexes.
    for table, column, index_name in _FK_INDEXES:
        op.create_index(index_name, table, [column], unique=False)


def downgrade() -> None:
    for _table, _column, index_name in reversed(_FK_INDEXES):
        op.drop_index(index_name, table_name=_table)

    with op.batch_alter_table("sessions") as batch:
        batch.drop_column("version")
