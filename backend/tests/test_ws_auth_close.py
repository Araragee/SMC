"""An unauthenticated socket must be *accepted* and then closed with 4001.

Closing before ``accept()`` makes Starlette answer the upgrade with a bare
403. A browser surfaces that as "WebSocket connection failed" — the very same
message it gives when the server is unreachable — so the client could not tell
a dead token from a dead backend. Since the access token lasts 15 minutes and
only an HTTP 401 renews it, a tab left open on this push-only channel retried
forever with a token the server had already refused.
"""
from __future__ import annotations

import asyncio

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("jwt")

from datetime import timedelta  # noqa: E402

from backend.dependencies import create_access_token  # noqa: E402
from backend.routers.messaging import WS_UNAUTHORIZED, websocket_endpoint  # noqa: E402


class _FakeWebSocket:
    """Records the order of accept/close so the test can assert on it."""

    def __init__(self, protocol_header: str | None = None):
        self.headers = {}
        if protocol_header is not None:
            self.headers["sec-websocket-protocol"] = protocol_header
        self.calls: list[tuple] = []

    async def accept(self, subprotocol: str | None = None):
        self.calls.append(("accept", subprotocol))

    async def close(self, code: int | None = None):
        self.calls.append(("close", code))


def _run(ws, user_id=1, token=None):
    asyncio.run(websocket_endpoint(user_id=user_id, websocket=ws, token=token))
    return ws.calls


def test_a_missing_token_is_accepted_then_closed_with_4001():
    calls = _run(_FakeWebSocket())
    assert calls == [("accept", None), ("close", WS_UNAUTHORIZED)]


def test_a_garbage_token_is_accepted_then_closed_with_4001():
    ws = _FakeWebSocket("jwt, not.a.real.token")
    calls = _run(ws)
    assert calls == [("accept", "jwt"), ("close", WS_UNAUTHORIZED)]


def test_a_token_for_another_user_is_rejected():
    """A valid signature is not enough — it must name the socket's own user."""
    token = create_access_token({"sub": "someone", "user_id": 99},
                                expires_delta=timedelta(minutes=5))
    ws = _FakeWebSocket(f"jwt, {token}")
    calls = _run(ws, user_id=1)
    assert calls == [("accept", "jwt"), ("close", WS_UNAUTHORIZED)]


def test_an_expired_token_is_rejected_rather_than_crashing():
    """The case that drove this: expiry must be a clean 4001, not a 500."""
    token = create_access_token({"sub": "someone", "user_id": 1},
                                expires_delta=timedelta(minutes=-5))
    ws = _FakeWebSocket(f"jwt, {token}")
    calls = _run(ws, user_id=1)
    assert calls == [("accept", "jwt"), ("close", WS_UNAUTHORIZED)]


def test_the_rejection_echoes_the_subprotocol_it_was_offered():
    """A browser aborts the handshake if the server names a protocol it did
    not offer, which would turn the 4001 back into an opaque failure."""
    ws = _FakeWebSocket("jwt, bad")
    _run(ws)
    assert ws.calls[0] == ("accept", "jwt")
