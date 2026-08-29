import json
import os
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Music School API"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30
    EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS: int = 24
    TWO_FA_CHALLENGE_EXPIRE_MINUTES: int = 5
    TOTP_ISSUER: str = "SMC Music School"

    # Minimum length for user-chosen passwords (change-password / reset-password).
    # NIST SP 800-63B treats length as the primary strength lever; 8 is the
    # documented floor. Override in .env to tighten without touching code.
    PASSWORD_MIN_LENGTH: int = 8

    # Default admin credentials (override in .env — never leave as defaults in production)
    DEFAULT_ADMIN_PASSWORD: str = "changeme_on_first_boot"
    DEFAULT_ADMIN_EMAIL: str = "admin@smc.edu"
    DEFAULT_ADMIN_USERNAME: str = "admin"

    # Database
    DATABASE_URL: str | None = None

    # Web Push (VAPID). Generate via scripts/gen_vapid.py.
    VAPID_PUBLIC_KEY: str = ""
    VAPID_PRIVATE_KEY: str = ""
    VAPID_SUBJECT: str = "mailto:admin@smc.edu"

    # Notifier backend: console | email
    NOTIFIER_TYPE: str = "console"

    # SMTP (required when NOTIFIER_TYPE=email)
    # Port 465 → implicit TLS; 587 → STARTTLS (recommended); 25 → plain
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@smc.local"

    # Debug mode — enables diagnostic endpoints; never True in production
    DEBUG: bool = False

    # Session checker tuning — can be overridden in .env without touching code
    STALE_THRESHOLD_HOURS: int = 48        # Hours before a pending_verification session is considered stale
    REMINDER_COOLDOWN_HOURS: int = 24      # Minimum hours between repeat stale-proof reminders
    LOW_STOCK_THRESHOLD: int = 5           # Shop stock level that triggers a low-stock notification
    CANCEL_CUTOFF_HOURS: int = 24          # Hours before start_time that a participant can cancel
    COUNTER_PROPOSAL_CAP: int = 3          # Maximum counter proposals allowed before admin mediation
    WORKING_HOURS_START: int = 8           # Start of school working hours (inclusive hour, e.g. 8 = 08:00)
    WORKING_HOURS_END: int = 22             # End of school working hours (exclusive hour, e.g. 22 = 22:00)
    SCHOOL_TIMEZONE: str = "Asia/Manila"   # Timezone for validating school working hours
    MAINTENANCE_MODE: bool = False




    # Where uploaded files land. Relative paths resolve against the process
    # CWD; point this at a mounted volume (e.g. /data/uploads) in any
    # deployment whose filesystem is ephemeral or replicated.
    UPLOADS_DIR: str = "uploads"

    # Object storage for uploads. When all three are set, files go to a private
    # Supabase Storage bucket instead of local disk — required on hosts with an
    # ephemeral filesystem (Render free tier) or more than one replica.
    # SUPABASE_SERVICE_KEY bypasses row-level security: server-side only.
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_BUCKET: str = ""

    # CORS. NoDecode turns off pydantic-settings' automatic JSON parsing so the
    # validator below sees the raw string: without it a value that is not valid
    # JSON raises SettingsError at import and the process dies before it can
    # serve anything — a misformatted origin list took the whole API down
    # rather than just refusing that origin.
    ALLOWED_ORIGINS: Annotated[list[str], NoDecode] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def _parse_allowed_origins(cls, value: object) -> list[str]:
        """Accept a JSON list, a comma-separated list, or a single origin.

        Dashboard env fields are free text and every hosting UI encourages a
        different shape, so all three are treated as valid. Trailing slashes are
        stripped because a browser's Origin header never carries one and the
        comparison is exact.
        """
        if value is None or isinstance(value, list):
            return [str(v).strip().rstrip("/") for v in (value or [])]
        text = str(value).strip()
        if not text:
            return []
        if text.startswith("["):
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                # Tolerate single quotes and stray smart quotes from a paste.
                cleaned = (
                    text.replace("\u201c", '"').replace("\u201d", '"').replace("'", '"')
                )
                parsed = json.loads(cleaned)
            return [str(v).strip().rstrip("/") for v in parsed]
        return [part.strip().rstrip("/") for part in text.split(",") if part.strip()]

    # Refresh-token cookie (Phase 2).
    # The refresh token used to live in localStorage on the frontend — any XSS
    # equalled full account takeover. It now lives in an HttpOnly + SameSite
    # cookie. In dev (HTTP) Secure must be False or browsers drop the cookie.
    # Production should set REFRESH_COOKIE_SECURE=true and serve over HTTPS.
    REFRESH_COOKIE_NAME: str = "smc_rt"
    REFRESH_COOKIE_PATH: str = "/auth"           # only sent to /auth/* endpoints
    REFRESH_COOKIE_SECURE: bool = False          # set to True behind HTTPS
    REFRESH_COOKIE_SAMESITE: str = "lax"         # "lax" | "strict" | "none"

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
