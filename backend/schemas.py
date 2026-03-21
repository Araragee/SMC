from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel


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


class SessionBase(BaseModel):
    teacher_id: int
    student_id: int
    start_time: datetime
    end_time: datetime
    proof_image_url: Optional[str] = None
    homework_assigned: Optional[str] = None

class SessionCreate(SessionBase):
    pass

class Session(SessionBase):
    id: int
    model_config = {"from_attributes": True}


class UserBase(BaseModel):
    email: str
    name: str
    role_id: int

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool
    role: Optional[Role] = None
    model_config = {"from_attributes": True}
