"""Notification abstraction. Swap ConsoleNotifier for EmailNotifier in prod by
setting env NOTIFIER_TYPE=email and providing SMTP_* env vars.

All methods are best-effort: failures must NOT raise into the request path —
log and swallow so transactional writes (e.g. payment recorded) are not
rolled back by a flaky mail server.
"""
from __future__ import annotations

import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Protocol

logger = logging.getLogger(__name__)


class Notifier(Protocol):
    def send_welcome(self, user, temp_password: str) -> None: ...
    def send_password_reset(self, user, token: str) -> None: ...
    def send_email_verification(self, user, token: str) -> None: ...
    def send_session_reminder(self, user, session) -> None: ...
    def send_session_confirmed(self, user, session) -> None: ...
    def send_proof_rejected(self, user, session, reason: str) -> None: ...
    def send_payment_receipt(self, user, payment) -> None: ...


class ConsoleNotifier:
    """Default dev notifier: logs the message instead of sending."""

    def _log(self, kind: str, to: str, body: str) -> None:
        logger.info("[NOTIFY/%s -> %s] %s", kind, to, body)
        print(f"[NOTIFY/{kind} -> {to}] {body}")

    def send_welcome(self, user, temp_password):
        self._log("welcome", user.email,
                  f"Welcome {user.name}. Temp password: {temp_password}. Change on first login.")

    def send_password_reset(self, user, token):
        self._log("reset", user.email,
                  f"Reset link: /reset-password?token={token} (expires in 30m)")

    def send_email_verification(self, user, token):
        self._log("verify", user.email,
                  f"Verify link: /verify-email?token={token}")

    def send_session_reminder(self, user, session):
        when = getattr(session, "start_time", "?")
        self._log("reminder", user.email,
                  f"Session reminder: {when}. Session id={session.id}")

    def send_session_confirmed(self, user, session):
        when = getattr(session, "start_time", "?")
        self._log("confirmed", user.email,
                  f"Session confirmed for {when}. Session id={session.id}")

    def send_proof_rejected(self, user, session, reason):
        self._log("proof_rejected", user.email,
                  f"Your proof for session {session.id} was rejected: {reason}. Please re-upload.")

    def send_payment_receipt(self, user, payment):
        self._log("receipt", user.email,
                  f"Payment received: {payment.amount} via {payment.method} on {payment.date}.")


class EmailNotifier:
    """SMTP-backed notifier. Wire SMTP_* env vars before enabling.

    Required env: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM.
    Set NOTIFIER_TYPE=email in backend/.env to activate.

    Port 465  → implicit TLS (SMTP_SSL).
    Port 587  → STARTTLS (default, works with Gmail, SendGrid, Mailgun, etc.)
    Port 25   → plain SMTP (no encryption — dev/LAN use only).
    """

    def __init__(self) -> None:
        from ..config import settings  # lazy import avoids circular at module load
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.user = settings.SMTP_USER
        self.password = settings.SMTP_PASSWORD
        self.from_addr = settings.SMTP_FROM

    def _send(self, to: str, subject: str, body: str) -> None:
        """Send a plain-text email. Failures are logged but never re-raised."""
        if not self.host:
            logger.warning(
                "EmailNotifier: SMTP_HOST not set — skipping send to %s (%s)", to, subject
            )
            return

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.from_addr
        msg["To"] = to
        msg.attach(MIMEText(body, "plain", "utf-8"))

        try:
            if self.port == 465:
                # Implicit TLS
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(self.host, self.port, context=context) as server:
                    if self.user and self.password:
                        server.login(self.user, self.password)
                    server.sendmail(self.from_addr, [to], msg.as_string())
            else:
                # STARTTLS (587) or plain (25)
                with smtplib.SMTP(self.host, self.port) as server:
                    server.ehlo()
                    if self.port == 587:
                        context = ssl.create_default_context()
                        server.starttls(context=context)
                        server.ehlo()
                    if self.user and self.password:
                        server.login(self.user, self.password)
                    server.sendmail(self.from_addr, [to], msg.as_string())
            logger.info("EmailNotifier: sent '%s' to %s", subject, to)
        except Exception as exc:  # noqa: BLE001
            logger.error("EmailNotifier: failed to send to %s: %s", to, exc)

    def send_welcome(self, user, temp_password):
        self._send(user.email, "Welcome to SMC",
                   f"Hi {user.name}, your temporary password is: {temp_password}")

    def send_password_reset(self, user, token):
        self._send(user.email, "Reset your SMC password",
                   f"Use this token to reset: {token} (valid 30 min).")

    def send_email_verification(self, user, token):
        self._send(user.email, "Verify your SMC email",
                   f"Click to verify: /verify-email?token={token}")

    def send_session_reminder(self, user, session):
        self._send(user.email, "Upcoming SMC session",
                   f"Reminder: session id {session.id} at {session.start_time}.")

    def send_session_confirmed(self, user, session):
        self._send(user.email, "SMC session confirmed",
                   f"Your session at {session.start_time} is confirmed.")

    def send_proof_rejected(self, user, session, reason):
        self._send(user.email, "Session proof rejected",
                   f"Your proof for session {session.id} was rejected: {reason}.")

    def send_payment_receipt(self, user, payment):
        self._send(user.email, "Payment received",
                   f"We've recorded a payment of {payment.amount} via {payment.method}.")


_singleton: Notifier | None = None


def get_notifier() -> Notifier:
    global _singleton
    if _singleton is None:
        from ..config import settings
        _singleton = EmailNotifier() if settings.NOTIFIER_TYPE.lower() == "email" else ConsoleNotifier()
    return _singleton


def safe_notify(method: str, *args, **kwargs) -> None:
    """Call a notifier method by name, swallowing all errors. Use this in
    request handlers so a notifier glitch never aborts the user's action."""
    try:
        fn = getattr(get_notifier(), method, None)
        if fn:
            fn(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001
        logger.exception("notifier.%s failed: %s", method, exc)
