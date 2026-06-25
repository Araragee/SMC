"""Tests for auth/security helpers (``backend.dependencies``).

Covers JWT minting/verification and the role-guard dependencies. The guards
are plain functions that take the resolved ``current_user`` as an argument,
so we can call them directly with a lightweight stub instead of standing up
the full FastAPI dependency graph or a database.
"""
from __future__ import annotations

import time
from datetime import timedelta

import pytest

# dependencies.py pulls in the web/ORM/crypto stack at import time.
pytest.importorskip("fastapi")
pytest.importorskip("jwt")
pytest.importorskip("passlib")
pytest.importorskip("sqlalchemy")

import jwt  # noqa: E402
from fastapi import HTTPException  # noqa: E402

from backend.config import settings  # noqa: E402
from backend.dependencies import (  # noqa: E402
    create_access_token,
    get_current_active_user,
    require_admin,
    require_student,
    require_teacher,
)


def _decode(token: str, key: str | None = None) -> dict:
    return jwt.decode(token, key or settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


class _Role:
    def __init__(self, name: str):
        self.name = name


class _User:
    def __init__(self, role_name: str | None = None, is_active: bool = True):
        self.role = _Role(role_name) if role_name else None
        self.is_active = is_active


# ── JWT ───────────────────────────────────────────────────────────────────────

def test_access_token_round_trips_subject():
    token = create_access_token({"sub": "alice"})
    payload = _decode(token)
    assert payload["sub"] == "alice"
    assert "exp" in payload


def test_access_token_honours_custom_expiry():
    token = create_access_token({"sub": "bob"}, expires_delta=timedelta(hours=2))
    payload = _decode(token)
    # 2h ± a minute of slack.
    assert 7100 <= payload["exp"] - int(time.time()) <= 7300


def test_expired_token_is_rejected():
    token = create_access_token({"sub": "x"}, expires_delta=timedelta(seconds=-5))
    with pytest.raises(jwt.ExpiredSignatureError):
        _decode(token)


def test_token_signed_with_other_key_is_rejected():
    token = create_access_token({"sub": "x"})
    with pytest.raises(jwt.InvalidTokenError):
        _decode(token, key="a-different-secret")


# ── active-user guard ─────────────────────────────────────────────────────────

def test_active_user_passthrough():
    user = _User(role_name="student", is_active=True)
    assert get_current_active_user(user) is user


def test_inactive_user_blocked():
    with pytest.raises(HTTPException) as exc:
        get_current_active_user(_User(role_name="student", is_active=False))
    assert exc.value.status_code == 400


# ── role guards ───────────────────────────────────────────────────────────────

def test_require_admin_allows_admin_blocks_others():
    admin = _User(role_name="admin")
    assert require_admin(admin) is admin
    for role in ("teacher", "student"):
        with pytest.raises(HTTPException) as exc:
            require_admin(_User(role_name=role))
        assert exc.value.status_code == 403


def test_require_teacher_allows_teacher_and_admin():
    for role in ("teacher", "admin"):
        u = _User(role_name=role)
        assert require_teacher(u) is u
    with pytest.raises(HTTPException) as exc:
        require_teacher(_User(role_name="student"))
    assert exc.value.status_code == 403


def test_require_student_allows_student_and_admin():
    for role in ("student", "admin"):
        u = _User(role_name=role)
        assert require_student(u) is u
    with pytest.raises(HTTPException) as exc:
        require_student(_User(role_name="teacher"))
    assert exc.value.status_code == 403


def test_role_guard_handles_missing_role():
    with pytest.raises(HTTPException) as exc:
        require_admin(_User(role_name=None))
    assert exc.value.status_code == 403
