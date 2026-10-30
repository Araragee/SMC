"""Working hours are measured in school-local time, so the timezone must hold.

The old code caught every failure from ``ZoneInfo(...)`` and fell back to the
raw UTC datetime. For Manila (UTC+8) that did not loosen the rule, it moved
it: a 09:00 local lesson was refused while the error quoted a window the
booking sat inside, and a 23:00 one sailed through.
"""
from __future__ import annotations

from datetime import timedelta

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("pydantic_settings")

from fastapi import HTTPException  # noqa: E402

from backend.config import Settings, settings  # noqa: E402
from backend.routers import sessions as S  # noqa: E402
from backend.utils.time import UTC, utcnow  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_tz_cache():
    S._school_tz.cache_clear()
    original = settings.SCHOOL_TIMEZONE
    yield
    settings.SCHOOL_TIMEZONE = original
    S._school_tz.cache_clear()


def _morning_utc():
    """01:00 UTC == 09:00 in Manila: an ordinary mid-morning lesson."""
    return (utcnow() + timedelta(days=3)).replace(
        hour=1, minute=0, second=0, microsecond=0, tzinfo=UTC
    )


def test_a_mid_morning_local_lesson_is_accepted():
    start = _morning_utc()
    assert S._validate_session_window(start, start + timedelta(hours=1), is_admin=False)


def test_an_unresolvable_timezone_does_not_reject_a_valid_booking():
    """The regression. Falling back to UTC refused this with a misleading
    message; skipping the check is wrong in only one direction, and is logged."""
    settings.SCHOOL_TIMEZONE = "Not/AZone"
    S._school_tz.cache_clear()
    start = _morning_utc()

    end = S._validate_session_window(start, start + timedelta(hours=1), is_admin=False)
    assert end == start + timedelta(hours=1)


def test_an_unresolvable_timezone_resolves_to_none():
    settings.SCHOOL_TIMEZONE = "Not/AZone"
    S._school_tz.cache_clear()
    assert S._school_tz() is None


def test_a_typo_is_refused_at_startup():
    """The real defence: the app should not boot misconfigured at all."""
    with pytest.raises(Exception) as exc:
        Settings(SECRET_KEY="x" * 40, SCHOOL_TIMEZONE="Asia/Manilla")
    assert "timezone" in str(exc.value).lower()


def test_duration_rules_still_apply_without_a_timezone():
    """Losing the timezone must not disable the checks that do not need one."""
    settings.SCHOOL_TIMEZONE = "Not/AZone"
    S._school_tz.cache_clear()
    start = _morning_utc()

    with pytest.raises(HTTPException) as exc:
        S._validate_session_window(start, start + timedelta(minutes=5), is_admin=False)
    assert exc.value.status_code == 400
