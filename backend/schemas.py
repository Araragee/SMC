from datetime import datetime
from typing import Annotated, Any, List, Literal

from pydantic import BaseModel, Field, computed_field, field_validator

# ── String length caps ───────────────────────────────────────────────────────
# Centralized so the values are auditable and adjustable in one place.
# Applied with Annotated[str, Field(max_length=N)] on user-facing string fields
# to prevent unbounded payloads from reaching the DB or breaking the UI.
NAME_LEN          = 100
SHORT_NOTE_LEN    = 500    # rejection reasons, payment notes
NOTE_LEN          = 2000   # session/homework notes, product descriptions
LONG_NOTE_LEN     = 4000   # message body, free-form long inputs
URL_LEN           = 500
EMAIL_LEN         = 254    # RFC 5321
USERNAME_LEN      = 64
PHONE_LEN         = 32
ADDRESS_LEN       = 200
DATE_STR_LEN      = 32
TOKEN_LEN         = 256
LONG_TOKEN_LEN    = 512    # JWT challenge tokens can be ~400-500 chars

# Convenience aliases used throughout.
NameStr           = Annotated[str, Field(min_length=1, max_length=NAME_LEN)]
OptName           = Annotated[str | None, Field(default=None, max_length=NAME_LEN)]
OptShortNote      = Annotated[str | None, Field(default=None, max_length=SHORT_NOTE_LEN)]
OptNote           = Annotated[str | None, Field(default=None, max_length=NOTE_LEN)]
OptLongNote       = Annotated[str | None, Field(default=None, max_length=LONG_NOTE_LEN)]
OptUrl            = Annotated[str | None, Field(default=None, max_length=URL_LEN)]
OptPhone          = Annotated[str | None, Field(default=None, max_length=PHONE_LEN)]
OptAddress        = Annotated[str | None, Field(default=None, max_length=ADDRESS_LEN)]
OptDateStr        = Annotated[str | None, Field(default=None, max_length=DATE_STR_LEN)]
EmailStr          = Annotated[str, Field(min_length=3, max_length=EMAIL_LEN)]
UsernameStr       = Annotated[str, Field(min_length=1, max_length=USERNAME_LEN)]


class RoleBase(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=NAME_LEN)]

class RoleCreate(RoleBase):
    pass

class Role(RoleBase):
    id: int
    model_config = {"from_attributes": True}

class InstrumentBase(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=NAME_LEN)]

class InstrumentCreate(InstrumentBase):
    pass

class Instrument(InstrumentBase):
    id: int
    model_config = {"from_attributes": True}

class TeacherStudentBase(BaseModel):
    teacher_id: int
    student_id: int

class TeacherStudentCreate(TeacherStudentBase):
    pass

class TeacherStudent(TeacherStudentBase):
    id: int
    assigned_at: datetime
    model_config = {"from_attributes": True}

class NotificationBase(BaseModel):
    message: Annotated[str, Field(min_length=1, max_length=NOTE_LEN)]
    is_read: bool = False
    link: OptUrl = None

class NotificationCreate(NotificationBase):
    user_id: int

class Notification(NotificationBase):
    id: int
    user_id: int
    link: OptUrl = None
    created_at: datetime
    model_config = {"from_attributes": True}


class HomeworkBase(BaseModel):
    description: Annotated[str, Field(min_length=1, max_length=NOTE_LEN)]
    is_completed: bool = False
    file_url: OptUrl = None

class HomeworkCreate(HomeworkBase):
    pass

class Homework(HomeworkBase):
    id: int
    session_id: int
    created_at: datetime
    model_config = {"from_attributes": True}

class SessionProofBase(BaseModel):
    image_url: Annotated[str, Field(min_length=1, max_length=URL_LEN)]

class SessionProofCreate(SessionProofBase):
    pass

class SessionProof(SessionProofBase):
    id: int
    session_id: int
    uploaded_at: datetime
    uploader_id: int | None = None
    uploader_role: str | None = None
    model_config = {"from_attributes": True}

PaymentMethod = Literal["cash", "bank_transfer", "card", "gcash", "maya"]

class PaymentBase(BaseModel):
    student_id: int
    amount: int = Field(gt=0, lt=10_000_000)
    method: PaymentMethod
    status: Annotated[str, Field(default="completed", max_length=32)] = "completed"
    notes: OptShortNote = None

class PaymentCreate(PaymentBase):
    pass

class Payment(PaymentBase):
    id: int
    date: datetime
    student_name: OptName = None
    model_config = {"from_attributes": True}

