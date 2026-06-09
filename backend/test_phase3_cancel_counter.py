from __future__ import annotations

from datetime import datetime, timedelta, timezone
import pytest

from backend.dependencies import (
    get_current_active_user,
    require_admin,
    require_student,
    require_teacher,
)
from backend.main import app
from backend.models import Session as SessionModel, User, SessionProof
from backend.test_main import (  # noqa: F401
    TestingSessionLocal,
    as_admin,
    as_student,
    as_teacher,
    client,
    fresh_db,
)
from backend.test_session_state_machine import _seed_users, _make_user_obj, _iso, _future, _swap_to_student, _swap_to_teacher


def test_cancel_session_by_student_success(client, as_admin):
    _, t, s = _seed_users(client)
    student_user = _make_user_obj(s, "student", "Student")
    _swap_to_student(student_user)

    start = _future(48)
    # create a session
    db = TestingSessionLocal()
    session = SessionModel(
        teacher_id=t,
        student_id=s,
        start_time=start.replace(tzinfo=None),
        end_time=(start + timedelta(hours=1)).replace(tzinfo=None),
        status="scheduled",
        version=0,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    sid = session.id
    db.close()

    # Cancel session
    r = client.post(f"/sessions/{sid}/cancel", json={"version": 0, "notes": "I need to cancel"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "cancelled"


def test_cancel_session_cutoff_failure_for_student(client, as_admin):
    _, t, s = _seed_users(client)
    student_user = _make_user_obj(s, "student", "Student")
    _swap_to_student(student_user)

    # Start time is in 10 hours (less than 24h cutoff)
    start = _future(10)
    db = TestingSessionLocal()
    session = SessionModel(
        teacher_id=t,
        student_id=s,
        start_time=start.replace(tzinfo=None),
        end_time=(start + timedelta(hours=1)).replace(tzinfo=None),
        status="scheduled",
        version=0,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    sid = session.id
    db.close()

    r = client.post(f"/sessions/{sid}/cancel", json={"version": 0})
    assert r.status_code == 400
    assert "cutoff" in r.json()["detail"].lower() or "hours" in r.json()["detail"].lower()


def test_cancel_session_cutoff_success_for_admin(client, as_admin):
    # Admin can cancel even within the 24h cutoff
    admin_id, t, s = _seed_users(client)
    start = _future(10)
    db = TestingSessionLocal()
    session = SessionModel(
        teacher_id=t,
        student_id=s,
        start_time=start.replace(tzinfo=None),
        end_time=(start + timedelta(hours=1)).replace(tzinfo=None),
        status="scheduled",
        version=0,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    sid = session.id
    db.close()

    r = client.post(f"/sessions/{sid}/cancel", json={"version": 0})
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"


def test_request_approval_with_teacher_proof(client, as_admin):
    _, t, s = _seed_users(client)
    student_user = _make_user_obj(s, "student", "Student")
    _swap_to_student(student_user)

    # Setup session directly in DB as overdue
    past_start = datetime.now(timezone.utc) - timedelta(days=2)
    db = TestingSessionLocal()
    session = SessionModel(
        teacher_id=t,
        student_id=s,
        start_time=past_start.replace(tzinfo=None),
        end_time=(past_start + timedelta(hours=1)).replace(tzinfo=None),
        status="overdue",
        version=0,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    sid = session.id

    # Add teacher-uploaded proof
    proof = SessionProof(
        session_id=sid,
        image_url="http://proof.url/image.png",
        uploader_id=t,
        uploader_role="teacher"
    )
    db.add(proof)
    db.commit()
    db.close()

    # Now request approval - should succeed because teacher proof exists
    r = client.post(f"/sessions/{sid}/request-approval", json={"version": 0})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "pending_verification"


def test_counter_cap_deadlock(client, as_admin):
    _, t, s = _seed_users(client)

    start = _future(48)
    db = TestingSessionLocal()
    session = SessionModel(
        teacher_id=t,
        student_id=s,
        start_time=start.replace(tzinfo=None),
        end_time=(start + timedelta(hours=1)).replace(tzinfo=None),
        status="pending_teacher",
        version=0,
        counter_count=2,  # Already countered twice
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    sid = session.id
    db.close()

    # Counter again as teacher -> counter_count becomes 3 (cap is 3)
    teacher_user = _make_user_obj(t, "teacher", "Teacher")
    _swap_to_teacher(teacher_user)

    new_start = start + timedelta(hours=2)
    r = client.post(f"/sessions/{sid}/counter/teacher", json={
        "start_time": _iso(new_start),
        "end_time": _iso(new_start + timedelta(hours=1)),
        "version": 0,
    })
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "pending_admin"
    assert r.json()["counter_count"] == 3
