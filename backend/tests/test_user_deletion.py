"""Deleting a user must never 500, whatever else references them.

SQLite in these tests does not enforce foreign keys by default, so the hard
constraint is exercised against the shape of the code: rows that belong to the
account are cleared, linked accounts are deactivated rather than deleted.
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

    engine = create_engine(f"sqlite:///{tmp_path/'users.db'}", connect_args={"check_same_thread": False})
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
    role_ids = {"admin": admin_role.id, "student": student_role.id, "teacher": teacher_role.id}
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
        c.role_ids = role_ids
        c.session_factory = TestingSession
        yield c
    auth_session.close()
    app.dependency_overrides.clear()


def test_delete_clean_user_is_removed(client):
    created = client.post("/users/", json={
        "email": "gone@x.io", "name": "Gone", "password": "SmokeTest!2345",
        "role_id": client.role_ids["student"], "username": "gone",
    })
    assert created.status_code == 200, created.text
    user_id = created.json()["user"]["id"]

    removed = client.delete(f"/users/{user_id}")
    assert removed.status_code == 200, removed.text
    assert "deleted" in removed.json()["message"]
    assert client.get(f"/users/{user_id}").status_code == 404


def test_delete_clears_refresh_tokens_and_push_subscriptions(client):
    """A deleted account must not leave a usable refresh token behind."""
    import datetime

    created = client.post("/users/", json={
        "email": "tok@x.io", "name": "Tok", "password": "SmokeTest!2345",
        "role_id": client.role_ids["student"], "username": "tok",
    })
    user_id = created.json()["user"]["id"]

    session = client.session_factory()
    session.add(models.RefreshToken(
        user_id=user_id, token_hash="deadbeef",
        expires_at=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=1),
    ))
    session.add(models.PushSubscription(
        user_id=user_id, endpoint="https://push.example/x", keys_p256dh="k", keys_auth="a",
    ))
    session.commit()
    session.close()

    removed = client.delete(f"/users/{user_id}")
    assert removed.status_code == 200, removed.text

    session = client.session_factory()
    assert session.query(models.RefreshToken).filter_by(user_id=user_id).count() == 0
    assert session.query(models.PushSubscription).filter_by(user_id=user_id).count() == 0
    session.close()


def test_user_with_sessions_is_deactivated_not_deleted(client):
    import datetime

    created = client.post("/users/", json={
        "email": "linked@x.io", "name": "Linked", "password": "SmokeTest!2345",
        "role_id": client.role_ids["student"], "username": "linked",
    })
    user_id = created.json()["user"]["id"]

    start = datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=1)
    session = client.session_factory()
    session.add(models.Session(
        teacher_id=client.ids["teacher"], student_id=user_id,
        start_time=start, end_time=start + datetime.timedelta(hours=1), status="scheduled",
    ))
    session.commit()
    session.close()

    removed = client.delete(f"/users/{user_id}")
    assert removed.status_code == 200, removed.text
    assert "deactivated" in removed.json()["message"]
    assert client.get(f"/users/{user_id}").json()["is_active"] is False
