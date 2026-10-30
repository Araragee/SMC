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


def test_cors_origins_is_non_empty_list():
    # ALLOWED_ORIGINS is a raw string by design (a malformed list must refuse
    # one origin, not kill the process at import); cors_origins is the parsed
    # accessor the app actually reads.
    assert isinstance(settings.ALLOWED_ORIGINS, str)
    assert isinstance(settings.cors_origins, list)
    assert settings.cors_origins


@pytest.mark.parametrize(
    ("configured", "expected"),
    [
        # Comma-separated — the shape of the in-code default.
        (
            "http://localhost:5173,http://127.0.0.1:5173",
            ["http://localhost:5173", "http://127.0.0.1:5173"],
        ),
        # JSON list, as DEPLOY.md documents for the compose path.
        ('["https://smc.example.com"]', ["https://smc.example.com"]),
        # Trailing slashes: an Origin header never carries one.
        ("https://smc.example.com/", ["https://smc.example.com"]),
        # Bare host: what Render's `fromService` host property yields. Must
        # gain a scheme or it matches no Origin header and CORS fails on the
        # deployed frontend's very first request.
        ("smc-web.onrender.com", ["https://smc-web.onrender.com"]),
        (
            '["smc-web.onrender.com", "https://smc.example.com"]',
            ["https://smc-web.onrender.com", "https://smc.example.com"],
        ),
        # Unparseable or empty refuses every origin rather than raising.
        ("", []),
        ("[not json", []),
    ],
)
def test_cors_origins_parses_every_shape(configured, expected):
    from backend.config import Settings

    assert Settings(SECRET_KEY="test", ALLOWED_ORIGINS=configured).cors_origins == expected
