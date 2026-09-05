import asyncio
import os
import logging
import uuid
import traceback
from contextlib import asynccontextmanager

import jwt
from fastapi import FastAPI, Request, Response, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import text

from . import models

# Load .env from the backend directory
from .config import settings
from .database import SessionLocal
from .routers import activity, auth, messaging, notifications, payments, push, sessions, shop, uploads, users
from .routers.sessions import session_checker_task

# Setup logger
logger = logging.getLogger(__name__)

# Rate limiter shared with routers (e.g. login endpoint).
limiter = Limiter(key_func=get_remote_address)

# NOTE: Table creation is managed by Alembic migrations.
# Run `alembic upgrade head` before starting the app.
# Do NOT call models.Base.metadata.create_all() here — it bypasses Alembic versioning.


def _seed_defaults() -> None:
    """Seed required roles, instruments, and a default admin on first boot."""
    db = SessionLocal()
    try:
        for role_name in ["admin", "teacher", "student"]:
            if not db.query(models.Role).filter(models.Role.name == role_name).first():
                db.add(models.Role(name=role_name))
        db.commit()

        for instrument_name in ["Guitar", "Bass", "Voice", "Drum", "Flute", "Violin", "Keyboard", "Ukulele"]:
            if not db.query(models.Instrument).filter(models.Instrument.name == instrument_name).first():
                db.add(models.Instrument(name=instrument_name))
        db.commit()

        admin_role = db.query(models.Role).filter(models.Role.name == "admin").first()
        admin_user = db.query(models.User).filter(
            (models.User.email == settings.DEFAULT_ADMIN_EMAIL) |
            (models.User.username == settings.DEFAULT_ADMIN_USERNAME)
        ).first()
        if not admin_user and admin_role:
            from .dependencies import pwd_context
            hashed_password = pwd_context.hash(settings.DEFAULT_ADMIN_PASSWORD)
            db.add(models.User(
                email=settings.DEFAULT_ADMIN_EMAIL,
                username=settings.DEFAULT_ADMIN_USERNAME,
                name="System Admin",
                hashed_password=hashed_password,
                role_id=admin_role.id,
                is_active=True,
                # Force the operator to rotate the .env default on first login.
                # Frontend redirects to /change-password whenever this flag is set.
                must_change_password=True,
            ))
            db.commit()
            logger.info(f"Default admin user created: {settings.DEFAULT_ADMIN_USERNAME} / [see DEFAULT_ADMIN_PASSWORD in .env]")
        elif admin_user and not admin_user.username:
            admin_user.username = settings.DEFAULT_ADMIN_USERNAME
            db.commit()
    finally:
        db.close()


