"""Tests for the object-level authorization helpers (``backend.dependencies``).

The role guards answer "what kind of user is this?"; these answer "may this
user see *this* record?". Several endpoints take a user id in the path, so
without these checks any authenticated account could read another user's
schedule, lesson history, enrollments or notifications by changing the number.

Like ``test_security.py`` these are plain functions, so they are exercised
directly with lightweight stubs rather than a live database.
"""
from __future__ import annotations

import pytest

# dependencies.py pulls in the web/ORM/crypto stack at import time.
pytest.importorskip("fastapi")
pytest.importorskip("jwt")
pytest.importorskip("passlib")
pytest.importorskip("sqlalchemy")

from fastapi import HTTPException  # noqa: E402

from backend.dependencies import (  # noqa: E402
    is_admin,
    require_can_view_user,
    require_self_or_admin,
)


class _Role:
    def __init__(self, name: str):
        self.name = name


class _User:
    def __init__(self, user_id: int, role_name: str | None = None):
        self.id = user_id
        self.role = _Role(role_name) if role_name else None


class _FakeQuery:
    def __init__(self, result):
        self._result = result

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        return self._result


class _FakeDB:
    """Returns a canned row per queried model.

    ``require_can_view_user`` queries TeacherStudent first, then Session, so
    the mapping keys off the model's class name.
    """

    def __init__(self, *, assignment=None, enrollment=None, session=None):
        self._rows = {"TeacherStudent": assignment, "Enrollment": enrollment, "Session": session}
        self.queried: list[str] = []

    def query(self, model):
        name = getattr(model, "__name__", str(model))
        self.queried.append(name)
        return _FakeQuery(self._rows.get(name))


ADMIN = _User(1, "admin")
TEACHER = _User(2, "teacher")
STUDENT = _User(3, "student")
OTHER_STUDENT = _User(4, "student")


# ── is_admin ──────────────────────────────────────────────────────────────────

def test_is_admin_recognises_admin():
    assert is_admin(ADMIN) is True


@pytest.mark.parametrize("user", [TEACHER, STUDENT, _User(9), None])
def test_is_admin_rejects_everyone_else(user):
    assert is_admin(user) is False


def test_is_admin_is_case_insensitive():
    assert is_admin(_User(5, "Admin")) is True


# ── require_self_or_admin ─────────────────────────────────────────────────────

def test_self_may_access_own_records():
    require_self_or_admin(STUDENT, STUDENT.id)


def test_admin_may_access_anyones_records():
    require_self_or_admin(ADMIN, STUDENT.id)


def test_other_user_is_blocked():
    with pytest.raises(HTTPException) as exc:
        require_self_or_admin(STUDENT, OTHER_STUDENT.id)
    assert exc.value.status_code == 403


def test_teacher_has_no_blanket_access():
    """A teacher is not privileged by role alone — only by relationship."""
    with pytest.raises(HTTPException) as exc:
        require_self_or_admin(TEACHER, STUDENT.id)
    assert exc.value.status_code == 403


# ── require_can_view_user ─────────────────────────────────────────────────────

def test_self_short_circuits_without_querying():
    db = _FakeDB()
    require_can_view_user(db, STUDENT, STUDENT.id)
    assert db.queried == []


def test_admin_short_circuits_without_querying():
    db = _FakeDB()
    require_can_view_user(db, ADMIN, STUDENT.id)
    assert db.queried == []


def test_assigned_teacher_may_view_their_student():
    db = _FakeDB(assignment=object())
    require_can_view_user(db, TEACHER, STUDENT.id)
    # Resolved on the assignment lookup; no need to fall through to sessions.
    assert db.queried == ["TeacherStudent"]


def test_enrolled_teacher_may_view_their_student():
    db = _FakeDB(assignment=None, enrollment=object())
    require_can_view_user(db, TEACHER, STUDENT.id)
    assert db.queried == ["TeacherStudent", "Enrollment"]


def test_shared_session_grants_access_without_an_assignment():
    db = _FakeDB(assignment=None, enrollment=None, session=object())
    require_can_view_user(db, TEACHER, STUDENT.id)
    assert db.queried == ["TeacherStudent", "Enrollment", "Session"]



def test_unrelated_student_is_blocked():
    """The core regression: student A reading student B's records."""
    db = _FakeDB(assignment=None, session=None)
    with pytest.raises(HTTPException) as exc:
        require_can_view_user(db, STUDENT, OTHER_STUDENT.id)
    assert exc.value.status_code == 403


def test_unrelated_teacher_is_blocked():
    db = _FakeDB(assignment=None, session=None)
    with pytest.raises(HTTPException) as exc:
        require_can_view_user(db, TEACHER, STUDENT.id)
    assert exc.value.status_code == 403
