"""Idempotency helpers for migrations.

This file lives inside ``versions/`` because Alembic adds that directory to
``sys.path`` while loading scripts — siblings can therefore import it.

Alembic also tries to load every ``*.py`` file in ``versions/`` as a
revision script, so this module is deliberately structured as a no-op
revision: it declares ``revision``/``down_revision`` (chained to the
0001 baseline so it doesn't introduce another head) and an empty
``upgrade()``/``downgrade()``.

Real work happens in the helper functions below, which the legacy
e0c69a-chain migrations import to skip DDL that the 0001 baseline has
already performed on fresh installs.
"""
from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import inspect

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "phase1_helper"
# Chain off 0001 so this file participates in the graph harmlessly.
# The Phase 1 merge migration lists "phase1_helper" as one of its parents,
# converging everything to a single head.
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """No-op. This file exists only so its helper functions are importable."""
    return None


def downgrade() -> None:
    return None


# ── Helpers ──────────────────────────────────────────────────────────────────


def _inspector():
    return inspect(op.get_bind())


def has_table(name: str) -> bool:
    try:
        return name in _inspector().get_table_names()
    except Exception:
        return False


def has_column(table: str, column: str) -> bool:
    try:
        return any(c["name"] == column for c in _inspector().get_columns(table))
    except Exception:
        return False


def has_index(table: str, index: str) -> bool:
    try:
        return any(ix.get("name") == index for ix in _inspector().get_indexes(table))
    except Exception:
        return False
