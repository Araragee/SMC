"""Add compound index on sessions(status, start_time)

Revision ID: i6j7k8l9m0n1
Revises: h5i6j7k8l9m0
Create Date: 2026-06-04 00:00:00.000000

The session checker background task runs every 60 s and filters by
``status IN (...)`` + ``start_time`` comparisons.  A compound index
dramatically reduces the number of rows scanned for each tick.

Also adds (teacher_id, start_time) and (student_id, start_time) to
speed up per-user schedule lookups that span a time range.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "i6j7k8l9m0n1"
down_revision: str | None = "h5i6j7k8l9m0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("sessions") as batch_op:
        # Checker-loop primary filter: status then time ordering
        batch_op.create_index(
            "ix_sessions_status_start_time",
            ["status", "start_time"],
        )
        # Per-teacher schedule range queries
        batch_op.create_index(
            "ix_sessions_teacher_start_time",
            ["teacher_id", "start_time"],
        )
        # Per-student schedule range queries
        batch_op.create_index(
            "ix_sessions_student_start_time",
            ["student_id", "start_time"],
        )


def downgrade() -> None:
    with op.batch_alter_table("sessions") as batch_op:
        batch_op.drop_index("ix_sessions_status_start_time")
        batch_op.drop_index("ix_sessions_teacher_start_time")
        batch_op.drop_index("ix_sessions_student_start_time")
