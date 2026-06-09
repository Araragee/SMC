"""State-machine tests for the session lifecycle.

Covers, for the routes in ``backend/routers/sessions.py``:

  * Every legal status transition reaches the expected next state.
  * Illegal transitions are rejected with 409.
  * Optimistic-locking ``version`` mismatches return 409.
  * Overlap conflicts return 409.
  * Window validation (past time, duration bounds) returns 400.
  * Force-complete is only allowed 24h after the session ends.
  * Completion atomically decrements ``sessions_left``.

Tests share the in-memory SQLite setup with ``test_main.py`` — fixtures from
that module are imported so we don't duplicate the schema-reset boilerplate.
"""
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
from backend.models import Role, Session as SessionModel, TeacherStudent, User

# Re-use the fresh-DB fixture, TestClient fixture, etc.
from backend.test_main import (  # noqa: F401
    TestingSessionLocal,
    as_admin,
    as_student,
    as_teacher,
    client,
    fresh_db,
)


# ── Helpers ─────────────────────────────────────────────────────────────────

def _iso(dt: datetime) -> str:
    """Return an ISO string with explicit UTC offset (Pydantic likes this)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _future(hours: float = 24) -> datetime:
    target = datetime.now(timezone.utc) + timedelta(hours=hours)
    if target.hour < 9 or target.hour >= 21:
        target = target.replace(hour=10, minute=0, second=0, microsecond=0)
    return target


def _seed_users(client) -> tuple[int, int, int]:
    """Create roles + admin/teacher/student users via the API.

    Returns (admin_id, teacher_id, student_id). Run while ``as_admin`` is
    active so the create-user endpoint accepts the calls.
    """
    admin_role = client.post("/roles/", json={"name": "admin"}).json()["id"]
    teacher_role = client.post("/roles/", json={"name": "teacher"}).json()["id"]
    student_role = client.post("/roles/", json={"name": "student"}).json()["id"]

    def _create(email: str, name: str, role_id: int, extra: dict | None = None) -> int:
        payload = {"email": email, "name": name, "password": "password1", "role_id": role_id}
        if extra:
            payload.update(extra)
        body = client.post("/users/", json=payload).json()
        # build_token_pair wraps the user inside a TokenPair; sanity-check.
        assert "user" in body, f"Unexpected user-create body: {body}"
        return body["user"]["id"]

    a = _create("a@x.com", "Admin", admin_role)
    t = _create("t@x.com", "Teacher", teacher_role)
    s = _create("s@x.com", "Student", student_role, {"sessions_left": 10})

    # Link teacher↔student so student propose endpoint passes its guard.
    client.post("/teacher-students/", json={"teacher_id": t, "student_id": s})
    return a, t, s


def _swap_to_teacher(teacher_user: User) -> None:
    app.dependency_overrides[get_current_active_user] = lambda: teacher_user
    app.dependency_overrides[require_teacher] = lambda: teacher_user


def _swap_to_student(student_user: User) -> None:
    app.dependency_overrides[get_current_active_user] = lambda: student_user
    app.dependency_overrides[require_student] = lambda: student_user


def _make_user_obj(uid: int, role_name: str, name: str = "U") -> User:
    return User(
        id=uid,
        username=f"user{uid}",
        email=f"u{uid}@x.com",
        name=name,
        role_id=uid,
        role=Role(id=uid, name=role_name),
        is_active=True,
        sessions_left=10 if role_name == "student" else None,
    )


# ── Validation ──────────────────────────────────────────────────────────────

def test_propose_rejects_past_start(client, as_admin):
    """propose with a start_time in the past → 400."""
    _, t, s = _seed_users(client)
    student_user = _make_user_obj(s, "student", "Student")
    _swap_to_student(student_user)
    past_start = datetime.now(timezone.utc) - timedelta(hours=2)
    r = client.post("/sessions/propose/student", json={
        "teacher_id": t,
        "student_id": s,
        "start_time": _iso(past_start),
        "end_time": _iso(past_start + timedelta(hours=1)),
    })
    assert r.status_code == 400
    assert "past" in r.json()["detail"].lower()


def test_propose_rejects_too_short(client, as_admin):
    _, t, s = _seed_users(client)
    student_user = _make_user_obj(s, "student", "Student")
    _swap_to_student(student_user)
    start = _future(2)
    r = client.post("/sessions/propose/student", json={
        "teacher_id": t,
        "student_id": s,
        "start_time": _iso(start),
        "end_time": _iso(start + timedelta(minutes=5)),
    })
    assert r.status_code == 400
    assert "short" in r.json()["detail"].lower()


def test_propose_rejects_too_long(client, as_admin):
    _, t, s = _seed_users(client)
    student_user = _make_user_obj(s, "student", "Student")
    _swap_to_student(student_user)
    start = _future(2)
    r = client.post("/sessions/propose/student", json={
        "teacher_id": t,
        "student_id": s,
        "start_time": _iso(start),
        "end_time": _iso(start + timedelta(hours=5)),
    })
    assert r.status_code == 400
    assert "long" in r.json()["detail"].lower()


def test_propose_rejects_end_before_start(client, as_admin):
    _, t, s = _seed_users(client)
    student_user = _make_user_obj(s, "student", "Student")
    _swap_to_student(student_user)
    start = _future(2)
    r = client.post("/sessions/propose/student", json={
        "teacher_id": t,
        "student_id": s,
        "start_time": _iso(start),
        "end_time": _iso(start - timedelta(minutes=30)),
    })
    assert r.status_code == 400


def test_admin_create_accepts_valid(client, as_admin):
    """admin POST /sessions/ with a valid future window → scheduled."""
    _, t, s = _seed_users(client)
    start = _future(48)
    r = client.post("/sessions/", json={
        "teacher_id": t,
        "student_id": s,
        "start_time": _iso(start),
        "end_time": _iso(start + timedelta(hours=1)),
        "notes": "First lesson",
    })
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "scheduled"


def test_admin_record_past_allows_history(client, as_admin):
    """record_past_session must allow past windows (it logs history)."""
    _, t, s = _seed_users(client)
    past = datetime.now(timezone.utc) - timedelta(days=2)
    r = client.post("/sessions/record", json={
        "teacher_id": t,
        "student_id": s,
        "start_time": _iso(past),
        "end_time": _iso(past + timedelta(hours=1)),
        "notes": "Logged after the fact",
    })
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "completed"


# ── State machine: legal transitions ────────────────────────────────────────

def test_student_propose_then_teacher_approve(client, as_admin):
    """pending_teacher → pending_admin via teacher approval."""
    _, t, s = _seed_users(client)

    # Switch to student to propose.
    student_user = _make_user_obj(s, "student", "Student")
    _swap_to_student(student_user)
    start = _future(36)
    propose = client.post("/sessions/propose/student", json={
        "teacher_id": t,
        "student_id": s,
        "start_time": _iso(start),
        "end_time": _iso(start + timedelta(hours=1)),
    })
    assert propose.status_code == 200, propose.text
    sid = propose.json()["id"]
    assert propose.json()["status"] == "pending_teacher"

    # Teacher approves → pending_admin.
    teacher_user = _make_user_obj(t, "teacher", "Teacher")
    _swap_to_teacher(teacher_user)
    approve = client.post(f"/sessions/{sid}/approve/teacher")
    assert approve.status_code == 200, approve.text
    assert approve.json()["status"] == "pending_admin"


def test_full_three_step_negotiation_to_scheduled(client, as_admin):
    """propose(student) → counter(teacher) → approve(student) → approve(admin)."""
    admin_user_id, t, s = _seed_users(client)

    # student proposes
    student_user = _make_user_obj(s, "student", "Student")
    _swap_to_student(student_user)
    start = _future(40)
    propose = client.post("/sessions/propose/student", json={
        "teacher_id": t,
        "student_id": s,
        "start_time": _iso(start),
        "end_time": _iso(start + timedelta(hours=1)),
    })
    sid = propose.json()["id"]

    # teacher counters → pending_student
    teacher_user = _make_user_obj(t, "teacher", "Teacher")
    _swap_to_teacher(teacher_user)
    new_start = start + timedelta(hours=2)
    counter = client.post(f"/sessions/{sid}/counter/teacher", json={
        "start_time": _iso(new_start),
        "end_time": _iso(new_start + timedelta(hours=1)),
    })
    assert counter.status_code == 200, counter.text
    assert counter.json()["status"] == "pending_student"

    # student approves the counter → pending_admin
    _swap_to_student(student_user)
    approve = client.post(f"/sessions/{sid}/approve/student")
    assert approve.status_code == 200, approve.text
    assert approve.json()["status"] == "pending_admin"

    # admin approves → scheduled
    admin_user = _make_user_obj(admin_user_id, "admin", "Admin")
    app.dependency_overrides[require_admin] = lambda: admin_user
    app.dependency_overrides[get_current_active_user] = lambda: admin_user
    final = client.post(f"/sessions/{sid}/approve/admin")
    assert final.status_code == 200, final.text
    assert final.json()["status"] == "scheduled"


def test_admin_reject_pending(client, as_admin):
    """pending_admin → rejected via admin reject."""
    _, t, s = _seed_users(client)
    start = _future(48)
    create = client.post("/sessions/", json={
        "teacher_id": t, "student_id": s,
        "start_time": _iso(start), "end_time": _iso(start + timedelta(hours=1)),
    }).json()
    sid = create["id"]
    # Manually push to pending_admin by re-using DB
    db = TestingSessionLocal()
    s_row = db.query(SessionModel).filter(SessionModel.id == sid).first()
    s_row.status = "pending_admin"
    db.commit()
    cached_version = s_row.version
    db.close()

    r = client.post(f"/sessions/{sid}/reject/admin", json={"reason": "Conflict", "version": cached_version})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "rejected"


# ── State machine: illegal transitions ──────────────────────────────────────

def test_teacher_cannot_approve_already_scheduled(client, as_admin):
    """teacher approve on scheduled session → 409."""
    _, t, s = _seed_users(client)
    start = _future(48)
    create = client.post("/sessions/", json={
        "teacher_id": t, "student_id": s,
        "start_time": _iso(start), "end_time": _iso(start + timedelta(hours=1)),
    }).json()
    sid = create["id"]

    teacher_user = _make_user_obj(t, "teacher", "Teacher")
    _swap_to_teacher(teacher_user)
    r = client.post(f"/sessions/{sid}/approve/teacher")
    assert r.status_code == 409


def test_admin_complete_on_rejected_fails(client, as_admin):
    """complete on rejected session → 409."""
    _, t, s = _seed_users(client)
    start = _future(48)
    create = client.post("/sessions/", json={
        "teacher_id": t, "student_id": s,
        "start_time": _iso(start), "end_time": _iso(start + timedelta(hours=1)),
    }).json()
    sid = create["id"]

    # Force the session into rejected directly in the DB.
    db = TestingSessionLocal()
    s_row = db.query(SessionModel).filter(SessionModel.id == sid).first()
    s_row.status = "rejected"
    db.commit()
    db.close()

    r = client.post(f"/sessions/{sid}/complete")
    assert r.status_code == 409


# ── Optimistic locking ──────────────────────────────────────────────────────

def test_stale_version_rejected(client, as_admin):
    """edit with a stale version → 409 with helpful message."""
    _, t, s = _seed_users(client)
    start = _future(48)
    create = client.post("/sessions/", json={
        "teacher_id": t, "student_id": s,
        "start_time": _iso(start), "end_time": _iso(start + timedelta(hours=1)),
    }).json()
    sid = create["id"]
    current_version = create["version"]

    # First edit succeeds and bumps the version.
    first = client.put(f"/sessions/{sid}", json={
        "notes": "Updated note", "version": current_version,
    })
    assert first.status_code == 200

    # A second edit using the now-stale version is rejected.
    second = client.put(f"/sessions/{sid}", json={
        "notes": "Stale edit", "version": current_version,
    })
    assert second.status_code == 409
    assert "modified by someone else" in second.json()["detail"]


# ── Overlap detection ──────────────────────────────────────────────────────

def test_overlap_rejected_for_teacher(client, as_admin):
    """Booking two overlapping sessions for the same teacher → 409."""
    _, t, s = _seed_users(client)
    start = _future(50)
    first = client.post("/sessions/", json={
        "teacher_id": t, "student_id": s,
        "start_time": _iso(start), "end_time": _iso(start + timedelta(hours=1)),
    })
    assert first.status_code == 200, first.text

    # Second session overlaps the first.
    overlap_start = start + timedelta(minutes=30)
    r = client.post("/sessions/", json={
        "teacher_id": t, "student_id": s,
        "start_time": _iso(overlap_start),
        "end_time": _iso(overlap_start + timedelta(hours=1)),
    })
    assert r.status_code == 409
    assert "conflict" in r.json()["detail"].lower()


# ── Force-complete window ──────────────────────────────────────────────────

def test_force_complete_too_early(client, as_admin):
    """force-complete a scheduled session before end_time+24h → 400."""
    _, t, s = _seed_users(client)
    # Schedule one starting 30 min from now and ending 1.5h from now.
    start = _future(0.5)
    create = client.post("/sessions/", json={
        "teacher_id": t, "student_id": s,
        "start_time": _iso(start), "end_time": _iso(start + timedelta(hours=1)),
    }).json()
    sid = create["id"]

    r = client.post(f"/sessions/{sid}/complete")
    assert r.status_code == 400
    assert "24 hours" in r.json()["detail"]


def test_force_complete_after_window_succeeds(client, as_admin):
    """After 24h past end_time, complete succeeds and decrements sessions_left."""
    _, t, s = _seed_users(client)
    # Create directly in DB at status=scheduled with end_time well in the past.
    db = TestingSessionLocal()
    past_start = datetime.now(timezone.utc) - timedelta(days=3)
    row = SessionModel(
        teacher_id=t, student_id=s,
        start_time=past_start.replace(tzinfo=None),
        end_time=(past_start + timedelta(hours=1)).replace(tzinfo=None),
        status="scheduled",
        version=0,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    sid = row.id
    student_row = db.query(User).filter(User.id == s).first()
    before_left = student_row.sessions_left
    db.close()

    r = client.post(f"/sessions/{sid}/complete")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "completed"
    assert r.json()["is_force_completed"] is True

    # sessions_left decremented.
    db = TestingSessionLocal()
    student_row = db.query(User).filter(User.id == s).first()
    assert student_row.sessions_left == before_left - 1
    db.close()


# ── Window resolved end_time when omitted ─────────────────────────────────

def test_propose_defaults_end_time_to_one_hour(client, as_admin):
    """If client omits end_time, server fills in start + 1h."""
    _, t, s = _seed_users(client)
    student_user = _make_user_obj(s, "student", "Student")
    _swap_to_student(student_user)
    start = _future(36)
    r = client.post("/sessions/propose/student", json={
        "teacher_id": t,
        "student_id": s,
        "start_time": _iso(start),
        # no end_time
    })
    assert r.status_code == 200, r.text
    body = r.json()
    start_back = datetime.fromisoformat(body["start_time"].replace("Z", "+00:00"))
    end_back = datetime.fromisoformat(body["end_time"].replace("Z", "+00:00"))
    delta = end_back - start_back
    assert timedelta(minutes=59) <= delta <= timedelta(minutes=61)