class SessionBase(BaseModel):
    teacher_id: int
    student_id: int
    start_time: datetime
    end_time: datetime
    status: Annotated[str, Field(default="scheduled", max_length=32)] = "scheduled"
    proposed_by: int | None = None
    notes: OptNote = None
    instrument_id: int | None = None
    is_manual_entry: bool = False
    session_number: int | None = None
    notified_24h: bool = False
    notified_12h: bool = False
    proof_justification: OptNote = None
    rejection_reason: OptShortNote = None
    is_force_completed: bool = False
    counter_count: int = 0
    version: int = 0

    @field_validator('is_manual_entry', 'notified_24h', 'notified_12h', 'is_force_completed', mode='before')
    @classmethod
    def convert_null_to_false(cls, v: Any) -> bool:
        if v is None:
            return False
        return bool(v)

class SessionCreate(SessionBase):
    pass

# Used by teacher/student to propose a session
class SessionPropose(BaseModel):
    teacher_id: int
    student_id: int
    start_time: datetime
    end_time: datetime | None = None  # defaults to start_time + 1h if omitted
    notes: OptNote = None
    instrument_id: int | None = None

# Used by admin to edit a session
class SessionEdit(BaseModel):
    teacher_id: int | None = None
    student_id: int | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    notes: OptNote = None
    instrument_id: int | None = None
    is_manual_entry: bool | None = None
    session_number: int | None = None
    version: int | None = None  # optimistic lock; reject with 409 if stale

# Used for approve/reject actions with optional reason
class SessionApproval(BaseModel):
    notes: OptShortNote = None
    version: int | None = None  # optimistic lock; reject with 409 if stale

class SessionRequestApproval(BaseModel):
    justification: OptNote = None
    version: int | None = None

class SessionRejectProof(BaseModel):
    reason: Annotated[str, Field(min_length=1, max_length=SHORT_NOTE_LEN)]
    version: int | None = None

# Used for counter-proposals
class SessionCounter(BaseModel):
    start_time: datetime
    end_time: datetime
    notes: OptNote = None
    version: int | None = None

class Session(SessionBase):
    id: int
    homeworks: list[Homework] = []
    proofs: list[SessionProof] = []
    proof_image_url: str | None = None
    homework_assigned: str | None = None
    homework_completed: bool = False
    instrument: Instrument | None = None

    model_config = {"from_attributes": True}


class EnrollmentBase(BaseModel):
    student_id: int
    teacher_id: int
    sessions_purchased: int = 0
    sessions_used: int = 0

class EnrollmentCreate(EnrollmentBase):
    pass

class Enrollment(EnrollmentBase):
    id: int
    created_at: datetime

    @computed_field
    def sessions_left(self) -> int:
        return self.sessions_purchased - self.sessions_used
    model_config = {"from_attributes": True}


# ── Messaging Schemas ──────────────────────────────────────────────────────────

class MessageOut(BaseModel):
    id:              int
    conversation_id: int
    sender_id:       int
    body:            Annotated[str, Field(max_length=LONG_NOTE_LEN)]
    created_at:      datetime
    is_deleted:      bool
    sender_name:     OptName = None
    model_config = {"from_attributes": True}

class ParticipantOut(BaseModel):
    user_id:      int
    joined_at:    datetime
    last_read_at: datetime | None = None
    name:         OptName = None
    model_config = {"from_attributes": True}

class ConversationOut(BaseModel):
    id:           int
    type:         Annotated[str, Field(max_length=32)]
    name:         OptName = None
    created_at:   datetime
    participants: list[ParticipantOut] = []
    last_message: MessageOut | None = None
    unread_count: int = 0
    model_config = {"from_attributes": True}

class CreateDMRequest(BaseModel):
    other_user_id: int

class CreateGroupRequest(BaseModel):
    name:            NameStr
    participant_ids: Annotated[list[int], Field(min_length=1, max_length=100)]

class AddParticipantRequest(BaseModel):
    user_id: int

class CreateMessageRequest(BaseModel):
    body: Annotated[str, Field(min_length=1, max_length=LONG_NOTE_LEN)]

class MessageCursorPage(BaseModel):
    messages:    list[MessageOut]
    next_cursor: int | None = None

# ──────────────────────────────────────────────────────────────────────────────


