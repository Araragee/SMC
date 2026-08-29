"""Drop the teacher_students table

Revision ID: p3q4r5s6t7u8
Revises: o2p3q4r5s6t7
Create Date: 2026-08-29

Assignments and enrollments were two overlapping answers to "which students
belong to this teacher". Booking, credits, payment scope and record access all
key off enrollments now, leaving assignments as a second roster that nothing
consulted but an admin could still edit — so the two could disagree with no
way to tell which was right.

Downgrade recreates the table but cannot recover its rows; the relationships
it held are represented by enrollments.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "p3q4r5s6t7u8"
down_revision: str | Sequence[str] | None = "o2p3q4r5s6t7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(table: str) -> bool:
    try:
        return table in sa.inspect(op.get_bind()).get_table_names()
    except Exception:
        return False


def upgrade() -> None:
    if not _has_table("teacher_students"):
        return
    op.drop_table("teacher_students")


def downgrade() -> None:
    if _has_table("teacher_students"):
        return
    op.create_table(
        "teacher_students",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("teacher_id", sa.Integer(), nullable=True),
        sa.Column("student_id", sa.Integer(), nullable=True),
        sa.Column("assigned_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["teacher_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_teacher_students_teacher_id", "teacher_students", ["teacher_id"])
    op.create_index("ix_teacher_students_student_id", "teacher_students", ["student_id"])
