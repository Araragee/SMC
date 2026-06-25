"""Pytest configuration shared by every backend test module.

Three responsibilities, all of which must run *before* any ``backend.*``
module is imported by a test:

1. **Python 3.10 compatibility shim.** The codebase imports ``UTC`` directly
   from ``datetime`` (a 3.11+ alias for ``datetime.timezone.utc``). Production
   runs on 3.11+; this shim only fires on 3.10 dev/CI environments so the
   suite still imports.
2. **Hermetic environment.** We force a throwaway ``SECRET_KEY`` and a local
   SQLite ``DATABASE_URL`` through the process environment. pydantic-settings
   gives environment variables precedence over the committed ``.env``, so the
   suite never depends on a developer's real secret or a running Postgres.
3. **Import path.** Guarantee the repository root is importable so
   ``import backend`` resolves no matter which directory pytest is launched
   from.
"""
from __future__ import annotations

import datetime as _dt
import os
import sys
from pathlib import Path

# 1. datetime.UTC shim for Python 3.10 dev/CI environments.
if not hasattr(_dt, "UTC"):
    _dt.UTC = _dt.timezone.utc  # type: ignore[attr-defined]  # noqa: UP017

# 2. Hermetic test settings. ``setdefault`` so a CI job may still override
#    these explicitly; env vars win over values read from ``.env``.
os.environ.setdefault("SECRET_KEY", "test-secret-key-deterministic-not-for-prod")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_smc.db")

# 3. Make ``import backend`` resolvable regardless of the launch directory.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
