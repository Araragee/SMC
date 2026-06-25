"""
Seed script using raw sqlite3 — guaranteed to work regardless of import context.
Run from SMC/ root:
  ./backend/venv/bin/python3 backend/seed_data.py
"""
import datetime
import pathlib
import sqlite3
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

import random

TEACHERS = [
    ("Dr. Sarah Jenkins",  "sarah.jenkins@smc.edu"),
    ("Marcus Vane",         "marcus.vane@smc.edu"),
    ("Dr. Eleanor Rigby",   "eleanor.rigby@smc.edu"),
    ("Arthur Brown",        "arthur.brown@smc.edu"),
    ("Dr. Aris Thorne",     "aris.thorne@smc.edu"),
]

# Generate 40 random student names
FIRST_NAMES = ["Elena", "Julian", "Sarah", "Marcus", "James", "Sophie", "Oliver", "Emma", "Liam", "Ava",
               "Noah", "Isabella", "Ethan", "Mia", "Lucas", "Harper", "Mason", "Evelyn", "Logan", "Abigail",
               "Aiden", "Emily", "Jackson", "Elizabeth", "Sebastian", "Avery", "Benjamin", "Ella", "Michael", "Scarlett",
               "Daniel", "Victoria", "Matthew", "Grace", "Alexander", "Chloe", "Jacob", "Lily", "Joseph", "Zoe"]

LAST_NAMES = ["Rodriguez", "Chen", "Mitchell", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
              "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson",
              "Martin", "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis",
              "Robinson", "Young", "Walker", "Hall", "Allen", "King", "Wright", "Scott", "Torres", "Peterson"]

STUDENTS = [
    (f"{FIRST_NAMES[i]} {LAST_NAMES[i]}", f"{FIRST_NAMES[i].lower()}.{LAST_NAMES[i].lower()}{i}@smc.edu")
    for i in range(40)
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

def upsert_user(name, email, role_id, sessions_left=0, username=None):
    if not username:
        username = email.split("@")[0] if email else name.replace(" ", "").lower()

    cur.execute("SELECT id FROM users WHERE email=? OR username=?", (email, username))
    row = cur.fetchone()
    if row:
        print(f"  Exists: {username} ({email})")
        return row[0]
    hashed = hash_pw("password123")
    cur.execute(
        "INSERT INTO users (email, username, name, hashed_password, is_active, role_id, sessions_left) VALUES (?,?,?,?,1,?,?)",
        (email, username, name, hashed, role_id, sessions_left)
    )
    conn.commit()
    cur.execute("SELECT id FROM users WHERE username=?", (username,))
    uid = cur.fetchone()[0]
    print(f"  Created: {username} ({email})")
    return uid

def seed():
    teacher_role_id = get_role_id("teacher")
    student_role_id = get_role_id("student")
    get_role_id("admin")  # ensure admin role exists too

    # Simple accounts first
    upsert_user("Default Teacher", "teacher@smc.edu", teacher_role_id, 0, "teacher")
    upsert_user("Default Student", "student@smc.edu", student_role_id, 10, "student")
    upsert_user("System Admin", "admin@smc.edu", get_role_id("admin"), 0, "admin")

    teacher_ids = [upsert_user(n, e, teacher_role_id, 0) for n, e in TEACHERS]
    student_ids = [upsert_user(n, e, student_role_id, 20) for n, e in STUDENTS]

    # Randomly assign students to teachers (2-4 students per teacher on average)
    random.seed(42)  # for reproducibility
    enrollments_created = 0
    for sid in student_ids:
        # Each student gets 1-2 teachers
        num_teachers = random.randint(1, 2)
        assigned_teachers = random.sample(teacher_ids, num_teachers)
        for tid in assigned_teachers:
            # Create teacher-student assignment
            cur.execute(
                "INSERT OR IGNORE INTO teacher_students (teacher_id, student_id) VALUES (?,?)",
                (tid, sid)
            )
            # Create enrollment with purchased sessions
            cur.execute(
                "INSERT OR IGNORE INTO enrollments (teacher_id, student_id, sessions_purchased, sessions_used) VALUES (?,?,?,?)",
                (tid, sid, 20, 0)
            )
            conn.commit()
            enrollments_created += 1

    # Create fake schedules
    base = datetime.datetime(2026, 3, 22, 9, 0, 0)
    session_count = 0
    hw_count = 0
    statuses = ["scheduled", "completed", "pending_verification", "overdue"]

    for i, sid in enumerate(student_ids):
        # Get teachers assigned to this student
        cur.execute("SELECT teacher_id FROM enrollments WHERE student_id=?", (sid,))
        assigned_teachers = [row[0] for row in cur.fetchall()]

        for j, tid in enumerate(assigned_teachers):
            # Create 3-5 sessions per teacher-student pair
            for k in range(random.randint(3, 5)):
                offset_days = (i * 7 + j * 3 + k * 2) % 30
                offset_hours = (j * 2 + k) % 8
                start = base + datetime.timedelta(days=offset_days, hours=offset_hours)
                end = start + datetime.timedelta(hours=1)
                status = random.choice(statuses)

                cur.execute(
                    "INSERT INTO sessions (teacher_id, student_id, start_time, end_time, status) VALUES (?,?,?,?,?)",
                    (tid, sid, start.isoformat(), end.isoformat(), status)
                )
                conn.commit()
                sess_id = cur.lastrowid
                session_count += 1

                if status == "completed":
                    hw = HOMEWORK_TEXTS[(i + j + k) % len(HOMEWORK_TEXTS)]
                    is_done = 1 if random.random() > 0.3 else 0
                    cur.execute(
                        "INSERT INTO homework (session_id, description, is_completed, created_at) VALUES (?,?,?,?)",
                        (sess_id, hw, is_done, datetime.datetime.now(datetime.UTC).isoformat())
                    )
                    conn.commit()
                    hw_count += 1

    print(f"\n✅ Seeded {len(teacher_ids)} teachers, {len(student_ids)} students")
    print(f"   {enrollments_created} enrollments, {session_count} sessions, {hw_count} homework entries")
    print("\n🔐 Login credentials for all accounts: password123")
    print("\n👨‍🏫 Teacher accounts:")
    for n, e in TEACHERS:
        print(f"  {e}")
    print("\n👩‍🎓 Student accounts (sample):")
    for i, (n, e) in enumerate(STUDENTS[:5]):
        print(f"  {e}")
    print(f"  ... and {len(STUDENTS) - 5} more")

if __name__ == "__main__":
    seed()
    conn.close()
