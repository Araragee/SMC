"""Auth flows: refresh tokens, password reset, email verification, 2FA (TOTP).

Endpoints:
- POST /auth/refresh           — rotate refresh token, return new access+refresh
- POST /auth/logout            — revoke current refresh token
- POST /auth/forgot-password   — issue reset token (dispatched via notifier; console in dev, SMTP in prod)
- POST /auth/reset-password    — consume reset token, set new password
- POST /auth/send-verification — issue email verify token
- GET  /auth/verify-email      — consume verify token
- POST /auth/2fa/setup         — generate TOTP secret + QR
- POST /auth/2fa/enable        — confirm TOTP code, mark enabled
- POST /auth/2fa/disable       — require password + code
- POST /auth/2fa/verify        — exchange challenge_token + TOTP for token pair
"""
import base64
import hashlib
import io
import secrets
from datetime import UTC, datetime, timedelta

import jwt
import pyotp
import qrcode
from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request, Response
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config import settings
from ..database import get_db
from ..dependencies import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_current_active_user,
    pwd_context,
)
from ..services.notifier import safe_notify
from ..utils.totp_crypt import decrypt_totp_secret, encrypt_totp_secret, is_encrypted
from .activity import log_activity

router = APIRouter(prefix="/auth", tags=["auth"])
_limiter = Limiter(key_func=get_remote_address)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _naive(dt: datetime) -> datetime:
    """Strip tz for SQLite compat (existing schema uses naive UTC)."""
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


def issue_refresh_token(db: Session, user_id: int) -> tuple[str, models.RefreshToken]:
    raw = secrets.token_urlsafe(48)
    rt = models.RefreshToken(
        user_id=user_id,
        token_hash=_hash_token(raw),
        expires_at=_naive(_utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)),
    )
    db.add(rt)
    db.commit()
    db.refresh(rt)
    return raw, rt


def _user_to_schema(user: models.User) -> schemas.User:
    return schemas.User.model_validate(user)


def build_token_pair(db: Session, user: models.User) -> schemas.TokenPair:
    access = create_access_token(
        data={"sub": user.username or user.email, "user_id": user.id},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_raw, _ = issue_refresh_token(db, user.id)
    return schemas.TokenPair(
        access_token=access,
        refresh_token=refresh_raw,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=_user_to_schema(user),
    )


# ── Refresh-token cookie helpers ────────────────────────────────────────────
#
# As of Phase 2 the refresh token also lives in an HttpOnly cookie so an XSS
# in the SPA can't lift it. The token is STILL returned in the response body
# for backward compatibility with non-browser clients (mobile apps, tests,
# anyone running curl). The /auth/refresh and /auth/logout endpoints read
# from the cookie first and fall back to the body — see those handlers for
# the read order.

def _set_refresh_cookie(response: Response, token: str) -> None:
    """Set the HttpOnly + SameSite refresh cookie on ``response``.

    The cookie path is scoped to ``/auth`` so the cookie is only sent to
    refresh/logout requests — it never accompanies an API call to ``/sessions``
    or ``/users``, so it can't leak into application logs.
    """
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        httponly=True,
        secure=settings.REFRESH_COOKIE_SECURE,
        samesite=settings.REFRESH_COOKIE_SAMESITE,
        path=settings.REFRESH_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    """Drop the cookie. We pass the same path the cookie was set with —
    browsers require the path to match to delete."""
    response.delete_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        path=settings.REFRESH_COOKIE_PATH,
    )


def build_token_pair_with_cookie(
    db: Session, user: models.User, response: Response
) -> schemas.TokenPair:
    """Same as ``build_token_pair`` but ALSO attaches the refresh cookie.

    Use this from any endpoint that mints a fresh token pair (login, 2FA
    verify, refresh) so browser clients automatically transition off
    localStorage on the next request.
    """
    pair = build_token_pair(db, user)
    _set_refresh_cookie(response, pair.refresh_token)
    return pair


