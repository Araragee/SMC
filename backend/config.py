import os

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # CORS
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

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
