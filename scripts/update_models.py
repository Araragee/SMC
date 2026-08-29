import re

with open("backend/models.py", "r") as f:
    content = f.read()

# Add Instrument model
instrument_model = """
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
"""

content = content.replace("class User(Base):", instrument_model + "\nclass User(Base):")

user_additions = """
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
"""

content = content.replace("    sessions_left = Column(Integer, default=0, nullable=True)", "    sessions_left = Column(Integer, default=0, nullable=True)" + user_additions)


session_additions = """
    instrument_id = Column(Integer, ForeignKey("instruments.id"), nullable=True)
    is_manual_entry = Column(Boolean, default=False)
    session_number = Column(Integer, nullable=True)

    instrument = relationship("Instrument")
"""

content = content.replace("    notes = Column(String, nullable=True)", "    notes = Column(String, nullable=True)" + session_additions)

with open("backend/models.py", "w") as f:
    f.write(content)