def _purge_stale_tokens() -> None:
    """Delete expired and revoked auth tokens to prevent unbounded table growth."""
    import datetime
    db = SessionLocal()
    try:
        now = datetime.datetime.now(datetime.UTC)
        deleted_refresh = (
            db.query(models.RefreshToken)
            .filter(
                (models.RefreshToken.revoked.is_(True))
                | (models.RefreshToken.expires_at < now)
            )
            .delete(synchronize_session=False)
        )
        deleted_reset = (
            db.query(models.PasswordResetToken)
            .filter(models.PasswordResetToken.expires_at < now)
            .delete(synchronize_session=False)
        )
        db.commit()
        if deleted_refresh or deleted_reset:
            logger.info(f"Token purge: removed {deleted_refresh} refresh token(s), {deleted_reset} reset token(s).")
        else:
            logger.info("Token purge completed: nothing to remove.")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: seed DB on startup, clean up on shutdown."""
    _seed_defaults()
    _purge_stale_tokens()
    checker = asyncio.create_task(session_checker_task())
    yield
    checker.cancel()
    try:
        await checker
    except asyncio.CancelledError:
        pass

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = str(uuid.uuid4())
    logger.error(
        f"Unhandled exception occurred. Request ID: {request_id} | "
        f"Path: {request.url.path} | Method: {request.method} | "
        f"Detail: {exc}",
        exc_info=exc
    )
    if settings.DEBUG:
        return JSONResponse(
            status_code=500,
            content={
                "detail": f"Internal server error (Request ID: {request_id})",
                "exception": str(exc),
                "traceback": traceback.format_exc(),
            }
        )
    else:
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )


from .utils import storage  # noqa: E402  (needs settings imported above)

# With object storage there is no local tree to create or mount; the uploads
# router serves every file, including the public shop images.
# Public assets only — shop product images are non-sensitive and benefit from
# StaticFiles' efficient streaming. Sensitive subdirectories (``proofs``,
# ``homework``) are served by the auth-gated router below, which requires both
# a valid HMAC-signed URL and an authenticated admin/participant. See
# backend/routers/uploads.py and backend/utils/signed_urls.py for the contract.
if not storage.is_remote():
    os.makedirs(settings.UPLOADS_DIR, exist_ok=True)
    _shop_dir = os.path.join(settings.UPLOADS_DIR, "shop")
    os.makedirs(_shop_dir, exist_ok=True)
    app.mount("/uploads/shop", StaticFiles(directory=_shop_dir), name="uploads_shop")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach a baseline set of security headers to every response.

    These don't replace a real reverse-proxy / CDN config but they're the
    minimum we should ship from the app itself so a misconfigured proxy
    doesn't leave us completely exposed:

      * X-Content-Type-Options: blocks MIME sniffing (defense against
        the browser interpreting an uploaded PNG as JS).
      * X-Frame-Options: forbids embedding in an iframe (clickjacking).
      * Referrer-Policy: stops the browser from leaking the full app URL
        (which can include session IDs in query strings) to third parties.
      * Strict-Transport-Security: when running behind HTTPS, instruct the
        browser to refuse plaintext. Only emit it if the request actually
        came in over TLS — otherwise modern browsers warn.
      * Content-Security-Policy: a conservative starter policy. ``unsafe-inline``
        is kept on style/script because the SPA still ships inline styles
        from Vue's runtime; tighten as the front-end is hardened.
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        # Every API response is either a token, someone's personal data, or a
        # schedule that changes under you. None of it may sit in a browser or
        # intermediary cache. Static uploads set their own policy and are left
        # alone so images stay cacheable.
        if not request.url.path.startswith("/uploads"):
            response.headers.setdefault("Cache-Control", "no-store")
        if request.url.scheme == "https":
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "img-src 'self' data: blob:; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "script-src 'self'; "
            "connect-src 'self' ws: wss:; "
            "frame-ancestors 'none'",
        )
        return response


class MaintenanceModeMiddleware(BaseHTTPMiddleware):
    """Return 503 for everyone except admins while MAINTENANCE_MODE is on.

    We never read the request body here: doing so drains the ASGI stream and
    leaves the real route handler with an empty body (a known BaseHTTPMiddleware
    footgun). Instead we let the auth endpoints through unconditionally — a
    non-admin can obtain a token, but every *other* route is still blocked by
    the Bearer-header admin check below, so nothing useful leaks. Admin identity
    is read only from the JWT in the Authorization header (no DB write, no body).
    """

    # Open during maintenance: health probe + the endpoints an admin needs to
    # authenticate. Token-issuing is harmless because non-admin tokens still
    # fail _is_admin on every protected route.
    _ALLOWED_PATHS = {"/health", "/login", "/auth/refresh", "/auth/logout"}

    async def dispatch(self, request: Request, call_next):
        if not settings.MAINTENANCE_MODE:
            return await call_next(request)
        if request.url.path in self._ALLOWED_PATHS or self._is_admin(request):
            return await call_next(request)
        return JSONResponse(
            status_code=503,
            content={"detail": "Service under maintenance. Please try again later."},
        )

    @staticmethod
    def _is_admin(request: Request) -> bool:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return False
        token = auth_header.split(" ", 1)[1]
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        except jwt.InvalidTokenError:
            return False
        username = payload.get("sub")
        if not username:
            return False
        db = SessionLocal()
        try:
            user = db.query(models.User).filter(
                (models.User.username == username) | (models.User.email == username)
            ).first()
            return bool(user and user.role and user.role.name.lower() == "admin")
        finally:
            db.close()


# Middleware runs outermost-first (last added = outermost). CORS is added LAST
# so it wraps everything: early 503s from MaintenanceModeMiddleware and 500s
# from the exception handler still come back with CORS headers, otherwise the
# browser would mask them as opaque CORS failures on cross-origin calls.
app.add_middleware(MaintenanceModeMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# Include routers
app.include_router(users.router)
app.include_router(sessions.router)
app.include_router(notifications.router)
app.include_router(messaging.router)
app.include_router(payments.router, prefix="/payments", tags=["payments"])
app.include_router(shop.router, prefix="/shop", tags=["shop"])
app.include_router(activity.router, prefix="/activity-log", tags=["activity"])
app.include_router(auth.router)
app.include_router(push.router)
app.include_router(uploads.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Music School API"}

@app.get("/health")
def health_check():
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Database health check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed"
        )
    finally:
        db.close()
