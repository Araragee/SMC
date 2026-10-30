"""The homework assignment lifecycle.

Two things are worth locking down here. The **status derivation** is computed
rather than stored, so it has to agree with the timestamps that justify it in
every ordering — including the awkward ones (reviewed but late, submitted after
the deadline). And the **teacher-side guard** is a different rule from the
participant guard: a student on the session may submit to an assignment, but
assigning, editing, grading and deleting belong to the teacher who runs it.
"""
from __future__ import annotations

from datetime import timedelta

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")

from fastapi import HTTPException  # noqa: E402

from backend import schemas  # noqa: E402
from backend.routers.sessions import _require_can_teach_session  # noqa: E402
from backend.utils.time import utcnow  # noqa: E402


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


def _homework(**overrides):
    """Build a Homework schema with sensible defaults for the fields under test."""
    fields = {
        "id": 1,
        "session_id": 1,
        "description": "Practise the G major scale",
        "created_at": utcnow(),
        "is_completed": False,
    }
    fields.update(overrides)
    return schemas.Homework(**fields)


# ── status derivation ─────────────────────────────────────────────────────────

def test_a_new_assignment_is_assigned():
    assert _homework().status == "assigned"


def test_an_assignment_with_a_future_deadline_is_not_overdue():
    assert _homework(due_date=utcnow() + timedelta(days=3)).status == "assigned"


def test_a_past_deadline_with_nothing_handed_in_is_overdue():
    assert _homework(due_date=utcnow() - timedelta(days=1)).status == "overdue"


def test_an_assignment_with_no_deadline_never_goes_overdue():
    """"By next lesson" is a real way to assign work, and it should not start
    nagging the student about a date nobody set."""
    assert _homework(due_date=None).status == "assigned"


def test_submitting_clears_overdue():
    """Late work is handed in, not still outstanding — it belongs in the
    teacher's review queue, not on the overdue list."""
    hw = _homework(due_date=utcnow() - timedelta(days=1), is_completed=True,
                   completed_at=utcnow())
    assert hw.status == "submitted"


def test_the_completion_flag_alone_counts_as_submitted():
    """Rows predating ``completed_at`` only have the boolean; they must not
    read as still outstanding."""
    assert _homework(is_completed=True, completed_at=None).status == "submitted"


def test_reviewing_wins_over_everything_else():
    hw = _homework(due_date=utcnow() - timedelta(days=5), is_completed=True,
                   completed_at=utcnow(), reviewed_at=utcnow(), grade="B+")
    assert hw.status == "reviewed"


def test_status_survives_a_naive_stored_timestamp():
    """SQLite hands back naive datetimes while a fresh one is aware. Comparing
    the two directly raises TypeError, which would 500 the whole list."""
    naive_past = (utcnow() - timedelta(days=2)).replace(tzinfo=None)
    assert _homework(due_date=naive_past).status == "overdue"


def test_a_review_with_no_grade_still_counts_as_reviewed():
    """"Seen it, nothing to add" is a legitimate review; the timestamp is what
    marks it done, not the presence of a mark."""
    hw = _homework(is_completed=True, reviewed_at=utcnow(), grade=None, feedback=None)
    assert hw.status == "reviewed"


# ── teacher guard ─────────────────────────────────────────────────────────────

def _assert_denied(session, user):
    with pytest.raises(HTTPException) as exc:
        _require_can_teach_session(session, user)
    assert exc.value.status_code == 403


def test_the_session_teacher_may_manage_its_homework():
    _require_can_teach_session(_Session(), _User(1, "teacher"))


def test_an_admin_may_manage_any_homework():
    _require_can_teach_session(_Session(), _User(99, "admin"))


def test_the_student_may_not_assign_or_grade():
    """The participant guard lets this student submit; this one must not let
    them create an assignment or mark their own work."""
    _assert_denied(_Session(), _User(2, "student"))


def test_another_teacher_may_not_touch_this_session():
    """``require_teacher`` only asks whether the caller is *a* teacher. Without
    this, any teacher in the school could assign homework to any student."""
    _assert_denied(_Session(), _User(3, "teacher"))


def test_an_unassigned_teacher_slot_does_not_admit_a_null_caller():
    session = _Session(teacher_id=None)
    user = _User(7, "teacher")
    user.id = None
    _assert_denied(session, user)


# ── schema contracts ──────────────────────────────────────────────────────────

def test_clearing_a_due_date_is_distinguishable_from_omitting_it():
    """In a PATCH body ``due_date: null`` and "field absent" both arrive as
    None, so removing a deadline needs its own flag or it is impossible."""
    omitted = schemas.HomeworkUpdate()
    cleared = schemas.HomeworkUpdate(clear_due_date=True)
    assert omitted.due_date is None and omitted.clear_due_date is False
    assert cleared.clear_due_date is True


def test_an_assignment_needs_a_description():
    with pytest.raises(ValueError):
        schemas.HomeworkCreate(description="")


def test_a_grade_is_bounded():
    with pytest.raises(ValueError):
        schemas.HomeworkReview(grade="A" * (schemas.GRADE_LEN + 1))


def test_a_grade_accepts_whatever_the_school_already_uses():
    for mark in ["A-", "92%", "Needs work", "5/10"]:
        assert schemas.HomeworkReview(grade=mark).grade == mark
