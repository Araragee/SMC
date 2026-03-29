"""
Seed script using raw sqlite3 — guaranteed to work regardless of import context.
Run from SMC/ root:
  ./backend/venv/bin/python3 backend/seed_data.py
"""
import sqlite3
import pathlib
import datetime
import hashlib
import sys

# Try to use bcrypt from the venv
try:
    import passlib.hash as ph
    def hash_pw(pw): return ph.bcrypt.hash(pw)
except Exception:
    # Fallback if passlib isn't available in this python context
    def hash_pw(pw): return pw + "notreallyhashed"

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent      # SMC/backend/
DB_PATH = SCRIPT_DIR / "sql_app.db"
ROOT_DB = SCRIPT_DIR.parent / "sql_app.db"               # SMC/sql_app.db (when uvicorn runs from root)
if not DB_PATH.exists() and ROOT_DB.exists():
    DB_PATH = ROOT_DB

if not DB_PATH.exists():
    print(f"❌ Database not found.\n   Checked:\n   {DB_PATH}\n   {ROOT_DB}")
    print("   Ensure the server has run at least once: python3 -m uvicorn backend.main:app")
    sys.exit(1)

print(f"📂 Using database: {DB_PATH}")

conn = sqlite3.connect(str(DB_PATH))
cur = conn.cursor()

TEACHERS = [
    ("Dr. Sarah Jenkins",  "sarah.jenkins@smc.edu"),
    ("Marcus Vane",         "marcus.vane@smc.edu"),
    ("Dr. Eleanor Rigby",   "eleanor.rigby@smc.edu"),
    ("Arthur Brown",        "arthur.brown@smc.edu"),
    ("Dr. Aris Thorne",     "aris.thorne@smc.edu"),
]

STUDENTS = [
    ("Elena Rodriguez",  "elena.rodriguez@smc.edu"),
    ("Julian Chen",      "julian.chen@smc.edu"),
    ("Sarah Mitchell",   "sarah.mitchell@smc.edu"),
]

HOMEWORK_TEXTS = [
    "Practice C major scales for 20 minutes daily",
    "Learn the first 16 bars of the assigned piece",
    "Record yourself playing the etude and listen back",
    "Focus on finger independence exercises at 80bpm",
    "Transcribe the melody from this week's recording",
]

def get_role_id(name):
    cur.execute("SELECT id FROM roles WHERE name=?", (name,))
    row = cur.fetchone()
    if not row:
        cur.execute("INSERT INTO roles (name) VALUES (?)", (name,))
        conn.commit()
        cur.execute("SELECT id FROM roles WHERE name=?", (name,))
        row = cur.fetchone()
    return row[0]

def upsert_user(name, email, role_id, sessions_left=0):
    cur.execute("SELECT id FROM users WHERE email=?", (email,))
    row = cur.fetchone()
    if row:
        print(f"  Exists: {email}")
        return row[0]
    hashed = hash_pw("password123")
    cur.execute(
        "INSERT INTO users (email, name, hashed_password, is_active, role_id, sessions_left) VALUES (?,?,?,1,?,?)",
        (email, name, hashed, role_id, sessions_left)
    )
    conn.commit()
    cur.execute("SELECT id FROM users WHERE email=?", (email,))
    uid = cur.fetchone()[0]
    print(f"  Created: {email}")
    return uid

def seed():
    teacher_role_id = get_role_id("teacher")
    student_role_id = get_role_id("student")
    get_role_id("admin")  # ensure admin role exists too

    teacher_ids = [upsert_user(n, e, teacher_role_id, 0) for n, e in TEACHERS]
    student_ids = [upsert_user(n, e, student_role_id, 10) for n, e in STUDENTS]

    base = datetime.datetime(2026, 3, 22, 9, 0, 0)
    session_count = 0
    hw_count = 0

    for i, sid in enumerate(student_ids):
        for j, tid in enumerate(teacher_ids):
            for k in range(2):
                offset_days = (i * 5 + j * 2 + k) % 14
                offset_hours = (j * 2 + k * 3) % 8
                start = base + datetime.timedelta(days=offset_days, hours=offset_hours)
                end = start + datetime.timedelta(hours=1)
                status = "completed" if (k == 0 and j < 3) else "scheduled"

                cur.execute(
                    "INSERT INTO sessions (teacher_id, student_id, start_time, end_time, status) VALUES (?,?,?,?,?)",
                    (tid, sid, start.isoformat(), end.isoformat(), status)
                )
                conn.commit()
                sess_id = cur.lastrowid
                session_count += 1

                if status == "completed":
                    hw = HOMEWORK_TEXTS[(i + j + k) % len(HOMEWORK_TEXTS)]
                    is_done = 1 if k == 0 else 0
                    cur.execute(
                        "INSERT INTO homework (session_id, description, is_completed, created_at) VALUES (?,?,?,?)",
                        (sess_id, hw, is_done, datetime.datetime.utcnow().isoformat())
                    )
                    conn.commit()
                    hw_count += 1

    print(f"\n✅ Seeded {len(teacher_ids)} teachers, {len(student_ids)} students, {session_count} sessions, {hw_count} homework entries.")
    print("\nLogin credentials for all new accounts: password123")
    print("\nTeacher accounts:")
    for n, e in TEACHERS:
        print(f"  {e}")
    print("\nStudent accounts:")
    for n, e in STUDENTS:
        print(f"  {e}")

if __name__ == "__main__":
    seed()
    conn.close()
