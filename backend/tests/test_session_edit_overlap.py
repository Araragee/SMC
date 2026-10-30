"""Admin session edits must respect the same double-booking rule as every
other path that moves a session.

``PUT /sessions/{id}`` was the one mutation route that never called
``_check_overlap``. Worse, its validation sat behind "did the times change?",
so an edit that only swapped ``teacher_id`` ran no checks at all — an admin
could hand a session to a teacher who was already booked for that hour.
"""
from __future__ import annotations

from datetime import timedelta

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")

from fastapi import HTTPException  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from backend import models, schemas  # noqa: E402
from backend.routers.sessions import update_session  # noqa: E402
from backend.utils.time import utcnow  # noqa: E402


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    models.Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def world(db):
    """Two teachers, two students, and one session per teacher at the same hour.

    Both sessions sit in the future so the window validator does not reject
    them for being in the past, and far enough out that the suite never races
    the clock.
    """
    admin_role = models.Role(name="admin")
    db.add(admin_role)
    db.flush()

    admin = models.User(name="Admin", username="admin", email="a@smc.com",
                        hashed_password="x", role_id=admin_role.id)
    t1 = models.User(name="T1", username="t1", email="t1@smc.com", hashed_password="x")
    t2 = models.User(name="T2", username="t2", email="t2@smc.com", hashed_password="x")
    s1 = models.User(name="S1", username="s1", email="s1@smc.com", hashed_password="x")
    s2 = models.User(name="S2", username="s2", email="s2@smc.com", hashed_password="x")
    db.add_all([admin, t1, t2, s1, s2])
    db.flush()

    # 10:00–11:00 UTC a week out. Naive, matching what SQLite stores.
    start = (utcnow().replace(tzinfo=None) + timedelta(days=7)).replace(
        hour=10, minute=0, second=0, microsecond=0
    )
    end = start + timedelta(hours=1)

    busy = models.Session(teacher_id=t2.id, student_id=s2.id, start_time=start,
                          end_time=end, status="scheduled", version=1)
    target = models.Session(teacher_id=t1.id, student_id=s1.id, start_time=start,
                            end_time=end, status="scheduled", version=1)
    db.add_all([busy, target])
    db.commit()

    return {"admin": admin, "t1": t1, "t2": t2, "s1": s1, "s2": s2,
            "busy": busy, "target": target, "start": start, "end": end}


def test_reassigning_onto_a_busy_teacher_is_rejected(db, world):
    """The regression: participants change, times do not."""
    edit = schemas.SessionEdit(teacher_id=world["t2"].id, version=1)

    with pytest.raises(HTTPException) as exc:
        update_session(world["target"].id, edit, db=db, current_user=world["admin"])

    assert exc.value.status_code == 409
    assert "conflict" in str(exc.value.detail).lower()


def test_moving_a_session_onto_a_busy_slot_is_rejected(db, world):
    """The same rule via the times, with the other teacher's student."""
    edit = schemas.SessionEdit(
        student_id=world["s2"].id,
        start_time=world["start"] + timedelta(minutes=30),
        version=1,
    )

    with pytest.raises(HTTPException) as exc:
        update_session(world["target"].id, edit, db=db, current_user=world["admin"])

    assert exc.value.status_code == 409


def test_a_session_does_not_conflict_with_itself(db, world):
    """Editing a session in place must not match its own row.

    Nudging the notes while leaving teacher, student and times alone used to
    be the case a naive overlap check would reject — the session overlaps
    itself. It must get past the check (the 404/500 that would follow from
    the unrelated machinery below is not what we are asserting).
    """
    edit = schemas.SessionEdit(
        start_time=world["start"] + timedelta(minutes=5), version=1
    )

    try:
        update_session(world["target"].id, edit, db=db, current_user=world["admin"])
    except HTTPException as exc:
        assert exc.status_code != 409, "a session must not conflict with itself"
