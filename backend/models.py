from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import relationship
import datetime

from .database import Base

class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True) # Admin, Teacher, Student

    users = relationship("User", back_populates="role")


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
    # status: pending_teacher | pending_admin | scheduled | completed | cancelled | rejected
    status = Column(String, default="scheduled")
    proposed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(String, nullable=True)

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

    session = relationship("Session", back_populates="proofs")

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    message = Column(String)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="notifications")
