"""Pytest configuration shared by every backend test module.

Two responsibilities, both of which must run *before* any ``backend.*``
module is imported by a test:

1. **Hermetic environment.** We force a throwaway ``SECRET_KEY`` and a local
   SQLite ``DATABASE_URL`` through the process environment. pydantic-settings
   gives environment variables precedence over the committed ``.env``, so the
   suite never depends on a developer's real secret or a running Postgres.
2. **Import path.** Guarantee the repository root is importable so
   ``import backend`` resolves no matter which directory pytest is launched
   from.

There used to be a third: a monkeypatch that grafted ``UTC`` onto ``datetime``
so the suite could import on Python 3.10. Every module now takes ``UTC`` from
``backend.utils.time``, which resolves the alias itself, so the shim is gone.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# 1. Hermetic test settings. ``setdefault`` so a CI job may still override
#    these explicitly; env vars win over values read from ``.env``.
os.environ.setdefault("SECRET_KEY", "test-secret-key-deterministic-not-for-prod")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_smc.db")

# 2. Make ``import backend`` resolvable regardless of the launch directory.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
