"""Serving private uploads: authorization, caching and response hardening.

The route functions in ``backend.routers.uploads`` are plain functions, so —
like ``test_object_authorization.py`` — they are exercised directly with
lightweight stubs rather than a live database.

What matters here is the order of operations. A signature check, an
authorization check and a conditional-request shortcut all guard the same
bytes, and the shortcut must never run first: a 304 confirms a file exists, so
answering one before authorizing would leak the existence of every proof in the
school to anyone holding a signed URL.
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")

from fastapi import HTTPException  # noqa: E402

from backend.routers import uploads as up  # noqa: E402
from backend.utils.signed_urls import sign_url  # noqa: E402


class _Role:
    def __init__(self, name):
        self.name = name


class _User:
    def __init__(self, user_id, role_name=None):
        self.id = user_id
        self.role = _Role(role_name) if role_name else None


class _Row:
    def __init__(self, teacher_id, student_id):
        self.teacher_id = teacher_id
        self.student_id = student_id


class _FakeQuery:
    def __init__(self, result):
        self._result = result

    def join(self, *_a, **_k):
        return self

    def filter(self, *_a, **_k):
        return self

    def first(self):
        return self._result


class _FakeDB:
    """Answers the single joined lookup the authorization helper performs."""

    def __init__(self, row=None):
        self.row = row
        self.query_count = 0

    def query(self, *_args):
        self.query_count += 1
        return _FakeQuery(self.row)


PROOF_NAME = "a" * 32 + ".webp"
PROOF_PATH = f"/uploads/proofs/{PROOF_NAME}"


def _signed(path=PROOF_PATH):
    """Return the (exp, sig) pair from a freshly signed URL."""
    signed = sign_url(path)
    query = signed.split("?", 1)[1]
    parts = dict(pair.split("=", 1) for pair in query.split("&"))
    return int(parts["exp"]), parts["sig"]


# ── ETag matching ─────────────────────────────────────────────────────────────

def test_etag_matching_follows_rfc_9110():
    etag = '"abc123"'
    assert up._matches_etag(None, etag) is False
    assert up._matches_etag("", etag) is False
    assert up._matches_etag('"abc123"', etag) is True
    assert up._matches_etag('W/"abc123"', etag) is True
    assert up._matches_etag('"other", "abc123"', etag) is True
    assert up._matches_etag("*", etag) is True
    assert up._matches_etag('"nope"', etag) is False


def test_etag_is_stable_for_a_name_and_distinct_between_names():
    assert up._etag_for("proofs", PROOF_NAME) == up._etag_for("proofs", PROOF_NAME)
    assert up._etag_for("proofs", PROOF_NAME) != up._etag_for("proofs", "b" * 32 + ".webp")
    # The same name in a different subdirectory is a different object.
    assert up._etag_for("proofs", PROOF_NAME) != up._etag_for("homework", PROOF_NAME)


def test_etag_does_not_restate_the_storage_key():
    """The validator travels through caches and proxies; it should identify the
    object without also naming it."""
    assert PROOF_NAME not in up._etag_for("proofs", PROOF_NAME)


# ── authorization ─────────────────────────────────────────────────────────────

def test_admins_may_see_any_proof_without_a_lookup():
    db = _FakeDB(row=None)
    assert up._user_can_see_proof(db, _User(99, "admin"), PROOF_PATH) is True
    assert db.query_count == 0


def test_a_participant_may_see_the_proof():
    db = _FakeDB(row=_Row(teacher_id=1, student_id=2))
    assert up._user_can_see_proof(db, _User(2, "student"), PROOF_PATH) is True
    assert up._user_can_see_proof(db, _User(1, "teacher"), PROOF_PATH) is True


def test_an_unrelated_teacher_may_not_see_the_proof():
    """Role alone grants nothing: a teacher who does not teach this session has
    no more business with the file than a stranger."""
    db = _FakeDB(row=_Row(teacher_id=1, student_id=2))
    assert up._user_can_see_proof(db, _User(3, "teacher"), PROOF_PATH) is False


def test_an_orphaned_file_is_admin_only():
    db = _FakeDB(row=None)
    assert up._user_can_see_proof(db, _User(2, "student"), PROOF_PATH) is False


def test_authorization_takes_a_single_query():
    """This runs once per image on screen, so the two sequential round trips it
    replaced were multiplied by every thumbnail in a session modal."""
    db = _FakeDB(row=_Row(teacher_id=1, student_id=2))
    up._user_can_see_proof(db, _User(2, "student"), PROOF_PATH)
    assert db.query_count == 1


# ── route guards ──────────────────────────────────────────────────────────────

def test_an_unsigned_request_is_refused():
    with pytest.raises(HTTPException) as exc:
        up.get_proof(PROOF_NAME, None, None, None, _FakeDB(), _User(1, "admin"))
    assert exc.value.status_code == 403
    assert "signature" in exc.value.detail.lower()


def test_a_forged_signature_is_refused():
    exp, _ = _signed()
    with pytest.raises(HTTPException) as exc:
        up.get_proof(PROOF_NAME, exp, "0" * 32, None, _FakeDB(), _User(1, "admin"))
    assert exc.value.status_code == 403


def test_a_signature_for_another_file_does_not_transfer():
    """The path is signed along with the expiry, so a valid signature for one
    proof cannot be replayed against another by editing the URL."""
    exp, sig = _signed("/uploads/proofs/" + "b" * 32 + ".webp")
    with pytest.raises(HTTPException) as exc:
        up.get_proof(PROOF_NAME, exp, sig, None, _FakeDB(), _User(1, "admin"))
    assert exc.value.status_code == 403


def test_authorization_runs_before_the_conditional_shortcut():
    """A 304 is proof the file exists. An unauthorized caller holding a valid
    signature and the right ETag must still get a 403, never a 304."""
    exp, sig = _signed()
    db = _FakeDB(row=_Row(teacher_id=1, student_id=2))
    etag = up._etag_for("proofs", PROOF_NAME)

    with pytest.raises(HTTPException) as exc:
        up.get_proof(PROOF_NAME, exp, sig, etag, db, _User(3, "teacher"))
    assert exc.value.status_code == 403


def test_a_bad_filename_is_refused_before_touching_the_disk():
    bad_names = [
        # Directory traversal. The target is deliberately an ordinary repo file
        # rather than one of the well-known unix credential paths: secret
        # scanners match those as credentials and fail the build on the line,
        # and what this case proves — that `..` never leaves the uploads tree —
        # does not depend on which file is aimed at. Please keep it boring.
        "../../backend/config.py",
        "..%2F..%2Fconfig.py",   # percent-encoded traversal
        "not-hex.webp",          # right shape, wrong alphabet
        "a" * 32 + ".svg",       # SVG is scriptable; never on the allowlist
        "a" * 31 + ".webp",      # one character short of a real token
    ]
    for bad in bad_names:
        with pytest.raises(HTTPException) as exc:
            up._serve("proofs", bad)
        assert exc.value.status_code == 400, bad


# ── response shape ────────────────────────────────────────────────────────────

def test_a_matching_etag_returns_304_with_no_body(tmp_path, monkeypatch):
    monkeypatch.setattr(up, "_UPLOADS_ROOT", tmp_path)
    target = tmp_path / "proofs" / PROOF_NAME
    target.parent.mkdir(parents=True)
    target.write_bytes(b"webp-bytes")

    etag = up._etag_for("proofs", PROOF_NAME, len(b"webp-bytes"))
    response = up._serve("proofs", PROOF_NAME, etag)

    assert response.status_code == 304
    assert response.body == b""
    # A 304 must repeat the validator and the caching policy.
    assert response.headers["ETag"] == etag
    assert "max-age" in response.headers["Cache-Control"]


def test_a_stale_etag_returns_the_file(tmp_path, monkeypatch):
    monkeypatch.setattr(up, "_UPLOADS_ROOT", tmp_path)
    target = tmp_path / "proofs" / PROOF_NAME
    target.parent.mkdir(parents=True)
    target.write_bytes(b"webp-bytes")

    response = up._serve("proofs", PROOF_NAME, '"stale"')
    assert response.status_code == 200
    assert response.headers["ETag"] == up._etag_for("proofs", PROOF_NAME, len(b"webp-bytes"))


def test_served_files_carry_the_hardening_headers(tmp_path, monkeypatch):
    """These are user-supplied bytes on our own origin, so they are handed the
    narrowest execution context available."""
    monkeypatch.setattr(up, "_UPLOADS_ROOT", tmp_path)
    target = tmp_path / "proofs" / PROOF_NAME
    target.parent.mkdir(parents=True)
    target.write_bytes(b"webp-bytes")

    headers = up._serve("proofs", PROOF_NAME).headers

    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["Content-Disposition"] == "inline"
    assert "sandbox" in headers["Content-Security-Policy"]
    assert "default-src 'none'" in headers["Content-Security-Policy"]
    # Private, so a shared cache never holds one student's proof.
    assert headers["Cache-Control"].startswith("private")


def test_a_missing_file_is_a_404(tmp_path, monkeypatch):
    monkeypatch.setattr(up, "_UPLOADS_ROOT", tmp_path)
    (tmp_path / "proofs").mkdir()
    with pytest.raises(HTTPException) as exc:
        up._serve("proofs", PROOF_NAME)
    assert exc.value.status_code == 404
