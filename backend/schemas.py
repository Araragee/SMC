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


class NotificationBase(BaseModel):
    message: str
    is_read: bool = False

class NotificationCreate(NotificationBase):
    user_id: int

class Notification(NotificationBase):
    id: int
    user_id: int
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

class SessionCreate(SessionBase):
    pass

class Session(SessionBase):
    id: int
    homeworks: List[Homework] = []
    proofs: List[SessionProof] = []
    proof_image_url: Optional[str] = None
    homework_assigned: Optional[str] = None
    homework_completed: bool = False

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


class UserBase(BaseModel):
    email: str
    name: str
    role_id: int
    avatar_url: Optional[str] = None
    sessions_left: Optional[int] = 0

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool
    role: Optional[Role] = None
    model_config = {"from_attributes": True}