class UserBase(BaseModel):
    email: EmailStr
    name: NameStr
    role_id: int
    avatar_url: OptUrl = None
    sessions_left: int | None = 0
    username: Annotated[str | None, Field(default=None, max_length=USERNAME_LEN)] = None
    contact_number: OptPhone = None
    home_address: OptAddress = None

    # Student specific
    birthday: OptDateStr = None
    age: Annotated[int | None, Field(default=None, ge=0, le=150)] = None
    school: OptName = None
    parent_name: OptName = None
    parent_contact: OptPhone = None
    sessions_enrolled: Annotated[int | None, Field(default=None, ge=0, le=10_000)] = None

class UserCreate(UserBase):
    password: Annotated[str | None, Field(default=None, min_length=8, max_length=128)] = None
    instrument_ids: Annotated[list[int] | None, Field(default=None, max_length=50)] = None

class UserUpdate(BaseModel):
    email: Annotated[str | None, Field(default=None, max_length=EMAIL_LEN)] = None
    name: OptName = None
    avatar_url: OptUrl = None
    password: Annotated[str | None, Field(default=None, min_length=8, max_length=128)] = None
    username: Annotated[str | None, Field(default=None, max_length=USERNAME_LEN)] = None
    contact_number: OptPhone = None
    home_address: OptAddress = None
    birthday: OptDateStr = None
    age: Annotated[int | None, Field(default=None, ge=0, le=150)] = None
    school: OptName = None
    parent_name: OptName = None
    parent_contact: OptPhone = None
    sessions_enrolled: Annotated[int | None, Field(default=None, ge=0, le=10_000)] = None
    sessions_left: Annotated[int | None, Field(default=None, ge=0, le=10_000)] = None
    instrument_ids: Annotated[list[int] | None, Field(default=None, max_length=50)] = None

class User(UserBase):
    id: int
    is_active: bool
    email_verified: bool = False
    totp_enabled: bool = False
    # Phase 2: frontend redirects to /change-password whenever this is true.
    must_change_password: bool = False
    role: Role | None = None
    instruments: list[Instrument] = []
    model_config = {"from_attributes": True}


# ── Auth schemas (refresh, password reset, email verify, 2FA) ─────────────────

# Password rule: min 8, at least 1 letter + 1 digit.
def _validate_password_strength(v: str) -> str:
    if len(v) < 8:
        raise ValueError("Password must be at least 8 characters")
    if not any(c.isalpha() for c in v):
        raise ValueError("Password must contain at least one letter")
    if not any(c.isdigit() for c in v):
        raise ValueError("Password must contain at least one digit")
    return v


StrongPassword = Annotated[str, Field(min_length=8, max_length=128)]


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: User


class LoginChallenge(BaseModel):
    """Returned when user has 2FA enabled — frontend must then POST /auth/2fa/verify."""
    requires_2fa: bool = True
    challenge_token: str


class RefreshRequest(BaseModel):
    # Optional because Phase 2 introduced the HttpOnly refresh cookie:
    # browser clients can leave this null and let the server read from
    # the cookie. Non-browser clients (mobile, tests, curl) still pass it
    # in the body.
    refresh_token: Annotated[str | None, Field(default=None, max_length=TOKEN_LEN)] = None


class LogoutRequest(BaseModel):
    # Optional for the same reason as RefreshRequest. A logout with no
    # token still clears the cookie and returns 200, so a stale tab can
    # always reach a clean signed-out state.
    refresh_token: Annotated[str | None, Field(default=None, max_length=TOKEN_LEN)] = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: Annotated[str, Field(min_length=1, max_length=TOKEN_LEN)]
    new_password: StrongPassword

    @field_validator("new_password")
    @classmethod
    def _strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class ChangePasswordRequest(BaseModel):
    """Self-service password change for an authenticated user.

    Used by the /change-password flow that ``must_change_password`` users
    are forced into, but also available as a normal "update my password"
    action for anyone signed in.
    """
    current_password: Annotated[str, Field(min_length=1, max_length=128)]
    new_password: StrongPassword

    @field_validator("new_password")
    @classmethod
    def _strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class TwoFASetupResponse(BaseModel):
    secret: str
    provisioning_uri: str
    qr_code_png_base64: str


class TwoFAEnableRequest(BaseModel):
    code: Annotated[str, Field(min_length=6, max_length=10)]


class TwoFADisableRequest(BaseModel):
    password: Annotated[str, Field(min_length=1, max_length=128)]
    code: Annotated[str, Field(min_length=6, max_length=10)]


class TwoFAVerifyRequest(BaseModel):
    challenge_token: Annotated[str, Field(min_length=1, max_length=LONG_TOKEN_LEN)]
    code: Annotated[str, Field(min_length=6, max_length=10)]


