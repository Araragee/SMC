from datetime import datetime
from typing import Annotated, Any, List, Literal

from pydantic import BaseModel, Field, computed_field, field_validator


class RoleBase(BaseModel):
    name: str

class RoleCreate(RoleBase):
    pass

class Role(RoleBase):
    id: int
    model_config = {"from_attributes": True}

class InstrumentBase(BaseModel):
    name: str

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
    message: str
    is_read: bool = False
    link: str | None = None

class NotificationCreate(NotificationBase):
    user_id: int

class Notification(NotificationBase):
    id: int
    user_id: int
    link: str | None = None
    created_at: datetime
    model_config = {"from_attributes": True}


class HomeworkBase(BaseModel):
    description: str
    is_completed: bool = False
    file_url: str | None = None

class HomeworkCreate(HomeworkBase):
    pass

class Homework(HomeworkBase):
    id: int
    session_id: int
    created_at: datetime
    model_config = {"from_attributes": True}

class SessionProofBase(BaseModel):
    image_url: str

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
    status: str = "completed"
    notes: str | None = None

class PaymentCreate(PaymentBase):
    pass

class Payment(PaymentBase):
    id: int
    date: datetime
    student_name: str | None = None
    model_config = {"from_attributes": True}

class SessionBase(BaseModel):
    teacher_id: int
    student_id: int
    start_time: datetime
    end_time: datetime
    status: str = "scheduled"
    proposed_by: int | None = None
    notes: str | None = None
    instrument_id: int | None = None
    is_manual_entry: bool = False
    session_number: int | None = None
    notified_24h: bool = False
    notified_12h: bool = False
    proof_justification: str | None = None
    rejection_reason: str | None = None
    is_force_completed: bool = False
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
    notes: str | None = None
    instrument_id: int | None = None

# Used by admin to edit a session
class SessionEdit(BaseModel):
    teacher_id: int | None = None
    student_id: int | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    notes: str | None = None
    instrument_id: int | None = None
    is_manual_entry: bool | None = None
    session_number: int | None = None
    version: int | None = None  # optimistic lock; reject with 409 if stale

# Used for approve/reject actions with optional reason
class SessionApproval(BaseModel):
    notes: str | None = None
    version: int | None = None  # optimistic lock; reject with 409 if stale

class SessionRequestApproval(BaseModel):
    justification: str | None = None
    version: int | None = None

class SessionRejectProof(BaseModel):
    reason: str
    version: int | None = None

# Used for counter-proposals
class SessionCounter(BaseModel):
    start_time: datetime
    end_time: datetime
    notes: str | None = None
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
    body:            str
    created_at:      datetime
    is_deleted:      bool
    sender_name:     str | None = None
    model_config = {"from_attributes": True}

class ParticipantOut(BaseModel):
    user_id:      int
    joined_at:    datetime
    last_read_at: datetime | None = None
    name:         str | None = None
    model_config = {"from_attributes": True}

class ConversationOut(BaseModel):
    id:           int
    type:         str
    name:         str | None = None
    created_at:   datetime
    participants: list[ParticipantOut] = []
    last_message: MessageOut | None = None
    unread_count: int = 0
    model_config = {"from_attributes": True}

class CreateDMRequest(BaseModel):
    other_user_id: int

class CreateGroupRequest(BaseModel):
    name:            str
    participant_ids: list[int]

class AddParticipantRequest(BaseModel):
    user_id: int

class CreateMessageRequest(BaseModel):
    body: str

class MessageCursorPage(BaseModel):
    messages:    list[MessageOut]
    next_cursor: int | None = None

# ──────────────────────────────────────────────────────────────────────────────


class UserBase(BaseModel):
    email: str
    name: str
    role_id: int
    avatar_url: str | None = None
    sessions_left: int | None = 0
    username: str | None = None
    contact_number: str | None = None
    home_address: str | None = None

    # Student specific
    birthday: str | None = None
    age: int | None = None
    school: str | None = None
    parent_name: str | None = None
    parent_contact: str | None = None
    sessions_enrolled: int | None = None

class UserCreate(UserBase):
    password: str | None = None
    instrument_ids: list[int] | None = None

class UserUpdate(BaseModel):
    email: str | None = None
    name: str | None = None
    avatar_url: str | None = None
    password: str | None = None
    username: str | None = None
    contact_number: str | None = None
    home_address: str | None = None
    birthday: str | None = None
    age: int | None = None
    school: str | None = None
    parent_name: str | None = None
    parent_contact: str | None = None
    sessions_enrolled: int | None = None
    sessions_left: int | None = None
    instrument_ids: list[int] | None = None

class User(UserBase):
    id: int
    is_active: bool
    email_verified: bool = False
    totp_enabled: bool = False
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
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
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
    password: str
    code: Annotated[str, Field(min_length=6, max_length=10)]


class TwoFAVerifyRequest(BaseModel):
    challenge_token: str
    code: Annotated[str, Field(min_length=6, max_length=10)]


class SimpleOK(BaseModel):
    ok: bool = True
    detail: str | None = None


# ── Recurring lesson series ──────────────────────────────────────────────────

class RecurringSessionCreate(BaseModel):
    """Bulk-create a recurring lesson series."""
    teacher_id: int
    student_id: int
    start_time: datetime
    end_time: datetime
    cadence: Literal["weekly", "biweekly", "monthly"] = "weekly"
    occurrences: Annotated[int, Field(ge=2, le=52)] = 4
    notes: str | None = None
    instrument_id: int | None = None
    skip_dates: List[datetime] = []


class RecurringSessionResult(BaseModel):
    created_count: int
    skipped_count: int
    session_ids: List[int]


# ── Push notification subscription ───────────────────────────────────────────

class PushSubscriptionIn(BaseModel):
    endpoint: str
    keys_p256dh: str
    keys_auth: str
    user_agent: str | None = None


# ── Shop Schemas ──────────────────────────────────────────────────────────────

class InstrumentProductBase(BaseModel):
    name: str
    description: str | None = None
    price_cents: int
    stock: int
    image_url: str | None = None
    category_id: int | None = None
    is_active: bool = True

class InstrumentProductCreate(InstrumentProductBase):
    pass

class InstrumentProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price_cents: int | None = None
    stock: int | None = None
    image_url: str | None = None
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
    quantity: int

class OrderItemCreate(OrderItemBase):
    pass

class OrderItem(OrderItemBase):
    id: int
    price_cents_at_purchase: int
    product: InstrumentProduct | None = None
    model_config = {"from_attributes": True}

class OrderBase(BaseModel):
    notes: str | None = None

class OrderCreate(OrderBase):
    items: list[OrderItemCreate]

class OrderStatusUpdate(BaseModel):
    status: str
    rejection_reason: str | None = None

class Order(OrderBase):
    id: int
    user_id: int
    status: str
    total_cents: int
    approved_by: int | None = None
    approved_at: datetime | None = None
    rejection_reason: str | None = None
    created_at: datetime
    updated_at: datetime
    user: User | None = None
    items: list[OrderItem] = []
    model_config = {"from_attributes": True}

# ── Activity Log ──────────────────────────────────────────────────────────────

class ActivityLogEntry(BaseModel):
    id: int
    action_type: str
    actor_id: int | None = None
    actor_name: str | None = None
    target_type: str | None = None
    target_id: int | None = None
    description: str
    created_at: datetime
    model_config = {"from_attributes": True}
