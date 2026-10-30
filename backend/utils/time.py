"""One place to get the current time, and one definition of UTC.

Two reasons this exists rather than each module reaching for ``datetime``:

1. **Version sensitivity.** ``datetime.UTC`` is a 3.11+ alias for
   ``datetime.timezone.utc``. Importing it directly meant every module failed
   to import on 3.10, which is why ``conftest.py`` carried a monkeypatch shim
   just so the test suite could load. Re-exporting the alias from here removes
   the sensitivity, and with it the shim.

2. **Naive-vs-aware consistency.** The routers juggle both: SQLite round-trips
   drop the tzinfo, so a value read back from the database is naive while a
   freshly computed one is aware, and comparing the two raises ``TypeError``.
   ``as_utc`` and ``naive`` give both directions one spelling so the coercion
   is obvious at the call site instead of being re-invented per module.
"""
from __future__ import annotations

import datetime as _dt

# 3.11 exposes ``datetime.UTC``; 3.10 only has ``datetime.timezone.utc``. They
# are the same object on 3.11, so this is an alias, not a fallback.
UTC = getattr(_dt, "UTC", _dt.timezone.utc)  # noqa: UP017

__all__ = ["UTC", "as_utc", "naive", "utcnow"]


def utcnow() -> _dt.datetime:
    """Timezone-aware "now" in UTC.

    Always prefer this over ``datetime.utcnow()``, which returns a *naive*
    value that claims to be local time and silently mis-compares.
    """
    return _dt.datetime.now(UTC)


def as_utc(value: _dt.datetime | None) -> _dt.datetime | None:
    """Attach UTC to a naive datetime; convert an aware one. ``None`` passes
    through so callers can use it directly on optional columns."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def naive(value: _dt.datetime | None) -> _dt.datetime | None:
    """Drop the timezone after normalizing to UTC.

    For writing to columns declared without ``timezone=True``, where storing an
    aware value would round-trip as naive anyway and make the two comparable
    only by accident.
    """
    utc = as_utc(value)
    return None if utc is None else utc.replace(tzinfo=None)
