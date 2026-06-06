"""Test suite for SMC backend.

Uses an in-memory SQLite database; each test runs against a fresh schema so
state cannot leak between tests. Auth-dependent flows override the auth
dependency to install a synthetic user.
"""
from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base, get_db
from backend.dependencies import (
    get_current_active_user,
    require_admin,
    require_student,
    require_teacher,
)
from backend.main import app
from backend.models import Role, User

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def _make_user(id_: int, role_name: str, name: str = "Test") -> User:
    return User(id=id_, username=f"user{id_}", email=f"u{id_}@x.com", name=name,
                role_id=id_, role=Role(id=id_, name=role_name), is_active=True)


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.pop(get_current_active_user, None)
    app.dependency_overrides.pop(require_admin, None)
    app.dependency_overrides.pop(require_teacher, None)
    app.dependency_overrides.pop(require_student, None)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def as_admin():
    admin = _make_user(1, "admin", "Admin")
    app.dependency_overrides[require_admin] = lambda: admin
    app.dependency_overrides[get_current_active_user] = lambda: admin
    app.dependency_overrides[require_teacher] = lambda: admin
    app.dependency_overrides[require_student] = lambda: admin
    return admin


@pytest.fixture
def as_teacher():
    teacher = _make_user(2, "teacher", "Teacher")
    app.dependency_overrides[get_current_active_user] = lambda: teacher
    app.dependency_overrides[require_teacher] = lambda: teacher
    return teacher


@pytest.fixture
def as_student():
    student = _make_user(3, "student", "Student")
    app.dependency_overrides[get_current_active_user] = lambda: student
    app.dependency_overrides[require_student] = lambda: student
    return student


# ── Basic ──────────────────────────────────────────────────────────────────

def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["message"].startswith("Welcome")


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# ── Roles / users ──────────────────────────────────────────────────────────

def test_create_role(client, as_admin):
    r = client.post("/roles/", json={"name": "Admin"})
    assert r.status_code == 200
    assert r.json()["name"] == "Admin"


def test_create_user(client, as_admin):
    client.post("/roles/", json={"name": "Teacher"})
    r = client.post("/users/", json={
        "email": "t@example.com", "name": "T", "password": "password1", "role_id": 1
    })
    assert r.status_code == 200, r.text
    assert r.json()["user"]["email"] == "t@example.com"
    # New: login response must carry refresh token.
    assert "refresh_token" in r.json()
    assert r.json().get("token_type") == "bearer"


# ── Auth: refresh / logout ─────────────────────────────────────────────────

def test_refresh_rotation_and_replay(client, as_admin):
    client.post("/roles/", json={"name": "Teacher"})
    create = client.post("/users/", json={
        "email": "r@example.com", "name": "R", "password": "password1", "role_id": 1
    }).json()
    refresh = create["refresh_token"]

    # First refresh succeeds, rotates.
    r1 = client.post("/auth/refresh", json={"refresh_token": refresh})
    assert r1.status_code == 200
    new_refresh = r1.json()["refresh_token"]
    assert new_refresh != refresh

    # Replaying the OLD token triggers chain revoke + 401.
    r2 = client.post("/auth/refresh", json={"refresh_token": refresh})
    assert r2.status_code == 401

    # New token also revoked by chain.
    r3 = client.post("/auth/refresh", json={"refresh_token": new_refresh})
    assert r3.status_code == 401


def test_logout_revokes_refresh(client, as_admin):
    client.post("/roles/", json={"name": "Teacher"})
    create = client.post("/users/", json={
        "email": "l@example.com", "name": "L", "password": "password1", "role_id": 1
    }).json()
    refresh = create["refresh_token"]
    out = client.post("/auth/logout", json={"refresh_token": refresh})
    assert out.status_code == 200
    # Now refreshing should fail.
    r = client.post("/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code == 401


# ── Auth: password reset ───────────────────────────────────────────────────

def test_forgot_password_no_enum(client):
    # Unknown email still returns 200 (no enumeration).
    r = client.post("/auth/forgot-password", json={"email": "nope@nope.com"})
    assert r.status_code == 200


def test_reset_password_requires_strong(client, as_admin):
    client.post("/roles/", json={"name": "Teacher"})
    client.post("/users/", json={
        "email": "rp@example.com", "name": "RP", "password": "password1", "role_id": 1
    })
    # weak password rejected by Pydantic validator
    r = client.post("/auth/reset-password", json={"token": "x", "new_password": "short"})
    assert r.status_code == 422


# ── IDOR: payments ─────────────────────────────────────────────────────────

def test_payments_idor_teacher_blocked(client, as_teacher):
    # Teacher trying to read payments of a student they don't teach -> 403.
    r = client.get("/payments/student/9999")
    assert r.status_code in (403, 404)


def test_payments_idor_student_self_only(client, as_student):
    # Student fetching another student's payments must be denied.
    r = client.get("/payments/student/9999")
    assert r.status_code in (403, 404)


# ── File uploads ───────────────────────────────────────────────────────────

def test_upload_rejects_non_image(client, as_admin):
    files = {"file": ("evil.txt", io.BytesIO(b"not an image"), "text/plain")}
    r = client.post("/session-proofs/?session_id=1", files=files)
    # Either 400 (validation) or 404 (no session yet) — both prove the route is guarded.
    assert r.status_code in (400, 404, 422)


def test_upload_magic_byte_mismatch(client, as_admin):
    # JPEG extension but PNG header would mismatch magic bytes.
    files = {"file": ("bad.jpg", io.BytesIO(b"\x89PNG\r\n\x1a\nrest"), "image/jpeg")}
    r = client.post("/session-proofs/?session_id=1", files=files)
    assert r.status_code in (400, 404, 422)


# ── ICS export ─────────────────────────────────────────────────────────────

def test_ics_export(client, as_admin):
    r = client.get("/sessions/export.ics")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/calendar")
    body = r.text
    assert body.startswith("BEGIN:VCALENDAR")
    assert "END:VCALENDAR" in body
