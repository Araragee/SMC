"""Tests for application settings (``backend.config``).

Asserts the stable invariants of the Settings model — code-level defaults and
sanity constraints — without coupling to a developer's ``.env`` values.
"""
from __future__ import annotations

import pytest

pytest.importorskip("pydantic_settings")

from backend.config import settings  # noqa: E402


def test_secret_key_is_present():
    assert isinstance(settings.SECRET_KEY, str)
    assert settings.SECRET_KEY  # never empty


def test_algorithm_and_token_lifetimes_are_sane():
    assert settings.ALGORITHM
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES > 0
    assert settings.REFRESH_TOKEN_EXPIRE_DAYS > 0


def test_code_level_defaults():
    # These are defined in code (not the .env), so they're deterministic.
    assert settings.TOTP_ISSUER == "SMC Music School"
    assert settings.COUNTER_PROPOSAL_CAP == 3
    assert settings.LOW_STOCK_THRESHOLD == 5
    assert settings.NOTIFIER_TYPE in {"console", "email"}


def test_working_hours_window_is_valid():
    assert 0 <= settings.WORKING_HOURS_START < settings.WORKING_HOURS_END <= 24


def test_refresh_cookie_samesite_is_valid():
    assert settings.REFRESH_COOKIE_SAMESITE in {"lax", "strict", "none"}


def test_allowed_origins_is_non_empty_list():
    assert isinstance(settings.ALLOWED_ORIGINS, list)
    assert settings.ALLOWED_ORIGINS
