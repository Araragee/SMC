"""Validate, normalize and persist an uploaded file.

Every path here is reachable by any authenticated user with a phone, so the
module is written defensively. In order, an upload must survive:

1. **An extension on the allowlist.** The extension — not the client-declared
   ``Content-Type`` — decides, because the latter is attacker-controlled and
   browsers get it wrong anyway (Safari sends an empty type for HEIC).
2. **A magic-byte check** matching that extension, so a ``.png`` that is really
   a script is refused before anything opens it.
3. **A hard size cap, enforced while reading.** The body is consumed in chunks
   and abandoned the moment it crosses the cap; an oversized upload is never
   fully resident in memory.
4. **A real decode.** Pillow re-encodes every image to WebP. That normalizes
   the zoo of phone formats to one the browser reliably renders, drops any
   embedded metadata (EXIF GPS included — these are photographs of minors), and
   means the bytes we serve were produced by our encoder rather than forwarded
   from an untrusted source.

The stored filename is ``token_hex(16).<ext>``: no component of it comes from
user input, so path traversal is not merely blocked but unrepresentable.
"""
from __future__ import annotations

import io
import logging
import secrets
from collections.abc import Iterable
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from . import storage

logger = logging.getLogger(__name__)

MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

# Read granularity for the size-capped read below. Large enough that a 10 MB
# upload is ~16 syscalls, small enough that the overshoot past the cap before
# we notice is negligible.
_CHUNK_BYTES = 64 * 1024

# HEIC/HEIF are what an iPhone produces with the default camera setting, which
# on a school app means most proofs. Accepting them is the difference between a
# working upload and a student concluding the feature is broken.
DEFAULT_ALLOWED_EXTS = {"jpg", "jpeg", "png", "webp", "heic", "heif"}

# Ceiling on decoded pixels, independent of the byte cap. A "decompression
# bomb" is a small file that expands enormously once decoded — well under
# MAX_SIZE_BYTES on the wire, gigabytes in RAM. 50 MP is comfortably above any
# phone camera (a 48 MP sensor shoots 8000x6000) and far below dangerous.
MAX_IMAGE_PIXELS = 50_000_000

# Longest edge of a stored image. Proofs are viewed in a modal on a phone; a
# 4000px original costs bandwidth and decode time on every render for detail
# nobody sees.
MAX_EDGE_PX = 2000

# WebP quality. 82 is the usual knee of the quality/size curve — visually
# indistinguishable from the original at this size, roughly a third of the bytes.
_WEBP_QUALITY = 82

# Magic-byte signatures keyed by normalized extension, as (offset, marker).
# HEIC/HEIF carry their brand in the ISO-BMFF ``ftyp`` box at offset 4; the
# brand itself varies by device ("heic", "heix", "mif1", "msf1"), so we check
# the box marker and let the decoder rule on the rest.
_MAGIC_SIGNATURES: dict[str, list[tuple[int, bytes]]] = {
    "jpg":  [(0, b"\xff\xd8\xff")],
    "jpeg": [(0, b"\xff\xd8\xff")],
    "png":  [(0, b"\x89PNG\r\n\x1a\n")],
    "webp": [(0, b"RIFF"), (8, b"WEBP")],
    "heic": [(4, b"ftyp")],
    "heif": [(4, b"ftyp")],
    "pdf":  [(0, b"%PDF-")],
}

# Bytes needed to check the longest signature above, with headroom.
_MAGIC_PEEK_BYTES = 32

_RASTER_EXTS = {"jpg", "jpeg", "png", "webp", "heic", "heif"}


def _matches_magic(head: bytes, ext: str) -> bool:
    sig = _MAGIC_SIGNATURES.get(ext)
    if not sig:
        return False
    return all(head[offset:offset + len(marker)] == marker for offset, marker in sig)


def _read_capped(file: UploadFile, max_bytes: int) -> bytes:
    """Read the whole body, or raise 413 as soon as it exceeds ``max_bytes``.

    The previous implementation read to EOF and *then* compared lengths, so a
    body of any size was fully buffered before being refused — a free memory
    exhaustion lever for any authenticated account. Stopping at the cap costs
    one extra chunk of overshoot and closes it.
    """
    buf = bytearray()
    while True:
        chunk = file.file.read(_CHUNK_BYTES)
        if not chunk:
            return bytes(buf)
        buf.extend(chunk)
        if len(buf) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum allowed size is {max_bytes // (1024 * 1024)} MB.",
            )


def _register_heif() -> None:
    """Teach Pillow to open HEIC/HEIF, once, if the plugin is installed.

    ``pillow-heif`` is a declared dependency, but it carries native codecs and
    is the most likely thing to be missing from a partially-provisioned host.
    A failure here must degrade to "HEIC is not accepted" rather than taking
    down every upload, so the import is guarded and logged loudly.
    """
    global _heif_state
    if _heif_state is not None:
        return
    try:
        import pillow_heif

        pillow_heif.register_heif_opener()
        _heif_state = True
    except Exception:
        logger.exception(
            "pillow-heif is unavailable; HEIC/HEIF uploads will be rejected. "
            "Install it (see backend/requirements.txt) to accept iPhone photos."
        )
        _heif_state = False


