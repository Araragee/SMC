import datetime
from datetime import timezone

from sqlalchemy import Boolean, Column, ForeignKey, Index, Integer, String
from sqlalchemy import DateTime as _NaiveDateTime

# All timestamp columns use timezone-aware DateTime so that PostgreSQL comparisons
# work correctly (SQLite silently accepts naive datetimes, but Postgres raises
# "can't compare offset-naive and offset-aware datetimes" without this flag).
class DateTime(_NaiveDateTime):  # noqa: N801 — intentional shadow
    def __init__(self, timezone: bool = True, **kw):
        super().__init__(timezone=timezone, **kw)
from sqlalchemy.orm import relationship

from .database import Base


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True) # Admin, Teacher, Student

    users = relationship("User", back_populates="role")



class Instrument(Base):
    __tablename__ = "instruments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)

class UserInstrument(Base):
    __tablename__ = "user_instruments"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True, index=True)
    instrument_id = Column(Integer, ForeignKey("instruments.id"), primary_key=True, index=True)

class TeacherStudent(Base):
    __tablename__ = "teacher_students"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), index=True)
    student_id = Column(Integer, ForeignKey("users.id"), index=True)
    assigned_at = Column(DateTime, default=lambda: datetime.datetime.now(timezone.utc))

    teacher = relationship("User", foreign_keys=[teacher_id], back_populates="students_assigned")
    student = relationship("User", foreign_keys=[student_id], back_populates="teachers_assigned")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    role_id = Column(Integer, ForeignKey("roles.id"), index=True)
    avatar_url = Column(String, nullable=True)
    sessions_left = Column(Integer, default=0, nullable=True)
    username = Column(String, unique=True, index=True, nullable=True)
    contact_number = Column(String, nullable=True)
    home_address = Column(String, nullable=True)

    # Student specific
    birthday = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
    school = Column(String, nullable=True)
    parent_name = Column(String, nullable=True)
    parent_contact = Column(String, nullable=True)
    sessions_enrolled = Column(Integer, nullable=True)

    # Auth hardening: brute-force lockout tracking.
    # MIGRATION NOTE: run `alembic revision --autogenerate -m "add login lockout fields"`
    # then `alembic upgrade head` to create the failed_login_count / locked_until columns.
    failed_login_count = Column(Integer, default=0, nullable=False, server_default="0")
    locked_until = Column(DateTime, nullable=True)

    # Email verification (added by auth-overhaul migration).
    email_verified = Column(Boolean, default=False, nullable=False, server_default="0")
    email_verification_token_hash = Column(String, nullable=True)

    # TOTP-based 2FA (added by auth-overhaul migration).
    # Secrets are stored Fernet-encrypted (see backend/utils/totp_crypt.py).
    # Legacy plain-text rows are migrated transparently on first read/write.
    totp_secret = Column(String, nullable=True)
    totp_enabled = Column(Boolean, default=False, nullable=False, server_default="0")

    # Phase 2: force-change-password gate. Set true on the default-admin
    # seed and after any admin-initiated password reset so the user can't
    # operate the app until they rotate the credential. The frontend
    # redirects to /change-password whenever ``user.must_change_password``
    # is true.
    must_change_password = Column(Boolean, default=False, nullable=False, server_default="0")

    instruments = relationship("Instrument", secondary="user_instruments")
    teachers_assigned = relationship("TeacherStudent", foreign_keys="TeacherStudent.student_id", back_populates="student")
    students_assigned = relationship("TeacherStudent", foreign_keys="TeacherStudent.teacher_id", back_populates="teacher")


    role = relationship("Role", back_populates="users")

    # Using string names for relationship targets to avoid circular import issues if separated later
    sessions_as_teacher = relationship("Session", foreign_keys="Session.teacher_id", back_populates="teacher")
    sessions_as_student = relationship("Session", foreign_keys="Session.student_id", back_populates="student")
    notifications = relationship("Notification", back_populates="user")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), index=True)
    student_id = Column(Integer, ForeignKey("users.id"), index=True)
    start_time = Column(DateTime, index=True)
    end_time = Column(DateTime)
    # status: pending_teacher | pending_admin | scheduled | completed | cancelled | rejected | overdue
    status = Column(String, default="scheduled", index=True)
    proposed_by = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    notes = Column(String, nullable=True)
    instrument_id = Column(Integer, ForeignKey("instruments.id"), nullable=True, index=True)
    is_manual_entry = Column(Boolean, default=False)
    session_number = Column(Integer, nullable=True)
    notified_24h = Column(Boolean, default=False)
    notified_12h = Column(Boolean, default=False)
    # Timestamp of the last stale-state reminder sent for pending_verification / overdue_rejected.
    # NULL means no reminder has been sent yet. Reset to NULL on every status change.
    stale_reminded_at = Column(DateTime, nullable=True)
    proof_justification = Column(String, nullable=True)
    rejection_reason = Column(String, nullable=True)
    is_force_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.datetime.now(timezone.utc),
        onupdate=lambda: datetime.datetime.now(timezone.utc),
    )

    # Optimistic locking: bumped on every status transition; clients send
    # this back and the server rejects with 409 if it has been incremented
    # by a concurrent request. SQLAlchemy auto-manages via version_id_col.
    counter_count = Column(Integer, default=0, server_default="0")
    version = Column(Integer, nullable=False, default=0, server_default="0")

    __mapper_args__ = {
        "version_id_col": version,
        "version_id_generator": False,  # we bump manually so we can detect mismatches
    }

    instrument = relationship("Instrument")


    teacher = relationship("User", foreign_keys=[teacher_id], back_populates="sessions_as_teacher")
    student = relationship("User", foreign_keys=[student_id], back_populates="sessions_as_student")
    proposer = relationship("User", foreign_keys=[proposed_by])

    homeworks = relationship("Homework", back_populates="session", cascade="all, delete-orphan")
    proofs = relationship("SessionProof", back_populates="session", cascade="all, delete-orphan")

    __table_args__ = (
        # Covers the session_checker_task's overdue query, which filters
        # WHERE status = 'scheduled' AND end_time < now every loop tick.
        Index("ix_sessions_status_end_time", "status", "end_time"),
    )


