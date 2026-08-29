"""The object-storage backend.

No network here: httpx is stubbed, so these assert the contract we depend on —
the right bucket URL, the service key on the request, and a round trip through
``put``/``get`` — without a Supabase project.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.config import settings  # noqa: E402
from backend.utils import storage  # noqa: E402


@pytest.fixture()
def remote(monkeypatch):
    monkeypatch.setattr(settings, "SUPABASE_URL", "https://proj.supabase.co", raising=False)
    monkeypatch.setattr(settings, "SUPABASE_SERVICE_KEY", "service-key", raising=False)
    monkeypatch.setattr(settings, "SUPABASE_BUCKET", "uploads", raising=False)


class _Response:
    def __init__(self, status_code=200, content=b"", headers=None):
        self.status_code = status_code
        self.content = content
        self.headers = headers or {}
        self.text = content.decode(errors="replace")


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


def test_remote_put_targets_the_bucket_with_the_service_key(remote, monkeypatch):
    seen = {}

    def fake_post(url, content, headers, timeout):
        seen.update(url=url, content=content, headers=headers)
        return _Response(200)

    monkeypatch.setattr(storage.httpx, "post", fake_post)

    key = storage.put("proofs", "abc.webp", b"image-bytes", "image/webp")

    assert key == "proofs/abc.webp"
    assert seen["url"] == "https://proj.supabase.co/storage/v1/object/uploads/proofs/abc.webp"
    assert seen["content"] == b"image-bytes"
    assert seen["headers"]["Authorization"] == "Bearer service-key"
    assert seen["headers"]["Content-Type"] == "image/webp"


def test_remote_put_raises_when_the_bucket_rejects_it(remote, monkeypatch):
    monkeypatch.setattr(
        storage.httpx, "post",
        lambda url, content, headers, timeout: _Response(403, b"denied"),
    )
    with pytest.raises(RuntimeError):
        storage.put("proofs", "abc.webp", b"x", "image/webp")


def test_remote_get_returns_none_for_a_missing_object(remote, monkeypatch):
    monkeypatch.setattr(
        storage.httpx, "get",
        lambda url, headers, timeout: _Response(404, b"not found"),
    )
    assert storage.get("proofs", "gone.webp") is None


def test_remote_get_returns_bytes_and_content_type(remote, monkeypatch):
    monkeypatch.setattr(
        storage.httpx, "get",
        lambda url, headers, timeout: _Response(200, b"webp-bytes", {"content-type": "image/webp"}),
    )
    data, content_type = storage.get("proofs", "abc.webp")
    assert data == b"webp-bytes"
    assert content_type == "image/webp"
