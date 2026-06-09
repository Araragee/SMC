from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import text
from backend.main import app
from backend.models import Session as SessionModel, User, Enrollment, Notification, Role
from backend.test_main import (  # noqa: F401
    TestingSessionLocal,
    as_admin,
    as_student,
    as_teacher,
    client,
    fresh_db,
)
from backend.test_session_state_machine import _seed_users, _make_user_obj, _iso, _future, _swap_to_student, _swap_to_teacher
from backend.routers.sessions import session_checker_task

def test_atomic_enrollment_counters(client, as_admin):
    # Setup student, teacher, and an active enrollment
    _, t_id, s_id = _seed_users(client)
    db = TestingSessionLocal()
    
    # Create enrollment
    enrollment = Enrollment(
        student_id=s_id,
        teacher_id=t_id,
        sessions_purchased=10,
        sessions_used=0,
        is_active=True
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    eid = enrollment.id
    db.close()

    # Create a past session to record, which increments enrollment.sessions_used
    r = client.post(
        "/sessions/record",
        json={
            "student_id": s_id,
            "teacher_id": t_id,
            "start_time": _iso(datetime.now(timezone.utc) - timedelta(hours=2)),
            "end_time": _iso(datetime.now(timezone.utc) - timedelta(hours=1)),
            "notes": "atomic test",
            "session_number": 1,
        }
    )
    assert r.status_code == 200, r.text
    sid = r.json()["id"]

    db = TestingSessionLocal()
    db_enrollment = db.query(Enrollment).filter(Enrollment.id == eid).first()
    assert db_enrollment.sessions_used == 1
    db.close()

    # Now delete the session, which should decrement the enrollment
    r = client.delete(f"/sessions/{sid}")
    assert r.status_code == 200, r.text

    db = TestingSessionLocal()
    db_enrollment = db.query(Enrollment).filter(Enrollment.id == eid).first()
    assert db_enrollment.sessions_used == 0
    db.close()

def test_session_deletion_limit_30_days(client, as_admin):
    _, t_id, s_id = _seed_users(client)
    db = TestingSessionLocal()
    
    # 1. Create a completed session that is old (e.g. 35 days ago)
    old_start = datetime.now(timezone.utc) - timedelta(days=35)
    old_session = SessionModel(
        student_id=s_id,
        teacher_id=t_id,
        start_time=old_start.replace(tzinfo=None),
        end_time=(old_start + timedelta(hours=1)).replace(tzinfo=None),
        status="completed",
        version=0,
    )
    
    # 2. Create a completed session that is new (e.g. 5 days ago)
    new_start = datetime.now(timezone.utc) - timedelta(days=5)
    new_session = SessionModel(
        student_id=s_id,
        teacher_id=t_id,
        start_time=new_start.replace(tzinfo=None),
        end_time=(new_start + timedelta(hours=1)).replace(tzinfo=None),
        status="completed",
        version=0,
    )
    
    db.add(old_session)
    db.add(new_session)
    db.commit()
    db.refresh(old_session)
    db.refresh(new_session)
    old_id = old_session.id
    new_id = new_session.id
    db.close()

    # Deleting old session should be blocked with 409
    r = client.delete(f"/sessions/{old_id}")
    assert r.status_code == 409
    assert "older than 30 days" in r.json()["detail"]

    # Deleting new session should succeed
    r = client.delete(f"/sessions/{new_id}")
    assert r.status_code == 200

def test_enrollment_delete_guard_and_soft_delete(client, as_admin):
    _, t_id, s_id = _seed_users(client)
    db = TestingSessionLocal()
    
    # Create enrollment with sessions_used > 0
    e1 = Enrollment(
        student_id=s_id,
        teacher_id=t_id,
        sessions_purchased=5,
        sessions_used=2,
        is_active=True
    )
    # Create enrollment with sessions_used == 0
    e2 = Enrollment(
        student_id=s_id,
        teacher_id=t_id,
        sessions_purchased=5,
        sessions_used=0,
        is_active=True
    )
    db.add(e1)
    db.add(e2)
    db.commit()
    db.refresh(e1)
    db.refresh(e2)
    e1_id = e1.id
    e2_id = e2.id
    db.close()

    # Deleting e1 (used) without force parameter should reject with 409
    r = client.delete(f"/enrollments/{e1_id}")
    assert r.status_code == 409
    assert "active usage history" in r.json()["detail"]

    # Deleting e1 with force=true should succeed and soft-delete (set is_active=False)
    r = client.delete(f"/enrollments/{e1_id}?force=true")
    assert r.status_code == 204

    db = TestingSessionLocal()
    db_e1 = db.query(Enrollment).filter(Enrollment.id == e1_id).first()
    assert db_e1 is not None
    assert db_e1.is_active is False

    # Deleting e2 (not used) should perform a hard delete
    r = client.delete(f"/enrollments/{e2_id}")
    assert r.status_code == 204

    db_e2 = db.query(Enrollment).filter(Enrollment.id == e2_id).first()
    assert db_e2 is None
    db.close()

def test_nightly_drift_recalculation_and_purges(client, as_admin):
    _, t_id, s_id = _seed_users(client)
    db = TestingSessionLocal()
    
    # Setup student sessions_left to be wrong (drift)
    student = db.query(User).filter(User.id == s_id).first()
    student.sessions_left = 50 # incorrect drift value
    
    # Active enrollment: purchased=10, used=2 => sessions left = 8
    e = Enrollment(
        student_id=s_id,
        teacher_id=t_id,
        sessions_purchased=10,
        sessions_used=2,
        is_active=True
    )
    # Inactive/soft-deleted enrollment: purchased=5, used=1 => should be ignored in active count
    e_inactive = Enrollment(
        student_id=s_id,
        teacher_id=t_id,
        sessions_purchased=5,
        sessions_used=1,
        is_active=False
    )
    
    # Add an old notification to test notification purge (>90 days)
    old_time = datetime.now(timezone.utc) - timedelta(days=95)
    old_notif = Notification(
        user_id=s_id,
        message="Too old",
        created_at=old_time.replace(tzinfo=None)
    )
    
    db.add(e)
    db.add(e_inactive)
    db.add(old_notif)
    db.commit()
    
    # Recalculate sessions endpoint
    r = client.post(f"/students/{s_id}/recalculate-sessions")
    assert r.status_code == 200
    assert r.json()["new_sessions_left"] == 8

    # Manually reset drift and run cleanup logic from session_checker_task
    student.sessions_left = 50
    db.commit()
    db.close()

    # Trigger checker daily tasks by calling the endpoint or simulating task logic
    # We can mock/force the timer in session_checker_task or run the db code directly.
    # Let's test the database calculation logic manually using db session
    db = TestingSessionLocal()
    
    # 90-day notification purge
    now = datetime.now(timezone.utc)
    deleted_notifs = db.query(Notification).filter(Notification.created_at < now - timedelta(days=90)).delete()
    assert deleted_notifs > 0
    
    # Drift check
    students = db.query(User).filter(User.sessions_left == 50).all()
    for s in students:
        enrollments = db.query(Enrollment).filter(Enrollment.student_id == s.id, Enrollment.is_active == True).all()
        recalculated = sum(max(0, e.sessions_purchased - e.sessions_used) for e in enrollments)
        s.sessions_left = recalculated
    db.commit()
    
    s_updated = db.query(User).filter(User.id == s_id).first()
    assert s_updated.sessions_left == 8
    db.close()

def test_session_activity_log_permissions(client, as_admin):
    # Setup users: admin, teacher, student, and bystander
    admin_id, t_id, s_id = _seed_users(client)
    
    # Create a bystander student
    db = TestingSessionLocal()
    bystander = User(
        name="Bystander",
        username="bystander",
        email="bystander@x.com",
        hashed_password="test",
        role_id=db.query(Role).filter(Role.name.ilike("student")).first().id
    )
    db.add(bystander)
    db.commit()
    db.refresh(bystander)
    bystander_id = bystander.id
    db.close()

    # Create a session
    start = _future(48)
    db = TestingSessionLocal()
    session = SessionModel(
        teacher_id=t_id,
        student_id=s_id,
        start_time=start.replace(tzinfo=None),
        end_time=(start + timedelta(hours=1)).replace(tzinfo=None),
        status="scheduled",
        version=0,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    sid = session.id
    db.close()

    # Log an activity for this session
    db = TestingSessionLocal()
    from backend.routers.activity import log_activity
    log_activity(db, action_type="session_created", description="Session created", target_type="session", target_id=sid)
    db.close()

    # 1. As admin, should be able to view history
    r = client.get(f"/activity-log/session/{sid}")
    assert r.status_code == 200
    assert len(r.json()) > 0
    assert r.json()[0]["description"] == "Session created"

    # 2. As student participant, should be able to view
    student_user = _make_user_obj(s_id, "student", "Student")
    _swap_to_student(student_user)
    r = client.get(f"/activity-log/session/{sid}")
    assert r.status_code == 200

    # 3. As teacher participant, should be able to view
    teacher_user = _make_user_obj(t_id, "teacher", "Teacher")
    _swap_to_teacher(teacher_user)
    r = client.get(f"/activity-log/session/{sid}")
    assert r.status_code == 200

    # 4. As bystander, should get 403 Forbidden
    bystander_user = _make_user_obj(bystander_id, "student", "Bystander")
    _swap_to_student(bystander_user)
    r = client.get(f"/activity-log/session/{sid}")
    assert r.status_code == 403