class Enrollment(Base):
    __tablename__ = "enrollments"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), index=True)
    sessions_purchased = Column(Integer, default=0)
    sessions_used = Column(Integer, default=0)
    is_active = Column(Boolean, default=True, server_default="1")
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(timezone.utc))

    student = relationship("User", foreign_keys=[student_id])
    teacher = relationship("User", foreign_keys=[teacher_id])

class Homework(Base):
    __tablename__ = "homework"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), index=True)
    description = Column(String)
    is_completed = Column(Boolean, default=False)
    file_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(timezone.utc))

    session = relationship("Session", back_populates="homeworks")

class SessionProof(Base):
    __tablename__ = "session_proofs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), index=True)
    image_url = Column(String)
    uploaded_at = Column(DateTime, default=lambda: datetime.datetime.now(timezone.utc))
    uploader_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    uploader_role = Column(String, nullable=True)

    session = relationship("Session", back_populates="proofs")
    uploader = relationship("User", foreign_keys=[uploader_id])

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), index=True)
    amount = Column(Integer) # In cents or smallest currency unit
    date = Column(DateTime, default=lambda: datetime.datetime.now(timezone.utc))
    method = Column(String) # cash | bank_transfer | card
    status = Column(String, default="completed") # pending | completed | failed
    notes = Column(String, nullable=True)

    student = relationship("User", foreign_keys=[student_id])

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    message = Column(String)
    link = Column(String, nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(timezone.utc))

    user = relationship("User", back_populates="notifications")

    __table_args__ = (
        # Covers the common "unread count" query: WHERE user_id = ? AND is_read = false
        Index("ix_notifications_user_unread", "user_id", "is_read"),
        # Supports the 90-day retention purge planned in Phase 4 and
        # date-range filtering in the notifications UI.
        Index("ix_notifications_created_at", "created_at"),
    )