class SimpleOK(BaseModel):
    ok: bool = True
    detail: Annotated[str | None, Field(default=None, max_length=SHORT_NOTE_LEN)] = None


# ── Recurring lesson series ──────────────────────────────────────────────────

class RecurringSessionCreate(BaseModel):
    """Bulk-create a recurring lesson series."""
    teacher_id: int
    student_id: int
    start_time: datetime
    end_time: datetime
    cadence: Literal["weekly", "biweekly", "monthly"] = "weekly"
    occurrences: Annotated[int, Field(ge=2, le=52)] = 4
    notes: OptNote = None
    instrument_id: int | None = None
    skip_dates: Annotated[List[datetime], Field(max_length=52)] = []


class RecurringSessionResult(BaseModel):
    created_count: int
    skipped_count: int
    session_ids: List[int]


# ── Push notification subscription ───────────────────────────────────────────

class PushSubscriptionIn(BaseModel):
    endpoint: Annotated[str, Field(min_length=1, max_length=URL_LEN)]
    keys_p256dh: Annotated[str, Field(min_length=1, max_length=TOKEN_LEN)]
    keys_auth: Annotated[str, Field(min_length=1, max_length=TOKEN_LEN)]
    user_agent: Annotated[str | None, Field(default=None, max_length=URL_LEN)] = None


# ── Shop Schemas ──────────────────────────────────────────────────────────────

class InstrumentProductBase(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=NAME_LEN)]
    description: OptNote = None
    price_cents: Annotated[int, Field(ge=0, le=100_000_000)]
    stock: Annotated[int, Field(ge=0, le=1_000_000)]
    image_url: OptUrl = None
    category_id: int | None = None
    is_active: bool = True

class InstrumentProductCreate(InstrumentProductBase):
    pass

class InstrumentProductUpdate(BaseModel):
    name: OptName = None
    description: OptNote = None
    price_cents: Annotated[int | None, Field(default=None, ge=0, le=100_000_000)] = None
    stock: Annotated[int | None, Field(default=None, ge=0, le=1_000_000)] = None
    image_url: OptUrl = None
    category_id: int | None = None
    is_active: bool | None = None

class InstrumentProduct(InstrumentProductBase):
    id: int
    created_at: datetime
    updated_at: datetime
    category: Instrument | None = None
    model_config = {"from_attributes": True}

class OrderItemBase(BaseModel):
    product_id: int
    quantity: Annotated[int, Field(ge=1, le=1000)]

class OrderItemCreate(OrderItemBase):
    pass

class OrderItem(OrderItemBase):
    id: int
    price_cents_at_purchase: int
    product: InstrumentProduct | None = None
    model_config = {"from_attributes": True}

class OrderBase(BaseModel):
    notes: OptNote = None

class OrderCreate(OrderBase):
    items: Annotated[list[OrderItemCreate], Field(min_length=1, max_length=100)]

class OrderStatusUpdate(BaseModel):
    status: Annotated[str, Field(min_length=1, max_length=32)]
    rejection_reason: OptShortNote = None

class Order(OrderBase):
    id: int
    user_id: int
    status: Annotated[str, Field(max_length=32)]
    total_cents: int
    approved_by: int | None = None
    approved_at: datetime | None = None
    rejection_reason: OptShortNote = None
    created_at: datetime
    updated_at: datetime
    user: User | None = None
    items: list[OrderItem] = []
    model_config = {"from_attributes": True}

# ── Activity Log ──────────────────────────────────────────────────────────────

class ActivityLogEntry(BaseModel):
    id: int
    action_type: Annotated[str, Field(max_length=64)]
    actor_id: int | None = None
    actor_name: OptName = None
    target_type: Annotated[str | None, Field(default=None, max_length=64)] = None
    target_id: int | None = None
    description: Annotated[str, Field(max_length=LONG_NOTE_LEN)]
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Bulk Session Action & Stats ───────────────────────────────────────────────

class BulkActionRequest(BaseModel):
    # Cap at 100 to prevent unbounded payloads / runaway DB writes.
    session_ids: Annotated[list[int], Field(min_length=1, max_length=100)]
    action: Literal["approve", "cancel", "complete"]


class SessionStatsResponse(BaseModel):
    total_sessions: int
    scheduled_sessions: int
    completed_sessions: int
    completion_rate: int
    overdue_sessions: int
    pending_sessions: int
    awaiting_admin: int

