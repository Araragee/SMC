"""Import smoke test — the cheapest possible regression net.

Importing the FastAPI app forces every router, model, schema, and service
module to import cleanly. It catches the most common breakages (syntax
errors, bad imports, circular imports, decorator-time mistakes) without
needing a database or network. Replaces the deleted suite's coverage gap.

``backend.main`` calls ``os.makedirs("uploads/shop")`` and mounts a
``StaticFiles`` directory at import time (relative to the cwd), so we import
it from inside a throwaway temp directory to avoid polluting the repo.
"""
from __future__ import annotations

import importlib

import pytest

# The full app depends on the entire requirements set; skip cleanly in a
# minimal environment rather than erroring out of collection.
for _dep in ("fastapi", "sqlalchemy", "pydantic", "slowapi", "jwt", "passlib"):
    pytest.importorskip(_dep)

CORE_MODULES = [
    "backend.config",
    "backend.database",
    "backend.models",
    "backend.schemas",
    "backend.dependencies",
    "backend.utils.signed_urls",
    "backend.utils.uploads",
    "backend.services.notifier",
]

ROUTER_MODULES = [
    "backend.routers.activity",
    "backend.routers.auth",
    "backend.routers.messaging",
    "backend.routers.notifications",
    "backend.routers.payments",
    "backend.routers.push",
    "backend.routers.sessions",
    "backend.routers.shop",
    "backend.routers.uploads",
    "backend.routers.users",
]


@pytest.mark.parametrize("module_name", CORE_MODULES + ROUTER_MODULES)
def test_module_imports(module_name):
    assert importlib.import_module(module_name) is not None


def test_app_object_is_constructed(tmp_path, monkeypatch):
    # Import from a temp cwd: main.py makes ./uploads/shop and mounts it.
    monkeypatch.chdir(tmp_path)
    main = importlib.import_module("backend.main")
    assert main.app is not None
    # FastAPI sets .title from settings.PROJECT_NAME.
    assert main.app.title
