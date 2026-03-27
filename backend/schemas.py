from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, computed_field


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
    link: Optional[str] = None

class NotificationCreate(NotificationBase):
    user_id: int

class Notification(NotificationBase):
    id: int
    user_id: int
    link: Optional[str] = None
    created_at: datetime
    model_config = {"from_attributes": True}


class HomeworkBase(BaseModel):
    description: str
    is_completed: bool = False

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
    model_config = {"from_attributes": True}

class SessionBase(BaseModel):
    teacher_id: int
    student_id: int
    start_time: datetime
    end_time: datetime
    status: str = "scheduled"
    proposed_by: Optional[int] = None
    notes: Optional[str] = None
    instrument_id: Optional[int] = None
    is_manual_entry: bool = False
    session_number: Optional[int] = None

class SessionCreate(SessionBase):
    pass

# Used by teacher/student to propose a session
class SessionPropose(BaseModel):
    teacher_id: int
    student_id: int
    start_time: datetime
    end_time: datetime
    notes: Optional[str] = None

# Used by admin to edit a session
class SessionEdit(BaseModel):
    teacher_id: Optional[int] = None
    student_id: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    notes: Optional[str] = None
    instrument_id: Optional[int] = None
    is_manual_entry: Optional[bool] = None
    session_number: Optional[int] = None

# Used for approve/reject actions with optional reason
class SessionApproval(BaseModel):
    notes: Optional[str] = None

# Used for counter-proposals
class SessionCounter(BaseModel):
    start_time: datetime
    end_time: datetime
    notes: Optional[str] = None

class Session(SessionBase):
    id: int
    homeworks: List[Homework] = []
    proofs: List[SessionProof] = []
    proof_image_url: Optional[str] = None
    homework_assigned: Optional[str] = None
    homework_completed: bool = False
    instrument: Optional[Instrument] = None

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
    sender_name:     Optional[str] = None
    model_config = {"from_attributes": True}

class ParticipantOut(BaseModel):
    user_id:      int
    joined_at:    datetime
    last_read_at: Optional[datetime] = None
    name:         Optional[str] = None
    model_config = {"from_attributes": True}

class ConversationOut(BaseModel):
    id:           int
    type:         str
    name:         Optional[str] = None
    created_at:   datetime
    participants: List[ParticipantOut] = []
    last_message: Optional[MessageOut] = None
    unread_count: int = 0
    model_config = {"from_attributes": True}

class CreateDMRequest(BaseModel):
    other_user_id: int

class CreateGroupRequest(BaseModel):
    name:            str
    participant_ids: List[int]

class AddParticipantRequest(BaseModel):
    user_id: int

class CreateMessageRequest(BaseModel):
    body: str

class MessageCursorPage(BaseModel):
    messages:    List[MessageOut]
    next_cursor: Optional[int] = None

# ──────────────────────────────────────────────────────────────────────────────


class UserBase(BaseModel):
    email: str
    name: str
    role_id: int
    avatar_url: Optional[str] = None
    sessions_left: Optional[int] = 0
    username: Optional[str] = None
    contact_number: Optional[str] = None
    home_address: Optional[str] = None

    # Student specific
    birthday: Optional[str] = None
    age: Optional[int] = None
    school: Optional[str] = None
    parent_name: Optional[str] = None
    parent_contact: Optional[str] = None
    sessions_enrolled: Optional[int] = None

class UserCreate(UserBase):
    password: Optional[str] = None
    instrument_ids: Optional[List[int]] = None

class UserUpdate(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    password: Optional[str] = None
    username: Optional[str] = None
    contact_number: Optional[str] = None
    home_address: Optional[str] = None
    birthday: Optional[str] = None
    age: Optional[int] = None
    school: Optional[str] = None
    parent_name: Optional[str] = None
    parent_contact: Optional[str] = None
    sessions_enrolled: Optional[int] = None
    sessions_left: Optional[int] = None
    instrument_ids: Optional[List[int]] = None

class User(UserBase):
    id: int
    is_active: bool
    role: Optional[Role] = None
    instruments: List[Instrument] = []
    model_config = {"from_attributes": True}
