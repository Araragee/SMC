import sqlite3
import pathlib
import datetime
import sys

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent      # SMC/backend/
DB_PATH = SCRIPT_DIR / "sql_app.db"

if not DB_PATH.exists():
    print(f"❌ Database not found at {DB_PATH}")
    sys.exit(1)

conn = sqlite3.connect(str(DB_PATH))
cur = conn.cursor()

def seed_enrollments():
    print("Seeding enrollments...")
    # Get all unique student-teacher pairs from sessions
    cur.execute("SELECT DISTINCT teacher_id, student_id FROM sessions")
    pairs = cur.fetchall()
    
    for tid, sid in pairs:
        cur.execute("SELECT id FROM enrollments WHERE teacher_id = ? AND student_id = ?", (tid, sid))
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO enrollments (student_id, teacher_id, sessions_purchased, sessions_used, created_at) VALUES (?, ?, ?, ?, ?)",
                (sid, tid, 10, 2, datetime.datetime.utcnow().isoformat())
            )
            print(f"  Created enrollment: Teacher {tid} -> Student {sid}")
    conn.commit()

def seed_more_sessions():
    print("Seeding more diverse sessions...")
    # teacher@example.com (id 2) and student@example.com (id 3)
    tid, sid = 2, 3
    
    now = datetime.datetime(2026, 3, 23, 10, 0, 0) # Today
    
    sessions = [
        # Past sessions (completed)
        (now - datetime.timedelta(days=7), now - datetime.timedelta(days=7, hours=-1), "completed", None, "Reviewing basics"),
        (now - datetime.timedelta(days=14), now - datetime.timedelta(days=14, hours=-1), "completed", None, "First lesson"),
        
        # Upcoming sessions
        (now + datetime.timedelta(days=1, hours=2), now + datetime.timedelta(days=1, hours=3), "scheduled", None, "Tomorrow morning lesson"),
        (now + datetime.timedelta(days=2, hours=5), now + datetime.timedelta(days=2, hours=6), "pending_teacher", sid, "Student requested this"),
        (now + datetime.timedelta(days=3, hours=-2), now + datetime.timedelta(days=3, hours=-1), "pending_admin", tid, "Teacher proposed, needs admin"),
    ]
    
    for start, end, status, proposer, notes in sessions:
        cur.execute(
            "INSERT INTO sessions (teacher_id, student_id, start_time, end_time, status, proposed_by, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (tid, sid, start.isoformat(), end.isoformat(), status, proposer, notes)
        )
    
    print(f"  Added {len(sessions)} more sessions for teacher@example.com and student@example.com")
    conn.commit()

if __name__ == "__main__":
    seed_enrollments()
    seed_more_sessions()
    conn.close()
    print("✅ Comprehensive seeding complete.")
