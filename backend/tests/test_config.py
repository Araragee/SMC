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
    """``ALLOWED_ORIGINS`` is stored as raw text and parsed by ``cors_origins``.

    It was a ``list[str]`` once, and this assertion was left behind pointing at
    the raw field — so it has been failing (and CI with it) since the type
    changed. The parsing rules themselves are covered below.
    """
    assert isinstance(settings.cors_origins, list)
    assert settings.cors_origins


def test_cors_origins_accepts_a_comma_separated_list():
    settings.__dict__.pop("cors_origins", None)  # clear the cached_property
    try:
        settings.ALLOWED_ORIGINS = "https://a.example, https://b.example/"
        # Trailing slashes are stripped: a browser's Origin header never
        # carries one and the comparison is exact.
        assert settings.cors_origins == ["https://a.example", "https://b.example"]
    finally:
        settings.__dict__.pop("cors_origins", None)


def test_cors_origins_accepts_a_json_list():
    settings.__dict__.pop("cors_origins", None)
    try:
        settings.ALLOWED_ORIGINS = '["https://a.example", "https://b.example"]'
        assert settings.cors_origins == ["https://a.example", "https://b.example"]
    finally:
        settings.__dict__.pop("cors_origins", None)


def test_a_malformed_origin_list_does_not_take_the_api_down():
    """The whole reason this field is plain text: as ``list[str]``,
    pydantic-settings JSON-decoded it while building Settings, so one
    misformatted value raised at import and the process died before serving
    anything. A bad list must refuse origins, not the API."""
    settings.__dict__.pop("cors_origins", None)
    try:
        settings.ALLOWED_ORIGINS = "[not json at all"
        assert settings.cors_origins == []
    finally:
        settings.__dict__.pop("cors_origins", None)
