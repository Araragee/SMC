"""Tests for Phase 6 Stretch features: WebP downscaling and working hours enforcement."""
import io
import pytest
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, UploadFile
from PIL import Image

from backend.config import settings
from backend.utils.uploads import save_upload
from backend.test_main import (  # noqa: F401
    TestingSessionLocal,
    as_admin,
    as_student,
    as_teacher,
    client,
    fresh_db,
)
from backend.test_session_state_machine import (  # noqa: F401
    _make_user_obj,
    _seed_users,
    _swap_to_student,
    _swap_to_teacher,
)


def test_save_upload_webp_downscaling(tmp_path, monkeypatch):
    """Test that save_upload downscales large images and saves as WebP."""
    # Create a 3000 x 1200 PNG
    img = Image.new("RGB", (3000, 1200), color="red")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    upload = UploadFile(filename="large_photo.png", file=buf)
    
    # Run save_upload
    public_url, disk_path = save_upload(upload, "test_subdir")
    
    # Assert public URL and disk path have webp extension
    assert public_url.endswith(".webp")
    assert disk_path.endswith(".webp")
    
    # Open saved image and verify dimensions and format
    saved_img = Image.open(disk_path)
    assert saved_img.format == "WEBP"
    
    # Verify downscaled size: max edge is 2000, keeping aspect ratio (3000:1200 -> 2000:800)
    w, h = saved_img.size
    assert w == 2000
    assert h == 800

    # Clean up
    import os
    try:
        os.remove(disk_path)
    except OSError:
        pass


def test_working_hours_enforced_for_non_admins(client, as_admin):
    """Test that non-admins cannot propose/counter sessions outside working hours, but admins can."""
    a, t, s = _seed_users(client)
    
    # 1. Propose as student outside working hours (e.g., 07:00 UTC)
    # Configure working hours to be 8 to 22 in config
    base_date = datetime.now(timezone.utc) + timedelta(days=2)
    # set hour to 7
    start_outside = base_date.replace(hour=7, minute=0, second=0, microsecond=0)
    end_outside = start_outside + timedelta(hours=1)
    
    # Swap to student
    student_user = _make_user_obj(s, "student", "Student")
    _swap_to_student(student_user)
    
    # Propose session outside working hours -> should fail
    r = client.post("/sessions/propose/student", json={
        "teacher_id": t,
        "student_id": s,
        "start_time": start_outside.isoformat(),
        "end_time": end_outside.isoformat(),
        "instrument_id": 1,
        "notes": "Testing outside working hours",
    })
    assert r.status_code == 400
    assert "working hours" in r.json()["detail"].lower()

    # 2. Propose as student inside working hours -> should succeed
    start_inside = base_date.replace(hour=9, minute=0, second=0, microsecond=0)
    end_inside = start_inside + timedelta(hours=1)
    r = client.post("/sessions/propose/student", json={
        "teacher_id": t,
        "student_id": s,
        "start_time": start_inside.isoformat(),
        "end_time": end_inside.isoformat(),
        "instrument_id": 1,
        "notes": "Testing inside working hours",
    })
    assert r.status_code == 200
    
    # 3. Swap back to admin, schedule session outside working hours -> should succeed
    as_admin_user = _make_user_obj(a, "admin", "Admin")
    # Swap back to admin (or via header in pytest fixture client)
    # But pytest fixture client is overridden by the global require dependencies.
    # The fixture as_admin overrides active user to admin.
    from backend.dependencies import get_current_active_user, require_admin
    from backend.main import app
    app.dependency_overrides[get_current_active_user] = lambda: as_admin_user
    app.dependency_overrides[require_admin] = lambda: as_admin_user
    
    r = client.post("/sessions/", json={
        "student_id": s,
        "teacher_id": t,
        "start_time": start_outside.isoformat(),
        "end_time": end_outside.isoformat(),
        "notes": "Admin schedules outside working hours",
    })
    assert r.status_code == 200
