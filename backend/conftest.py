"""Pytest configuration shared by every backend test module.

Adds a small Python 3.10 compatibility shim: the codebase imports
``UTC`` directly from the ``datetime`` module (a Python 3.11+ alias for
``datetime.timezone.utc``). Production runs on 3.11+; this shim only
fires on 3.10 dev/test environments so the suite still imports.
"""
from __future__ import annotations

import datetime as _dt

if not hasattr(_dt, "UTC"):
    _dt.UTC = _dt.timezone.utc  # type: ignore[attr-defined]
