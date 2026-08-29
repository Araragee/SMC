"""Tests for secure upload handling (``backend.utils.uploads``).

Covers the three defences the helper promises: extension allow-listing,
magic-byte validation (anti MIME-spoofing), and the hard size cap. Also
exercises the happy path, which normalises images to WEBP.
"""
from __future__ import annotations

import io

import pytest

# Upload helper hard-depends on FastAPI (UploadFile/HTTPException) and Pillow.
pytest.importorskip("fastapi")
pytest.importorskip("PIL")

from fastapi import HTTPException  # noqa: E402

from backend.utils import storage  # noqa: E402
from backend.utils import uploads as up  # noqa: E402


class _FakeUpload:
    """Minimal duck-typed stand-in for starlette's UploadFile.

    ``save_upload`` only touches ``.filename`` and ``.file`` (a binary
    stream), so we avoid pulling in python-multipart just to build one.
    """

    def __init__(self, filename: str, data: bytes):
        self.filename = filename
        self.file = io.BytesIO(data)


def _png_bytes(size: tuple[int, int] = (8, 8)) -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", size, (200, 30, 30)).save(buf, format="PNG")
    return buf.getvalue()


PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


# ── magic-byte matcher ────────────────────────────────────────────────────────

def test_matches_magic_accepts_correct_png():
    assert up._matches_magic(PNG_MAGIC, "png") is True


def test_matches_magic_rejects_wrong_header():
    assert up._matches_magic(b"not-a-png-header", "png") is False


def test_matches_magic_webp_requires_both_markers():
    good = b"RIFF\x00\x00\x00\x00WEBPxxxx"
    bad = b"RIFF\x00\x00\x00\x00JUNKxxxx"
    assert up._matches_magic(good, "webp") is True
    assert up._matches_magic(bad, "webp") is False


def test_matches_magic_unknown_extension_is_false():
    assert up._matches_magic(PNG_MAGIC, "exe") is False


# ── save_upload validation ────────────────────────────────────────────────────

def test_rejects_unsupported_extension():
    f = _FakeUpload("notes.txt", b"hello")
    with pytest.raises(HTTPException) as exc:
        up.save_upload(f, "proofs")
    assert exc.value.status_code == 400
    assert "Unsupported file type" in exc.value.detail


def test_rejects_magic_mismatch():
    # Declared .png but the bytes are not a PNG ⇒ spoof attempt.
    f = _FakeUpload("evil.png", b"GIF89a-pretending-to-be-png")
    with pytest.raises(HTTPException) as exc:
        up.save_upload(f, "proofs")
    assert exc.value.status_code == 400
    assert "do not match" in exc.value.detail


def test_enforces_size_cap(monkeypatch):
    # Shrink the cap so we don't allocate 10 MB in the test.
    monkeypatch.setattr(up, "MAX_SIZE_BYTES", 16)
    oversized = PNG_MAGIC + b"\x00" * 64  # valid magic, over the cap
    f = _FakeUpload("big.png", oversized)
    with pytest.raises(HTTPException) as exc:
        up.save_upload(f, "proofs")
    assert exc.value.status_code == 400
    assert "too large" in exc.value.detail.lower()


def test_happy_path_normalises_to_webp(tmp_path, monkeypatch):
    # save_upload writes under <UPLOADS_DIR>/<subdir>/, which is relative to cwd.
    monkeypatch.chdir(tmp_path)
    f = _FakeUpload("photo.png", _png_bytes())
    public_url, key = up.save_upload(f, "proofs")
    assert public_url.startswith("/uploads/proofs/")
    assert public_url.endswith(".webp")
    subdir, _, filename = key.partition("/")
    assert storage.local_path(subdir, filename).exists()
