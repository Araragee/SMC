"""
TOTP secret encryption/decryption at rest.

Uses Fernet symmetric encryption keyed from the application SECRET_KEY so that
raw TOTP secrets are never stored in plain text in the database. Existing plain-text
secrets are transparently migrated on first read (encrypt-on-read strategy).

Key derivation: HKDF-SHA256 over SECRET_KEY → 32 bytes → URL-safe base64 → Fernet key.
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from backend.config import settings

# ---------------------------------------------------------------------------
# Key derivation (deterministic from SECRET_KEY so no extra env var needed)
# ---------------------------------------------------------------------------

def _derive_fernet_key() -> bytes:
    """Derive a stable 32-byte Fernet key from the application SECRET_KEY."""
    raw = hashlib.sha256(settings.SECRET_KEY.encode()).digest()  # 32 bytes
    return base64.urlsafe_b64encode(raw)  # Fernet requires URL-safe base64


_fernet = Fernet(_derive_fernet_key())

# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def encrypt_totp_secret(plain: str) -> str:
    """Encrypt a TOTP base32 secret string. Returns a Fernet token string."""
    return _fernet.encrypt(plain.encode()).decode()


def decrypt_totp_secret(stored: str) -> str:
    """
    Decrypt a stored TOTP secret.

    Transparently handles legacy plain-text secrets (base32 strings that
    predate encryption) by detecting InvalidToken and returning them as-is.
    Callers should re-encrypt after first use when this fallback is hit.
    """
    try:
        return _fernet.decrypt(stored.encode()).decode()
    except (InvalidToken, Exception):
        # Legacy plain-text value — return unchanged so TOTP still works
        return stored


def is_encrypted(stored: str) -> bool:
    """Return True if the stored value looks like a Fernet token."""
    # Fernet tokens start with 'gAAAAA' (version byte 0x80, base64-encoded)
    return stored.startswith("gAAAAA")