def revoke_all_user_refresh_tokens(db: Session, user_id: int) -> int:
    """Revoke every active refresh token for a user. Returns count revoked."""
    q = db.query(models.RefreshToken).filter(
        models.RefreshToken.user_id == user_id,
        models.RefreshToken.revoked.is_(False),
    )
    count = q.count()
    q.update({"revoked": True}, synchronize_session=False)
    db.commit()
    return count


# ── Refresh / logout ─────────────────────────────────────────────────────────

def _read_refresh_token(req: schemas.RefreshRequest | schemas.LogoutRequest | None,
                        cookie_token: str | None) -> str:
    """Resolve the refresh token from request body or cookie.

    Body wins if explicitly provided. This preserves backward compatibility
    with non-browser clients (mobile, tests, curl) and keeps the existing
    replay-detection semantics: posting a stale body token still triggers
    the revoke-chain even if the browser also has a fresh cookie.

    The cookie is the modern path for SPAs that have transitioned off
    localStorage — they call /auth/refresh with no body and the server reads
    the HttpOnly cookie. Either way, the same rotation + replay-detection
    code path runs against whichever token was selected.
    """
    body_token = getattr(req, "refresh_token", None) if req is not None else None
    token = body_token or cookie_token
    if not token:
        raise HTTPException(status_code=401, detail="Refresh token required")
    return token


@router.post("/refresh", response_model=schemas.TokenPair)
def refresh(
    response: Response,
    req: schemas.RefreshRequest | None = None,
    db: Session = Depends(get_db),
    cookie_token: str | None = Cookie(default=None, alias=settings.REFRESH_COOKIE_NAME),
):
    raw = _read_refresh_token(req, cookie_token)
    token_hash = _hash_token(raw)
    rt = db.query(models.RefreshToken).filter(
        models.RefreshToken.token_hash == token_hash
    ).first()
    if rt is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # Replay detection: if token was already revoked, attacker may be reusing
    # a stolen rotation chain. Revoke every active refresh token for the user.
    if rt.revoked:
        revoke_all_user_refresh_tokens(db, rt.user_id)
        # Clear any lingering cookie so the browser stops sending the
        # compromised token.
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail="Refresh token reuse detected; all sessions revoked")

    expires_at = rt.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at < _utcnow():
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail="Refresh token expired")

    user = db.query(models.User).filter(models.User.id == rt.user_id).first()
    if user is None or not user.is_active:
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail="User inactive or removed")

    # Rotate: mark old revoked, issue new pair (which sets a fresh cookie).
    rt.revoked = True
    rt.last_used_at = _naive(_utcnow())
    db.commit()
    return build_token_pair_with_cookie(db, user, response)


@router.post("/logout", response_model=schemas.SimpleOK)
def logout(
    response: Response,
    req: schemas.LogoutRequest | None = None,
    db: Session = Depends(get_db),
    cookie_token: str | None = Cookie(default=None, alias=settings.REFRESH_COOKIE_NAME),
):
    # Logout is best-effort: a logout with no token still clears the cookie
    # and returns success, so a tab whose token already expired can still
    # cleanly sign out.
    raw = cookie_token or (getattr(req, "refresh_token", None) if req else None)
    if raw:
        token_hash = _hash_token(raw)
        rt = db.query(models.RefreshToken).filter(
            models.RefreshToken.token_hash == token_hash
        ).first()
        if rt and not rt.revoked:
            rt.revoked = True
            db.commit()
    _clear_refresh_cookie(response)
    return schemas.SimpleOK(detail="logged out")


# ── Password reset ───────────────────────────────────────────────────────────

@router.post("/forgot-password", response_model=schemas.SimpleOK)
@_limiter.limit("5/minute")
def forgot_password(request: Request, req: schemas.ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == req.email).first()
    # Always return 200 to avoid email enumeration.
    if user is None:
        return schemas.SimpleOK(detail="If that email exists, a reset link was sent.")

    raw = secrets.token_urlsafe(32)
    prt = models.PasswordResetToken(
        user_id=user.id,
        token_hash=_hash_token(raw),
        expires_at=_naive(_utcnow() + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)),
    )
    db.add(prt)
    db.commit()

    safe_notify("send_password_reset", user, raw)
    return schemas.SimpleOK(detail="If that email exists, a reset link was sent.")