_heif_state: bool | None = None


def _normalize_image(contents: bytes, ext: str) -> bytes:
    """Decode, correct orientation, bound the size, and re-encode to WebP.

    Returns the encoded bytes. Raises 400 for input Pillow cannot make sense
    of — which at this point means genuinely corrupt data, since the extension
    and magic bytes already agreed.
    """
    from PIL import Image, ImageOps, UnidentifiedImageError

    if ext in {"heic", "heif"}:
        _register_heif()
        if not _heif_state:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="HEIC photos are not supported on this server. Re-save the photo as JPEG and try again.",
            )

    # Pillow's own bomb guard warns at ~89 MP and only raises at twice that.
    # Setting our own ceiling makes the limit explicit and much lower.
    previous_limit = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
    try:
        try:
            img = Image.open(io.BytesIO(contents))
            img.load()
        except Image.DecompressionBombError as err:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="That image's dimensions are too large to process.",
            ) from err
        except (UnidentifiedImageError, OSError, ValueError) as err:
            # Deliberately does not echo the decoder's message: it names
            # internal plugins and offsets, which is noise to the user and
            # detail to anyone probing the parser.
            logger.info("Rejected undecodable %s upload: %s", ext, err)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="That file could not be read as an image. It may be corrupt — try uploading it again.",
            ) from err

        # Phone cameras store the sensor's raw orientation and a rotation flag
        # rather than rotating pixels. Re-encoding discards the flag, so
        # without this every photo taken in portrait is served on its side —
        # which reads as a broken upload and invites a re-upload.
        img = ImageOps.exif_transpose(img) or img

        # WebP cannot encode a palette ("P") or a 16-bit ("I") image, and an
        # alpha channel on a photograph is meaningless weight. Flatten onto
        # white so transparent PNGs do not become black rectangles.
        if img.mode in ("RGBA", "LA", "PA"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.convert("RGBA").split()[-1])
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")

        width, height = img.size
        longest = max(width, height)
        if longest > MAX_EDGE_PX:
            scale = MAX_EDGE_PX / longest
            img = img.resize(
                (max(1, round(width * scale)), max(1, round(height * scale))),
                Image.Resampling.LANCZOS,
            )

        out = io.BytesIO()
        # No `exif=` and no `icc_profile=`: everything the camera attached,
        # location included, is dropped here rather than served to every
        # participant who can open the proof.
        img.save(out, format="WEBP", quality=_WEBP_QUALITY, method=4)
        return out.getvalue()
    finally:
        Image.MAX_IMAGE_PIXELS = previous_limit


def save_upload(
    file: UploadFile,
    subdir: str,
    allowed_exts: Iterable[str] = DEFAULT_ALLOWED_EXTS,
) -> tuple[str, str]:
    """Validate and persist an UploadFile under ``<subdir>/``.

    Returns ``(public_url, storage_key)``. The key is ``<subdir>/<filename>``;
    where that physically lives is the storage layer's business.

    Raises ``HTTPException`` with a status the client can branch on: 415 for a
    format we do not take, 413 for something too big, 400 for a file whose
    contents contradict its name.
    """
    allowed = {e.lower() for e in allowed_exts}

    ext = Path(file.filename or "").suffix.lower().lstrip(".")
    if ext not in allowed:
        readable = ", ".join(sorted(allowed))
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type. Accepted formats: {readable}.",
        )

    # Peek the header without losing the rest of the stream.
    head = file.file.read(_MAGIC_PEEK_BYTES)
    file.file.seek(0)
    if not _matches_magic(head, ext):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File contents do not match declared type",
        )

    contents = _read_capped(file, MAX_SIZE_BYTES)
    if not contents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The uploaded file is empty")

    if ext in _RASTER_EXTS:
        contents = _normalize_image(contents, ext)
        # Every raster input leaves as WebP, whatever it arrived as.
        ext = "webp"
        content_type = "image/webp"
    else:
        content_type = "application/pdf"

    safe_name = f"{secrets.token_hex(16)}.{ext}"
    try:
        key = storage.put(subdir, safe_name, contents, content_type=content_type)
    except HTTPException:
        raise
    except Exception as err:
        # Disk full, bucket unreachable, credentials rotated. The user can act
        # on "try again"; the operator needs the traceback, so log it here
        # rather than letting it surface as an opaque 500.
        logger.exception("Failed to store upload in %s", subdir)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not save the file right now. Please try again in a moment.",
        ) from err

    public_url = f"/uploads/{subdir}/{safe_name}"
    return public_url, key
