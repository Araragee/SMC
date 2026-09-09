"""Tests for secure upload handling (``backend.utils.uploads``).

Covers what the helper promises: extension allow-listing, magic-byte
validation (anti MIME-spoofing), a size cap enforced *while* reading rather
than after, and the normalisation pass — orientation, flattening, bounding and
metadata stripping — that every raster upload goes through on its way to WebP.
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


def _png_bytes(size: tuple[int, int] = (8, 8), mode: str = "RGB") -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    colour = (200, 30, 30, 255) if mode == "RGBA" else (200, 30, 30)
    Image.new(mode, size, colour).save(buf, format="PNG")
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


def test_matches_magic_heic_checks_the_ftyp_box():
    # ISO-BMFF: 4 bytes of box length, then the "ftyp" marker, then the brand.
    assert up._matches_magic(b"\x00\x00\x00\x18ftypheic", "heic") is True
    assert up._matches_magic(b"\x00\x00\x00\x18MOOVheic", "heic") is False


# ── save_upload validation ────────────────────────────────────────────────────

def test_rejects_unsupported_extension():
    f = _FakeUpload("notes.txt", b"hello")
    with pytest.raises(HTTPException) as exc:
        up.save_upload(f, "proofs")
    # 415, not 400: the client can tell "wrong format" from "bad request" and
    # say something useful about it.
    assert exc.value.status_code == 415
    assert "Unsupported file type" in exc.value.detail


def test_unsupported_extension_names_what_is_accepted():
    f = _FakeUpload("clip.gif", b"GIF89a")
    with pytest.raises(HTTPException) as exc:
        up.save_upload(f, "proofs")
    assert "heic" in exc.value.detail


def test_rejects_magic_mismatch():
    # Declared .png but the bytes are not a PNG ⇒ spoof attempt.
    f = _FakeUpload("evil.png", b"GIF89a-pretending-to-be-png")
    with pytest.raises(HTTPException) as exc:
        up.save_upload(f, "proofs")
    assert exc.value.status_code == 400
    assert "do not match" in exc.value.detail


def test_rejects_an_empty_file():
    f = _FakeUpload("empty.png", b"")
    with pytest.raises(HTTPException) as exc:
        up.save_upload(f, "proofs")
    assert exc.value.status_code == 400


def test_enforces_size_cap(monkeypatch):
    # Shrink the cap so we don't allocate 10 MB in the test.
    monkeypatch.setattr(up, "MAX_SIZE_BYTES", 16)
    oversized = PNG_MAGIC + b"\x00" * 64  # valid magic, over the cap
    f = _FakeUpload("big.png", oversized)
    with pytest.raises(HTTPException) as exc:
        up.save_upload(f, "proofs")
    assert exc.value.status_code == 413
    assert "too large" in exc.value.detail.lower()


def test_size_cap_stops_reading_instead_of_buffering_everything(monkeypatch):
    """The cap must be enforced *during* the read.

    Reading to EOF first and comparing lengths afterwards meant a body of any
    size was fully resident in memory before being refused. This asserts we
    stop shortly after crossing the limit rather than consuming the lot.
    """
    monkeypatch.setattr(up, "MAX_SIZE_BYTES", 1024)
    monkeypatch.setattr(up, "_CHUNK_BYTES", 256)

    body = PNG_MAGIC + b"\x00" * (5 * 1024 * 1024)
    f = _FakeUpload("huge.png", body)

    with pytest.raises(HTTPException) as exc:
        up.save_upload(f, "proofs")
    assert exc.value.status_code == 413

    # We stopped one chunk past the cap, nowhere near the end of the stream.
    assert f.file.tell() <= 1024 + 256


# ── normalisation ─────────────────────────────────────────────────────────────

def test_happy_path_normalises_to_webp(tmp_path, monkeypatch):
    # save_upload writes under <UPLOADS_DIR>/<subdir>/, which is relative to cwd.
    monkeypatch.chdir(tmp_path)
    f = _FakeUpload("photo.png", _png_bytes())
    public_url, key = up.save_upload(f, "proofs")
    assert public_url.startswith("/uploads/proofs/")
    assert public_url.endswith(".webp")
    subdir, _, filename = key.partition("/")
    assert storage.local_path(subdir, filename).exists()


def test_transparent_png_is_flattened_not_blackened(tmp_path, monkeypatch):
    """WebP cannot carry our RGBA input through unchanged, and converting
    straight to RGB turns transparent regions black. They must land white."""
    from PIL import Image

    monkeypatch.chdir(tmp_path)
    buf = io.BytesIO()
    Image.new("RGBA", (4, 4), (0, 0, 0, 0)).save(buf, format="PNG")

    f = _FakeUpload("logo.png", buf.getvalue())
    _, key = up.save_upload(f, "proofs")

    subdir, _, filename = key.partition("/")
    out = Image.open(storage.local_path(subdir, filename))
    assert out.mode == "RGB"
    assert out.getpixel((0, 0)) == (255, 255, 255)


def test_oversized_images_are_bounded(tmp_path, monkeypatch):
    from PIL import Image

    monkeypatch.chdir(tmp_path)
    f = _FakeUpload("wide.png", _png_bytes((up.MAX_EDGE_PX * 2, up.MAX_EDGE_PX // 2)))
    _, key = up.save_upload(f, "proofs")

    subdir, _, filename = key.partition("/")
    out = Image.open(storage.local_path(subdir, filename))
    assert max(out.size) == up.MAX_EDGE_PX
    # Aspect ratio preserved, not squashed to a square.
    assert out.size == (up.MAX_EDGE_PX, up.MAX_EDGE_PX // 4)


def test_exif_orientation_is_applied(tmp_path, monkeypatch):
    """A phone stores the sensor's raw frame plus a rotation flag. Re-encoding
    drops the flag, so without an explicit transpose every portrait photo is
    served on its side — which reads to the user as a failed upload."""
    from PIL import Image

    monkeypatch.chdir(tmp_path)

    # Orientation 6 means "rotate 90° clockwise for display".
    exif = Image.Exif()
    exif[0x0112] = 6
    buf = io.BytesIO()
    Image.new("RGB", (40, 10), (10, 20, 30)).save(buf, format="JPEG", exif=exif)

    f = _FakeUpload("portrait.jpg", buf.getvalue())
    _, key = up.save_upload(f, "proofs")

    subdir, _, filename = key.partition("/")
    out = Image.open(storage.local_path(subdir, filename))
    # 40x10 rotated for display is 10x40.
    assert out.size == (10, 40)


def test_metadata_is_stripped_on_re_encode(tmp_path, monkeypatch):
    """These are photographs taken by minors. Whatever the camera attached —
    GPS coordinates above all — must not be handed to everyone who can open
    the proof."""
    from PIL import Image

    monkeypatch.chdir(tmp_path)

    exif = Image.Exif()
    exif[0x010F] = "SecretCameraMake"
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), (1, 2, 3)).save(buf, format="JPEG", exif=exif)

    f = _FakeUpload("geotagged.jpg", buf.getvalue())
    _, key = up.save_upload(f, "proofs")

    subdir, _, filename = key.partition("/")
    stored = storage.local_path(subdir, filename).read_bytes()
    assert b"SecretCameraMake" not in stored
    assert not Image.open(io.BytesIO(stored)).getexif()


def test_corrupt_image_is_a_400_without_leaking_decoder_internals():
    # Correct PNG magic, then garbage: passes the cheap checks, fails to decode.
    f = _FakeUpload("broken.png", PNG_MAGIC + b"\xde\xad\xbe\xef" * 8)
    with pytest.raises(HTTPException) as exc:
        up.save_upload(f, "proofs")
    assert exc.value.status_code == 400
    # The user gets an actionable sentence, not a Pillow traceback fragment.
    assert "could not be read as an image" in exc.value.detail
    assert "PIL" not in exc.value.detail


def test_decompression_bomb_is_refused(tmp_path, monkeypatch):
    """A small file that decodes to an enormous raster is well under the byte
    cap on the wire and still exhausts memory. The pixel ceiling catches it."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(up, "MAX_IMAGE_PIXELS", 64)

    f = _FakeUpload("bomb.png", _png_bytes((100, 100)))
    with pytest.raises(HTTPException) as exc:
        up.save_upload(f, "proofs")
    assert exc.value.status_code == 413


