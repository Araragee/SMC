"""Secure file upload helpers.

Protects against path traversal and MIME spoofing by:
- Generating cryptographically random filenames (no user input in path).
- Validating magic bytes against the declared extension.
- Enforcing a hard 10 MB size cap.
- Using pathlib for safe path joins.
"""
import secrets
from collections.abc import Iterable
from pathlib import Path

from fastapi import HTTPException, UploadFile

MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
DEFAULT_ALLOWED_EXTS = {"jpg", "jpeg", "png", "webp"}

# Magic-byte signatures keyed by normalized extension.
_MAGIC_SIGNATURES = {
    "jpg":  [(0, b"\xff\xd8\xff")],
    "jpeg": [(0, b"\xff\xd8\xff")],
    "png":  [(0, b"\x89PNG\r\n\x1a\n")],
    "webp": [(0, b"RIFF"), (8, b"WEBP")],
    "pdf":  [(0, b"%PDF-")],
}


def _matches_magic(head: bytes, ext: str) -> bool:
    sig = _MAGIC_SIGNATURES.get(ext)
    if not sig:
        return False
    return all(head[offset:offset + len(marker)] == marker for offset, marker in sig)


def save_upload(
    file: UploadFile,
    subdir: str,
    allowed_exts: Iterable[str] = DEFAULT_ALLOWED_EXTS,
) -> tuple[str, str]:
    """Validate and persist an UploadFile under uploads/<subdir>/.

    Returns (public_url, disk_path) as strings. Raises HTTPException on failure.
    """
    allowed = {e.lower() for e in allowed_exts}

    ext = Path(file.filename or "").suffix.lower().lstrip(".")
    if ext not in allowed:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    # Peek magic bytes without losing the rest of the stream.
    head = file.file.read(16)
    file.file.seek(0)
    if not _matches_magic(head, ext):
        raise HTTPException(status_code=400, detail="File contents do not match declared type")

    contents = file.file.read()
    if len(contents) > MAX_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File too large. Maximum allowed size is 10 MB.")

    if ext in {"jpg", "jpeg", "png", "webp"}:
        import io

        from PIL import Image
        try:
            img = Image.open(io.BytesIO(contents))
            max_edge = 2000
            w, h = img.size
            if w > max_edge or h > max_edge:
                if w > h:
                    new_w = max_edge
                    new_h = int(h * (max_edge / w))
                else:
                    new_h = max_edge
                    new_w = int(w * (max_edge / h))
                img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            out_bytes = io.BytesIO()
            img.save(out_bytes, format="WEBP")
            contents = out_bytes.getvalue()
            ext = "webp"
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid image file: {str(e)}") from e

    safe_name = f"{secrets.token_hex(16)}.{ext}"
    dest = Path("uploads") / subdir / safe_name
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as f:
        f.write(contents)

    public_url = f"/uploads/{subdir}/{safe_name}"
    return public_url, str(dest)
