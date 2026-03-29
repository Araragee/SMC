from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import relationship
import datetime

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

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    instrument_id = Column(Integer, ForeignKey("instruments.id"), primary_key=True)

class TeacherStudent(Base):
    __tablename__ = "teacher_students"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"))
    student_id = Column(Integer, ForeignKey("users.id"))
    assigned_at = Column(DateTime, default=datetime.datetime.utcnow)

    teacher = relationship("User", foreign_keys=[teacher_id], back_populates="students_assigned")
    student = relationship("User", foreign_keys=[student_id], back_populates="teachers_assigned")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    role_id = Column(Integer, ForeignKey("roles.id"))
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
    teacher_id = Column(Integer, ForeignKey("users.id"))
    student_id = Column(Integer, ForeignKey("users.id"))
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    # status: pending_teacher | pending_admin | scheduled | completed | cancelled | rejected | overdue
    status = Column(String, default="scheduled")
    proposed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(String, nullable=True)
    instrument_id = Column(Integer, ForeignKey("instruments.id"), nullable=True)
    is_manual_entry = Column(Boolean, default=False)
    session_number = Column(Integer, nullable=True)
    notified_24h = Column(Boolean, default=False)
    notified_12h = Column(Boolean, default=False)
    proof_justification = Column(String, nullable=True)
    rejection_reason = Column(String, nullable=True)

    instrument = relationship("Instrument")


    teacher = relationship("User", foreign_keys=[teacher_id], back_populates="sessions_as_teacher")
    student = relationship("User", foreign_keys=[student_id], back_populates="sessions_as_student")
    proposer = relationship("User", foreign_keys=[proposed_by])

    homeworks = relationship("Homework", back_populates="session", cascade="all, delete-orphan")
    proofs = relationship("SessionProof", back_populates="session", cascade="all, delete-orphan")


class Enrollment(Base):
    __tablename__ = "enrollments"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"))
    teacher_id = Column(Integer, ForeignKey("users.id"))
    sessions_purchased = Column(Integer, default=0)
    sessions_used = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    student = relationship("User", foreign_keys=[student_id])
    teacher = relationship("User", foreign_keys=[teacher_id])

class Homework(Base):
    __tablename__ = "homework"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"))
    description = Column(String)
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    session = relationship("Session", back_populates="homeworks")

class SessionProof(Base):
    __tablename__ = "session_proofs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"))
    image_url = Column(String)
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)
    uploader_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    uploader_role = Column(String, nullable=True)

    session = relationship("Session", back_populates="proofs")
    uploader = relationship("User", foreign_keys=[uploader_id])

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    message = Column(String)
    link = Column(String, nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="notifications")


# ── Messaging ──────────────────────────────────────────────────────────────────

from sqlalchemy import UniqueConstraint

class Conversation(Base):
    __tablename__ = "conversations"

    id         = Column(Integer, primary_key=True, index=True)
    type       = Column(String, nullable=False, default="dm")  # "dm" | "group" | "session_thread"
    name       = Column(String, nullable=True)                  # for groups / session thread label
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    participants   = relationship("ConversationParticipant", back_populates="conversation", cascade="all, delete-orphan")
    messages       = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")
    session_thread = relationship("SessionThread", back_populates="conversation", uselist=False)


class ConversationParticipant(Base):
    __tablename__ = "conversation_participants"
    __table_args__ = (
        UniqueConstraint("conversation_id", "user_id", name="uq_conv_participant"),
    )

    id              = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=False)
    joined_at       = Column(DateTime, default=datetime.datetime.utcnow)
    last_read_at    = Column(DateTime, nullable=True)

    conversation = relationship("Conversation", back_populates="participants")
    user         = relationship("User")


class Message(Base):
    __tablename__ = "messages"

    id              = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    sender_id       = Column(Integer, ForeignKey("users.id"), nullable=False)
    body            = Column(String, nullable=False)
    created_at      = Column(DateTime, default=datetime.datetime.utcnow, index=True)
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