def test_heic_is_accepted_when_the_decoder_is_present(tmp_path, monkeypatch):
    """iPhone photos are the common case for a proof, so this is the path that
    matters most in practice."""
    pytest.importorskip("pillow_heif")
    from PIL import Image

    monkeypatch.chdir(tmp_path)

    import pillow_heif

    pillow_heif.register_heif_opener()
    buf = io.BytesIO()
    Image.new("RGB", (12, 12), (9, 9, 9)).save(buf, format="HEIF")

    f = _FakeUpload("IMG_0001.heic", buf.getvalue())
    public_url, key = up.save_upload(f, "proofs")

    assert public_url.endswith(".webp")
    subdir, _, filename = key.partition("/")
    assert Image.open(storage.local_path(subdir, filename)).size == (12, 12)


def test_heic_is_refused_clearly_when_the_decoder_is_missing(monkeypatch):
    """A host provisioned without pillow-heif must say so, not 500."""
    monkeypatch.setattr(up, "_heif_state", False)
    f = _FakeUpload("IMG_0002.heic", b"\x00\x00\x00\x18ftypheic" + b"\x00" * 32)
    with pytest.raises(HTTPException) as exc:
        up.save_upload(f, "proofs")
    assert exc.value.status_code == 415
    assert "HEIC" in exc.value.detail


def test_storage_failure_becomes_a_503_not_an_opaque_500(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def boom(*args, **kwargs):
        raise OSError("No space left on device")

    monkeypatch.setattr(up.storage, "put", boom)

    f = _FakeUpload("photo.png", _png_bytes())
    with pytest.raises(HTTPException) as exc:
        up.save_upload(f, "proofs")
    assert exc.value.status_code == 503
    assert "No space left" not in exc.value.detail
