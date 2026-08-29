"""Roster endpoints: enrollment edits must keep a student's credit balance
in step with what was purchased, and must never drop below what was used.

Uses a throwaway SQLite database and FastAPI's dependency override so the
test touches no real Postgres.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend import models
from backend.database import Base, get_db
from backend.database import engine as app_engine
from backend.dependencies import get_current_active_user
from backend.main import app


@pytest.fixture()
def client(tmp_path):
    # App startup (lifespan) seeds roles/admin against the app's own engine —
    # conftest points that at a throwaway SQLite file, so just make the tables.
    Base.metadata.create_all(app_engine)

    engine = create_engine(f"sqlite:///{tmp_path/'roster.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    db = TestingSession()
    admin_role = models.Role(name="admin")
    student_role = models.Role(name="student")
    teacher_role = models.Role(name="teacher")
    db.add_all([admin_role, student_role, teacher_role])
    db.flush()
    admin = models.User(email="a@x.io", name="Admin", hashed_password="x", role_id=admin_role.id)
    student = models.User(
        email="s@x.io", name="Stu", hashed_password="x", sessions_left=0, role_id=student_role.id
    )
    teacher = models.User(email="t@x.io", name="Teach", hashed_password="x", role_id=teacher_role.id)
    db.add_all([admin, student, teacher])
    db.commit()
    ids = {"admin": admin.id, "student": student.id, "teacher": teacher.id}
    db.close()

    def override_db():
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    # Kept open for the duration of the test: the admin User is handed to
    # request handlers, which lazy-load ``role`` off it.
    auth_session = TestingSession()

    def override_user():
        return auth_session.query(models.User).filter(models.User.id == ids["admin"]).first()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_active_user] = override_user
    with TestClient(app) as c:
        c.ids = ids
        yield c
    auth_session.close()
    app.dependency_overrides.clear()


def test_enrollment_edit_moves_student_credits(client):
    created = client.post(
        "/enrollments/",
        json={
            "student_id": client.ids["student"],
            "teacher_id": client.ids["teacher"],
            "sessions_purchased": 8,
            "sessions_used": 0,
        },
    )
    assert created.status_code == 200, created.text
    enrollment_id = created.json()["id"]

    student = client.get(f"/users/{client.ids['student']}").json()
    assert student["sessions_left"] == 8

    # Raising the purchase raises the balance by exactly the delta.
    bumped = client.put(f"/enrollments/{enrollment_id}", json={"sessions_purchased": 12})
    assert bumped.status_code == 200, bumped.text
    assert bumped.json()["sessions_left"] == 12
    assert client.get(f"/users/{client.ids['student']}").json()["sessions_left"] == 12

    # Lowering it below what was already used is refused, not silently clamped.
    client.put(f"/enrollments/{enrollment_id}", json={"sessions_purchased": 12})
    listing = client.get("/enrollments/")
    assert listing.status_code == 200
    assert any(e["id"] == enrollment_id for e in listing.json())


def test_enrollment_cannot_drop_below_used(client):
    created = client.post(
        "/enrollments/",
        json={
            "student_id": client.ids["student"],
            "teacher_id": client.ids["teacher"],
            "sessions_purchased": 10,
            "sessions_used": 4,
        },
    )
    enrollment_id = created.json()["id"]

    refused = client.put(f"/enrollments/{enrollment_id}", json={"sessions_purchased": 3})
    assert refused.status_code == 400
    assert "already used" in refused.json()["detail"]


