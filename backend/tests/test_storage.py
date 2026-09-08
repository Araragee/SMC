"""The object-storage backend.

No network here: the pooled httpx client is stubbed, so these assert the
contract we depend on — the right bucket URL, the service key on the request, a
round trip through ``put``/``get``, and the retry behaviour that keeps one
dropped connection from becoming a permanently broken image.
"""
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.config import settings  # noqa: E402
from backend.utils import storage  # noqa: E402


@pytest.fixture()
def remote(monkeypatch):
    monkeypatch.setattr(settings, "SUPABASE_URL", "https://proj.supabase.co", raising=False)
    monkeypatch.setattr(settings, "SUPABASE_SERVICE_KEY", "service-key", raising=False)
    monkeypatch.setattr(settings, "SUPABASE_BUCKET", "uploads", raising=False)


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    """Retries back off; the tests should not actually wait."""
    monkeypatch.setattr(storage.time, "sleep", lambda _seconds: None)


class _Response:
    def __init__(self, status_code=200, content=b"", headers=None):
        self.status_code = status_code
        self.content = content
        self.headers = headers or {}
        self.text = content.decode(errors="replace")


class _FakeClient:
    """Stands in for the pooled ``httpx.Client``.

    ``responses`` is a list of results to hand back in order; an ``Exception``
    entry is raised rather than returned, which is how transport failures are
    simulated.
    """

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append({"method": method, "url": url, **kwargs})
        result = self.responses.pop(0) if self.responses else _Response(200)
        if isinstance(result, Exception):
            raise result
        return result


@pytest.fixture()
def fake_client(monkeypatch):
    def install(*responses):
        client = _FakeClient(*responses)
        monkeypatch.setattr(storage, "_get_client", lambda: client)
        return client

    return install


# ── local backend ─────────────────────────────────────────────────────────────

def test_local_backend_is_the_default(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "SUPABASE_URL", "", raising=False)
    monkeypatch.chdir(tmp_path)

    assert storage.is_remote() is False
    key = storage.put("proofs", "abc.webp", b"bytes", "image/webp")
    assert key == "proofs/abc.webp"

    data, content_type = storage.get("proofs", "abc.webp")
    assert data == b"bytes"
    assert content_type == "image/webp"
    assert storage.get("proofs", "missing.webp") is None


# ── remote backend ────────────────────────────────────────────────────────────

def test_remote_put_targets_the_bucket_with_the_service_key(remote, fake_client):
    client = fake_client(_Response(200))

    key = storage.put("proofs", "abc.webp", b"image-bytes", "image/webp")

    assert key == "proofs/abc.webp"
    call = client.calls[0]
    assert call["method"] == "POST"
    assert call["url"] == "https://proj.supabase.co/storage/v1/object/uploads/proofs/abc.webp"
    assert call["content"] == b"image-bytes"
    assert call["headers"]["Authorization"] == "Bearer service-key"
    assert call["headers"]["Content-Type"] == "image/webp"


def test_remote_put_raises_when_the_bucket_rejects_it(remote, fake_client):
    fake_client(_Response(403, b"denied"))
    with pytest.raises(RuntimeError):
        storage.put("proofs", "abc.webp", b"x", "image/webp")


def test_remote_get_returns_none_for_a_missing_object(remote, fake_client):
    fake_client(_Response(404, b"not found"))
    assert storage.get("proofs", "gone.webp") is None


def test_remote_get_returns_bytes_and_content_type(remote, fake_client):
    fake_client(_Response(200, b"webp-bytes", {"content-type": "image/webp"}))
    data, content_type = storage.get("proofs", "abc.webp")
    assert data == b"webp-bytes"
    assert content_type == "image/webp"


# ── retries ───────────────────────────────────────────────────────────────────

def test_a_dropped_connection_is_retried(remote, fake_client):
    """One transient blip used to mean a permanently broken image in the UI,
    because nothing ever asked the bucket again."""
    client = fake_client(
        httpx.ConnectError("connection reset"),
        _Response(200, b"webp-bytes", {"content-type": "image/webp"}),
    )

    data, _ = storage.get("proofs", "abc.webp")

    assert data == b"webp-bytes"
    assert len(client.calls) == 2


def test_a_server_error_is_retried(remote, fake_client):
    client = fake_client(_Response(503, b"unavailable"), _Response(200))
    storage.put("proofs", "abc.webp", b"x", "image/webp")
    assert len(client.calls) == 2


def test_retries_are_bounded(remote, fake_client):
    client = fake_client(*[httpx.ConnectError("down")] * 10)
    assert storage.get("proofs", "abc.webp") is None
    assert len(client.calls) == storage._MAX_ATTEMPTS


def test_a_client_error_is_not_retried(remote, fake_client):
    """A 404 or a 403 will say the same thing however many times we ask, so
    repeating it only adds latency to a verdict that will not change."""
    client = fake_client(_Response(404, b"nope"))
    assert storage.get("proofs", "gone.webp") is None
    assert len(client.calls) == 1


# ── pooling ───────────────────────────────────────────────────────────────────

def test_the_client_is_pooled_and_closable():
    """Every thumbnail render is a request to the bucket; without a shared
    client each one paid a fresh TLS handshake first."""
    storage.close_client()
    first = storage._get_client()
    assert storage._get_client() is first
    storage.close_client()
    assert storage._client is None