class InstrumentProduct(Base):
    __tablename__ = "instrument_products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(String, nullable=True)
    price_cents = Column(Integer, nullable=False, default=0)
    stock = Column(Integer, nullable=False, default=0)
    image_url = Column(String, nullable=True)
    category_id = Column(Integer, ForeignKey("instruments.id"), nullable=True, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.datetime.now(timezone.utc),
                        onupdate=lambda: datetime.datetime.now(timezone.utc))

    category = relationship("Instrument")

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String, nullable=False, default="pending", index=True)
    # pending | approved | fulfilled | rejected | cancelled
    notes = Column(String, nullable=True)
    total_cents = Column(Integer, nullable=False, default=0)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime, default=lambda: datetime.datetime.now(timezone.utc),
                        onupdate=lambda: datetime.datetime.now(timezone.utc))

    user = relationship("User", foreign_keys=[user_id])
    approver = relationship("User", foreign_keys=[approved_by])
    items = relationship("OrderItem", back_populates="order",
                         cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("instrument_products.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=1)
    price_cents_at_purchase = Column(Integer, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("InstrumentProduct")

# ── Messaging ──────────────────────────────────────────────────────────────────

from sqlalchemy import UniqueConstraint


class Conversation(Base):
    __tablename__ = "conversations"

    id         = Column(Integer, primary_key=True, index=True)
    type       = Column(String, nullable=False, default="dm")  # "dm" | "group" | "session_thread"
    name       = Column(String, nullable=True)                  # for groups / session thread label
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(timezone.utc))

    participants   = relationship("ConversationParticipant", back_populates="conversation", cascade="all, delete-orphan")
    messages       = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")
    session_thread = relationship("SessionThread", back_populates="conversation", uselist=False)


class ConversationParticipant(Base):
    __tablename__ = "conversation_participants"
    __table_args__ = (
        UniqueConstraint("conversation_id", "user_id", name="uq_conv_participant"),
    )

    id              = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, index=True)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    joined_at       = Column(DateTime, default=lambda: datetime.datetime.now(timezone.utc))
    last_read_at    = Column(DateTime, nullable=True)

    conversation = relationship("Conversation", back_populates="participants")
    user         = relationship("User")


class Message(Base):
    __tablename__ = "messages"

    id              = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, index=True)
    sender_id       = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    body            = Column(String, nullable=False)
    created_at      = Column(DateTime, default=lambda: datetime.datetime.now(timezone.utc), index=True)
    is_deleted      = Column(Boolean, default=False)

    conversation = relationship("Conversation", back_populates="messages")
    sender       = relationship("User")


class SessionThread(Base):
    """One-to-one link between a Session and its Conversation thread."""
    __tablename__ = "session_threads"

    id              = Column(Integer, primary_key=True, index=True)
    session_id      = Column(Integer, ForeignKey("sessions.id"), unique=True, nullable=False)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), unique=True, nullable=False)

    session      = relationship("Session")
    conversation = relationship("Conversation", back_populates="session_thread")


class ActivityLog(Base):
    """Admin-facing audit trail of key system events."""
    __tablename__ = "activity_logs"

    id          = Column(Integer, primary_key=True, index=True)
    action_type = Column(String, nullable=False, index=True)   # e.g. 'session_completed'
    actor_id    = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    actor_name  = Column(String, nullable=True)                # snapshot at time of action
    target_type = Column(String, nullable=True)                # 'session' | 'payment' | 'user' …
    target_id   = Column(Integer, nullable=True)
    description = Column(String, nullable=False)
    created_at  = Column(DateTime, default=lambda: datetime.datetime.now(timezone.utc), index=True)

    actor = relationship("User", foreign_keys=[actor_id])


# ── Auth: refresh tokens, password reset ──────────────────────────────────────

class RefreshToken(Base):
    """Persisted refresh tokens (rotated on each use). We store only the sha256
    of the raw token so a DB leak does not expose live credentials."""
    __tablename__ = "refresh_tokens"

    id           = Column(Integer, primary_key=True, index=True)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash   = Column(String, nullable=False, unique=True, index=True)
    expires_at   = Column(DateTime, nullable=False)
    revoked      = Column(Boolean, nullable=False, default=False, server_default="0")
    created_at   = Column(DateTime, default=lambda: datetime.datetime.now(timezone.utc), nullable=False)
    last_used_at = Column(DateTime, nullable=True)

    user = relationship("User", foreign_keys=[user_id])


class PasswordResetToken(Base):
    """One-time password reset tokens. token_hash = sha256(raw)."""
    __tablename__ = "password_reset_tokens"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String, nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    used_at    = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(timezone.utc), nullable=False)

    user = relationship("User", foreign_keys=[user_id])


class PushSubscription(Base):
    """Web Push subscription registered by a client."""
    __tablename__ = "push_subscriptions"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    endpoint    = Column(String, nullable=False, unique=True, index=True)
    keys_p256dh = Column(String, nullable=False)
    keys_auth   = Column(String, nullable=False)
    user_agent  = Column(String, nullable=True)
    created_at  = Column(DateTime, default=lambda: datetime.datetime.now(timezone.utc), nullable=False)

    user = relationship("User", foreign_keys=[user_id])
