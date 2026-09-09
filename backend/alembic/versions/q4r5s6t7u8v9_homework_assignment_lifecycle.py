"""Give homework a full assignment lifecycle

Revision ID: q4r5s6t7u8v9
Revises: p3q4r5s6t7u8
Create Date: 2026-09-09

The table only recorded a description, a completion boolean and an optional
file, which is enough for a student to submit something and nothing else: no
due date, no record of who assigned it, and nowhere for a teacher to put a
grade or a remark. This adds the columns the teacher-side workflow needs.

Every column is nullable and no data is rewritten, so existing rows stay valid
and keep behaving exactly as before — an old row simply reads as "assigned,
never reviewed, no due date". ``downgrade`` drops them again, which loses the
grades and feedback recorded in the meantime; that is inherent to reversing a
feature, not an oversight.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "q4r5s6t7u8v9"
down_revision: str | Sequence[str] | None = "p3q4r5s6t7u8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# (name, type, indexed). Order matters only for readability.
_COLUMNS: tuple[tuple[str, sa.types.TypeEngine, bool], ...] = (
    ("due_date", sa.DateTime(), True),
    ("assigned_by_id", sa.Integer(), True),
    ("completed_at", sa.DateTime(), False),
    ("grade", sa.String(), False),
    ("feedback", sa.String(), False),
    ("reviewed_at", sa.DateTime(), False),
    ("reviewed_by_id", sa.Integer(), False),
)


def _existing_columns() -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns("homework")}


def upgrade() -> None:
    # Guarded against re-application: this project has repeatedly had schema
    # applied out of band, and a migration that explodes on an already-correct
    # database is worse than one that no-ops.
    existing = _existing_columns()

    # batch mode so SQLite (dev and CI) gets a table rebuild rather than an
    # ALTER it does not support, while PostgreSQL takes the direct path.
    with op.batch_alter_table("homework") as batch:
        for name, type_, _indexed in _COLUMNS:
            if name not in existing:
                batch.add_column(sa.Column(name, type_, nullable=True))

    # Indexes are created outside the batch: inside it they would be rebuilt
    # along with the table and collide with themselves.
    for name, _type, indexed in _COLUMNS:
        if indexed and name not in existing:
            op.create_index(f"ix_homework_{name}", "homework", [name])


def downgrade() -> None:
    existing = _existing_columns()

    for name, _type, indexed in _COLUMNS:
        if indexed and name in existing:
            op.drop_index(f"ix_homework_{name}", table_name="homework")

    with op.batch_alter_table("homework") as batch:
        for name, _type, _indexed in _COLUMNS:
            if name in existing:
                batch.drop_column(name)
