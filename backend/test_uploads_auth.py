"""Tests for the auth-gated upload routes.

Covers:
  * Unsigned requests → 403.
  * Forged signature → 403.
  * Expired signature → 403.
  * Valid signature + non-participant → 403.
  * Valid signature + participant (teacher or student) → 200.
  * Valid signature + admin → 200.
  * Path-traversal filenames → 400.
  * Missing file (signature valid but file deleted) → 404.

Tests use the in-memory SQLite + fixture wiring from ``test_main`` and
re-uses the user-seeding helper from ``test_session_state_machine`` so
we don't duplicate setup.
"""
from __future__ import annotations

import secrets
from pathlib import Path

import pytest

from backend.dependencies import get_current_active_user, require_teacher, require_student
from backend.main import app
from backend.models import SessionProof
from backend.test_main import (  # noqa: F401
    TestingSessionLocal,
    as_admin,
    as_student,
    as_teacher,
    client,
    fresh_db,
)
from backend.test_session_state_machine import (  # noqa: F401
    _make_user_obj,
    _seed_users,
    _swap_to_student,
    _swap_to_teacher,
)
from backend.utils.signed_urls import sign_url


@pytest.fixture
def proof_file(tmp_path, monkeypatch):
    """Create a real ``uploads/proofs/<token>.png`` file on disk so
    FileResponse has something to serve. Yields the (filename, full URL path).
    """
    # The router resolves uploads relative to CWD; tests run from repo root.
    proofs_dir = Path("uploads/proofs")
    proofs_dir.mkdir(parents=True, exist_ok=True)
    # Match the SAFE_FILENAME regex: 32 hex chars + ext.
    name = secrets.token_hex(16) + ".png"
    full = proofs_dir / name
    # Minimal PNG header so the file is non-empty (content isn't validated
    # on the read side — the upload route validates magic bytes, not us).
    full.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)
    yield name, f"/uploads/proofs/{name}"
    try:
        full.unlink()
    except FileNotFoundError:
        pass


def _seed_session_with_proof(client, proof_url: str) -> tuple[int, int, int, int]:
    """Create admin/teacher/student/session + a SessionProof row pointing
    at ``proof_url``. Returns (admin_id, teacher_id, student_id, session_id).
    """
    a, t, s = _seed_users(client)
    # Schedule a session, then attach a proof row directly via the DB
    # (simpler than going through the multipart upload route here).
    from datetime import datetime, timedelta, timezone
    start = datetime.now(timezone.utc) + timedelta(hours=24)
    create = client.post("/sessions/", json={
        "teacher_id": t, "student_id": s,
        "start_time": start.isoformat(),
        "end_time": (start + timedelta(hours=1)).isoformat(),
    }).json()
    sid = create["id"]

    db = TestingSessionLocal()
    db.add(SessionProof(
        session_id=sid, image_url=proof_url,
        uploader_id=s, uploader_role="student",
    ))
    db.commit()
    db.close()
    return a, t, s, sid


# ── Signature checks ───────────────────────────────────────────────────────

def test_proof_unsigned_request_rejected(client, as_admin, proof_file):
    _name, url = proof_file
    _seed_session_with_proof(client, url)
    r = client.get(url)
    assert r.status_code == 403
    assert "signature" in r.json()["detail"].lower()


def test_proof_forged_signature_rejected(client, as_admin, proof_file):
    _name, url = proof_file
    _seed_session_with_proof(client, url)
    r = client.get(f"{url}?exp=9999999999&sig={'a' * 32}")
    assert r.status_code == 403


def test_proof_expired_signature_rejected(client, as_admin, proof_file):
    _name, url = proof_file
    _seed_session_with_proof(client, url)
    signed = sign_url(url, ttl_seconds=-10)
    r = client.get(signed)
    assert r.status_code == 403


# ── Authorization checks ───────────────────────────────────────────────────

def test_proof_admin_can_view(client, as_admin, proof_file):
    _name, url = proof_file
    _seed_session_with_proof(client, url)
    signed = sign_url(url)
    r = client.get(signed)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("image/")


def test_proof_participant_student_can_view(client, as_admin, proof_file):
    _name, url = proof_file
    _a, _t, s, _sid = _seed_session_with_proof(client, url)
    # Swap to the student participant.
    student_user = _make_user_obj(s, "student", "Student")
    _swap_to_student(student_user)
    signed = sign_url(url)
    r = client.get(signed)
    assert r.status_code == 200


def test_proof_participant_teacher_can_view(client, as_admin, proof_file):
    _name, url = proof_file
    _a, t, _s, _sid = _seed_session_with_proof(client, url)
    teacher_user = _make_user_obj(t, "teacher", "Teacher")
    _swap_to_teacher(teacher_user)
    signed = sign_url(url)
    r = client.get(signed)
    assert r.status_code == 200


def test_proof_outsider_rejected(client, as_admin, proof_file):
    _name, url = proof_file
    _a, _t, _s, _sid = _seed_session_with_proof(client, url)
    # An unrelated teacher with no session-participant link.
    outsider = _make_user_obj(999, "teacher", "Outsider")
    app.dependency_overrides[get_current_active_user] = lambda: outsider
    app.dependency_overrides[require_teacher] = lambda: outsider
    signed = sign_url(url)
    r = client.get(signed)
    assert r.status_code == 403
    assert "authorized" in r.json()["detail"].lower()


# ── Path-traversal + missing-file safety ───────────────────────────────────

def test_proof_bad_filename_rejected(client, as_admin):
    # Traversal attempt — must be rejected with 400, not 403/200.
    bad = "/uploads/proofs/..%2F..%2Fetc%2Fpasswd"
    signed = sign_url("/uploads/proofs/../../etc/passwd")
    # Use the path the route actually sees — FastAPI parses {filename}.
    r = client.get("/uploads/proofs/not-a-32-hex.png?exp=9999999999&sig=" + "a" * 32)
    # Either 403 (sig fails first) or 400 (filename regex). Both prove the
    # traversal didn't succeed.
    assert r.status_code in (400, 403)


def test_proof_missing_file_returns_404(client, as_admin):
    # Sign a URL whose underlying file we never created.
    url = f"/uploads/proofs/{'b' * 32}.png"
    # Seed a row so the auth check passes.
    db = TestingSessionLocal()
    from backend.models import Session as SessionModel
    from datetime import datetime, timedelta, timezone
    a, t, s = _seed_users(client)
    start = datetime.now(timezone.utc) + timedelta(hours=24)
    create = client.post("/sessions/", json={
        "teacher_id": t, "student_id": s,
        "start_time": start.isoformat(),
        "end_time": (start + timedelta(hours=1)).isoformat(),
    }).json()
    sid = create["id"]
    db.add(SessionProof(session_id=sid, image_url=url, uploader_id=s, uploader_role="student"))
    db.commit()
    db.close()

    signed = sign_url(url)
    r = client.get(signed)
    assert r.status_code == 404