@router.post("/change-password", response_model=schemas.SimpleOK)
def change_password(
    req: schemas.ChangePasswordRequest,
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Authenticated self-service password change.

    Verifies the caller knows the current password (so a hijacked access
    token alone can't rotate the credential), updates the hash, clears
    ``must_change_password``, and revokes every refresh token for this
    user — including the current one — so other devices are signed out.
    """
    # passlib raises TypeError when hashed_password is None (e.g. a freshly
    # seeded test user) — treat every verify failure mode as a uniform
    # "incorrect password" so callers can't distinguish edge cases.
    valid = False
    try:
        valid = pwd_context.verify(req.current_password[:72], current_user.hashed_password)
    except Exception:
        valid = False
    if not valid:
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if req.new_password == req.current_password:
        raise HTTPException(status_code=400, detail="New password must differ from the current one")

    current_user.hashed_password = pwd_context.hash(req.new_password[:72])
    current_user.must_change_password = False
    revoke_all_user_refresh_tokens(db, current_user.id)
    _clear_refresh_cookie(response)

    log_activity(
        db, action_type="password_changed",
        description=f"Password changed for {current_user.name}",
        actor_id=current_user.id, actor_name=current_user.name,
        target_type="user", target_id=current_user.id,
    )
    db.commit()
    return schemas.SimpleOK(detail="Password updated; please sign in again")


@router.post("/reset-password", response_model=schemas.SimpleOK)
@_limiter.limit("5/minute")
def reset_password(request: Request, req: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    token_hash = _hash_token(req.token)
    prt = db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.token_hash == token_hash
    ).first()
    if prt is None or prt.used_at is not None:
        raise HTTPException(status_code=400, detail="Invalid or already-used token")

    expires_at = prt.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at < _utcnow():
        raise HTTPException(status_code=400, detail="Token expired")

    user = db.query(models.User).filter(models.User.id == prt.user_id).first()
    if user is None:
        raise HTTPException(status_code=400, detail="User not found")

    pwd = req.new_password
    if len(pwd.encode()) > 72:
        raise HTTPException(status_code=400, detail="Password too long (max 72 bytes)")
    user.hashed_password = pwd_context.hash(pwd[:72])
    prt.used_at = _naive(_utcnow())
    # A successful reset counts as the user rotating their credential —
    # clear the force-change flag so they're not immediately re-gated.
    user.must_change_password = False

    # Revoke all refresh tokens after password change.
    revoke_all_user_refresh_tokens(db, user.id)

    log_activity(
        db, action_type="password_reset",
        description=f"Password reset for user {user.name}",
        actor_id=user.id, actor_name=user.name,
        target_type="user", target_id=user.id,
    )
    db.commit()
    return schemas.SimpleOK(detail="Password updated")


# ── Email verification ───────────────────────────────────────────────────────

@router.post("/send-verification", response_model=schemas.SimpleOK)
def send_verification(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    if current_user.email_verified:
        return schemas.SimpleOK(detail="Already verified")
    raw = secrets.token_urlsafe(32)
    current_user.email_verification_token_hash = _hash_token(raw)
    db.commit()
    safe_notify("send_email_verification", current_user, raw)
    return schemas.SimpleOK(detail="Verification email sent")


@router.get("/verify-email", response_model=schemas.SimpleOK)
def verify_email(token: str = Query(...), db: Session = Depends(get_db)):
    h = _hash_token(token)
    user = db.query(models.User).filter(
        models.User.email_verification_token_hash == h
    ).first()
    if user is None:
        raise HTTPException(status_code=400, detail="Invalid token")
    user.email_verified = True
    user.email_verification_token_hash = None
    log_activity(
        db, action_type="email_verified",
        description=f"Email verified for {user.email}",
        actor_id=user.id, actor_name=user.name,
        target_type="user", target_id=user.id,
    )
    db.commit()
    return schemas.SimpleOK(detail="Email verified")


# ── 2FA (TOTP) ───────────────────────────────────────────────────────────────

def _qr_png_base64(uri: str) -> str:
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


@router.post("/2fa/setup", response_model=schemas.TwoFASetupResponse)
def two_fa_setup(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    if current_user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA already enabled")
    secret = pyotp.random_base32()
    current_user.totp_secret = encrypt_totp_secret(secret)
    db.commit()
    uri = pyotp.TOTP(secret).provisioning_uri(
        name=current_user.email,
        issuer_name=settings.TOTP_ISSUER,
    )
    return schemas.TwoFASetupResponse(
        secret=secret,
        provisioning_uri=uri,
        qr_code_png_base64=_qr_png_base64(uri),
    )


@router.post("/2fa/enable", response_model=schemas.SimpleOK)
def two_fa_enable(
    req: schemas.TwoFAEnableRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    if not current_user.totp_secret:
        raise HTTPException(status_code=400, detail="Call /2fa/setup first")
    _plain_enable = decrypt_totp_secret(current_user.totp_secret)
    # Migrate legacy plain-text secret to encrypted form on first enable
    if not is_encrypted(current_user.totp_secret):
        current_user.totp_secret = encrypt_totp_secret(_plain_enable)
    if not pyotp.TOTP(_plain_enable).verify(req.code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid code")
    current_user.totp_enabled = True
    log_activity(
        db, action_type="2fa_enabled",
        description=f"2FA enabled for {current_user.name}",
        actor_id=current_user.id, actor_name=current_user.name,
        target_type="user", target_id=current_user.id,
    )
    db.commit()
    return schemas.SimpleOK(detail="2FA enabled")


@router.post("/2fa/disable", response_model=schemas.SimpleOK)
def two_fa_disable(
    req: schemas.TwoFADisableRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    if not current_user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA not enabled")
    if not pwd_context.verify(req.password[:72], current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid password")
    _plain_disable = decrypt_totp_secret(current_user.totp_secret)
    if not pyotp.TOTP(_plain_disable).verify(req.code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid code")
    current_user.totp_enabled = False
    current_user.totp_secret = None
    log_activity(
        db, action_type="2fa_disabled",
        description=f"2FA disabled for {current_user.name}",
        actor_id=current_user.id, actor_name=current_user.name,
        target_type="user", target_id=current_user.id,
    )
    db.commit()
    return schemas.SimpleOK(detail="2FA disabled")


def issue_2fa_challenge(user_id: int) -> str:
    """Short-lived JWT marking step-1 of 2FA login. Sub = user_id, kind=2fa."""
    payload = {
        "sub": str(user_id),
        "kind": "2fa_challenge",
        "exp": datetime.now(UTC) + timedelta(minutes=settings.TWO_FA_CHALLENGE_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


@router.post("/2fa/verify", response_model=schemas.TokenPair)
@_limiter.limit("5/minute")
def two_fa_verify(
    request: Request,
    req: schemas.TwoFAVerifyRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    try:
        payload = jwt.decode(req.challenge_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid or expired challenge") from None
    if payload.get("kind") != "2fa_challenge":
        raise HTTPException(status_code=401, detail="Wrong token kind")
    try:
        user_id = int(payload.get("sub", ""))
    except ValueError:
        raise HTTPException(status_code=401, detail="Malformed challenge") from None
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None or not user.is_active or not user.totp_enabled or not user.totp_secret:
        raise HTTPException(status_code=401, detail="2FA not enabled for this user")
    _plain_verify = decrypt_totp_secret(user.totp_secret)
    # Migrate legacy plain-text secret to encrypted form on first login
    if not is_encrypted(user.totp_secret):
        user.totp_secret = encrypt_totp_secret(_plain_verify)
        db.commit()
    if not pyotp.TOTP(_plain_verify).verify(req.code, valid_window=1):
        raise HTTPException(status_code=401, detail="Invalid code")
    return build_token_pair_with_cookie(db, user, response)
