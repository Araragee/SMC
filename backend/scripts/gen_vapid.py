"""Generate a VAPID key pair for Web Push.

Usage:
    python -m backend.scripts.gen_vapid

Copy the printed VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY into backend/.env.
"""
from __future__ import annotations

import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def main() -> None:
    private_key = ec.generate_private_key(ec.SECP256R1())
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_numbers = private_key.public_key().public_numbers()
    x = public_numbers.x.to_bytes(32, "big")
    y = public_numbers.y.to_bytes(32, "big")
    public_b64 = _b64url(b"\x04" + x + y)
    private_b64 = _b64url(private_key.private_numbers().private_value.to_bytes(32, "big"))

    print("VAPID_PUBLIC_KEY=" + public_b64)
    print("VAPID_PRIVATE_KEY=" + private_b64)
    print("# Or use the PEM directly with pywebpush:")
    print(private_pem.decode().rstrip())


if __name__ == "__main__":
    main()
