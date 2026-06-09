"""Tests for the HttpOnly refresh cookie introduced in Phase 2.

The refresh token used to live in localStorage on the frontend, which
meant any XSS in the SPA could exfiltrate it. The cookie path is now:

  * /login, /users/, /auth/2fa/verify, /auth/refresh — set the cookie.
  * /auth/refresh, /auth/logout — read from cookie when body is absent.
  * /auth/logout — always clear the cookie.

These tests pin the attributes (HttpOnly, SameSite, Path) and confirm
both the cookie-only and body-only paths work, plus that the legacy
body path still wins over the cookie for backward compatibility.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.config import settings
from backend.main import app
from backend.test_main import as_admin, client, fresh_db  # noqa: F401

COOKIE_NAME = settings.REFRESH_COOKIE_NAME


def _create_user(client) -> dict:
    client.post("/roles/", json={"name": "Teacher"})
    return client.post("/users/", json={
        "email": "cookie@example.com", "name": "C", "password": "password1", "role_id": 1,
    }).json()


# ── Cookie is set on login / create ────────────────────────────────────────

def test_create_user_sets_refresh_cookie(client, as_admin):
    """POST /users/ (which logs the new user in) must drop the cookie."""
    create = client.post("/roles/", json={"name": "Teacher"})
    assert create.status_code == 200
    r = client.post("/users/", json={
        "email": "newcookie@example.com", "name": "NC", "password": "password1", "role_id": 1,
    })
    assert r.status_code == 200
    set_cookie = r.headers.get("set-cookie", "")
    assert COOKIE_NAME in set_cookie
    # HttpOnly is the whole point of this change — assert loudly.
    assert "HttpOnly" in set_cookie
    # Path scopes the cookie to /auth so it never accompanies API calls.
    assert f"Path={settings.REFRESH_COOKIE_PATH}" in set_cookie
    # SameSite present (browser would default to Lax otherwise; we set it).
    assert "SameSite" in set_cookie


# ── Refresh works using only the cookie ───────────────────────────────────

def test_refresh_uses_cookie_when_body_absent(client, as_admin):
    """POSTing to /auth/refresh with no body must succeed via cookie."""
    create = _create_user(client)
    original_refresh = create["refresh_token"]

    # No body at all — server must read the cookie set by /users/.
    r = client.post("/auth/refresh")
    assert r.status_code == 200, r.text
    new_pair = r.json()
    assert new_pair["refresh_token"] != original_refresh
    # New cookie set on rotation.
    assert COOKIE_NAME in r.headers.get("set-cookie", "")


# ── Body still wins (replay detection preserved) ──────────────────────────

def test_body_token_wins_over_cookie(client, as_admin):
    """If the body contains a (stale) refresh token, it must be used even
    when the cookie has a fresher one. This keeps the replay-revoke chain
    intact for legacy non-cookie clients."""
    create = _create_user(client)
    original = create["refresh_token"]

    # First refresh — cookie is now fresh, body presents the original.
    # Both are valid here; server uses body.
    r1 = client.post("/auth/refresh", json={"refresh_token": original})
    assert r1.status_code == 200

    # Replay original (now revoked); body wins → 401 + revoke-chain.
    r2 = client.post("/auth/refresh", json={"refresh_token": original})
    assert r2.status_code == 401
    assert "reuse" in r2.json()["detail"].lower()


# ── Logout clears cookie ──────────────────────────────────────────────────

def test_logout_clears_cookie(client, as_admin):
    _create_user(client)
    r = client.post("/auth/logout")
    assert r.status_code == 200
    # FastAPI's delete_cookie emits a Set-Cookie with an empty value AND
    # an expired Max-Age — either marker proves the clear was sent.
    set_cookie = r.headers.get("set-cookie", "")
    assert COOKIE_NAME in set_cookie
    assert ("Max-Age=0" in set_cookie) or ('=""' in set_cookie) or (f"{COOKIE_NAME}=;" in set_cookie)


# ── No tokens at all → 401 ─────────────────────────────────────────────────

def test_refresh_without_token_or_cookie_rejected():
    """A pristine client with neither cookie nor body must get 401."""
    bare_client = TestClient(app)
    r = bare_client.post("/auth/refresh")
    assert r.status_code == 401
    assert "required" in r.json()["detail"].lower()
