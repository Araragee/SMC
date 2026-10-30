"""The per-session participant guard.

Everything that belongs *to a session* — proofs, homework rows, homework
files — is reachable only by that session's teacher, its student, or an admin.
The routes used to open-code this rule and drifted apart doing so: some
constrained students only ("is this student asking about themselves?"), which
silently granted every teacher in the school access to every session's
homework, and one route had no object check at all.
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")

from fastapi import HTTPException  # noqa: E402

from backend.routers.sessions import _require_session_participant  # noqa: E402


class _Role:
    def __init__(self, name):
        self.name = name


class _User:
    def __init__(self, user_id, role_name=None):
        self.id = user_id
        self.role = _Role(role_name) if role_name else None


class _Session:
    def __init__(self, teacher_id=1, student_id=2):
        self.teacher_id = teacher_id
        self.student_id = student_id


def _assert_denied(session, user):
    with pytest.raises(HTTPException) as exc:
        _require_session_participant(session, user)
    assert exc.value.status_code == 403


def test_the_session_teacher_is_allowed():
    _require_session_participant(_Session(), _User(1, "teacher"))


def test_the_session_student_is_allowed():
    _require_session_participant(_Session(), _User(2, "student"))


def test_an_admin_is_allowed_without_participating():
    _require_session_participant(_Session(), _User(99, "admin"))


def test_an_unrelated_teacher_is_denied():
    """The bug this guard replaces: a role check alone let any teacher read or
    overwrite any student's homework by guessing an id."""
    _assert_denied(_Session(), _User(3, "teacher"))


def test_an_unrelated_student_is_denied():
    _assert_denied(_Session(), _User(4, "student"))


def test_a_user_with_no_role_is_denied():
    _assert_denied(_Session(), _User(5))


def test_the_admin_check_is_case_insensitive():
    """Role names arrive from the database as seeded, and the seed has varied
    between "admin" and "Admin"; a case-sensitive compare would deny an admin."""
    _require_session_participant(_Session(), _User(99, "Admin"))


def test_a_session_with_an_unassigned_participant_does_not_admit_everyone():
    """A null teacher_id must not match a user whose id is also absent —
    ``None in (None, 2)`` is the shape of that mistake."""
    session = _Session(teacher_id=None, student_id=2)
    user = _User(7, "teacher")
    user.id = None
    _assert_denied(session, user)
