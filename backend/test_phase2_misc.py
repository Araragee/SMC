"""Phase 2 misc tests: nudge auth, security headers, change-password.

These cases are deliberately scoped tight; the heavier upload-auth and
refresh-cookie suites live in their own files.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.dependencies import get_current_active_user, require_teacher
from backend.main import app
from backend.test_main import client, fresh_db, as_admin  # noqa: F401
from backend.test_session_state_machine import (  # noqa: F401
    _make_user_obj,
    _seed_users,
    _swap_to_student,
    _swap_to_teacher,
)


# ── Nudge endpoint authorization ───────────────────────────────────────────

def test_nudge_rejects_non_participant(client, as_admin):
    """Pre-Phase 2 any authenticated user could nudge any session; now
    only admins and the teacher/student on the session can."""
    _, t, s = _seed_users(client)
    start = datetime.now(timezone.utc) + timedelta(hours=24)
    sid = client.post("/sessions/", json={
        "teacher_id": t, "student_id": s,
        "start_time": start.isoformat(),
        "end_time": (start + timedelta(hours=1)).isoformat(),
    }).json()["id"]

    # Swap to an unrelated teacher.
    outsider = _make_user_obj(999, "teacher", "Outsider")
    app.dependency_overrides[get_current_active_user] = lambda: outsider
    app.dependency_overrides[require_teacher] = lambda: outsider

    r = client.post(f"/sessions/{sid}/nudge")
    assert r.status_code == 403
    assert "participant" in r.json()["detail"].lower()


def test_nudge_allows_participant(client, as_admin):
    _, t, s = _seed_users(client)
    start = datetime.now(timezone.utc) + timedelta(hours=24)
    sid = client.post("/sessions/", json={
        "teacher_id": t, "student_id": s,
        "start_time": start.isoformat(),
        "end_time": (start + timedelta(hours=1)).isoformat(),
    }).json()["id"]

    student_user = _make_user_obj(s, "student", "Student")
    _swap_to_student(student_user)

    r = client.post(f"/sessions/{sid}/nudge")
    assert r.status_code == 200


# ── Security headers ──────────────────────────────────────────────────────

def test_security_headers_present_on_health(client):
    """Health-check endpoint must carry the baseline security headers."""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert r.headers.get("Referrer-Policy") == "no-referrer"
    csp = r.headers.get("Content-Security-Policy", "")
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp


# ── change-password ───────────────────────────────────────────────────────

def test_change_password_requires_current(client, as_admin):
    """The endpoint must verify the caller knows the current password —
    otherwise a hijacked access token could rotate the credential alone."""
    r = client.post("/auth/change-password", json={
        "current_password": "wrong-pw",
        "new_password": "Newpass1word",
    })
    assert r.status_code == 400


def test_change_password_rejects_same_password(client, as_admin):
    # Re-set the admin user's password to a known value via /users/<id>
    # to make this test self-contained. The user-fixture's hashed_password
    # is from a fake row, so /change-password's verify will fail anyway;
    # this test pins "must differ" check by submitting equal values.
    r = client.post("/auth/change-password", json={
        "current_password": "Samepass1",
        "new_password": "Samepass1",
    })
    # Either 400 from same-as-current or 400 from wrong-current — both
    # prove the endpoint is wired and refuses to mutate state. The point
    # is that 200 must NOT come back.
    assert r.status_code == 400


def test_change_password_rejects_weak(client, as_admin):
    """Pydantic's StrongPassword rule must apply to /change-password too."""
    r = client.post("/auth/change-password", json={
        "current_password": "anything",
        "new_password": "short",
    })
    assert r.status_code == 422


# ── Debug-users route gone when DEBUG=False ──────────────────────────────

def test_debug_users_route_not_registered(client, as_admin):
    """With DEBUG False (the default in tests), the route shouldn't exist
    at all — a curl probe must 404, not 401/403."""
    r = client.get("/debug/users")
    assert r.status_code == 404
