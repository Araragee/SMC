"""
Fresh seed script. Drops all tables, recreates from models, inserts mock data.
Run from project root: PYTHONPATH=. python -m backend.seed_fresh
"""
import datetime
import os
import sys
from datetime import timedelta

# Allow running as `python backend/seed_fresh.py` too
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import passlib.hash
from sqlalchemy.orm import Session

from backend import models
from backend.database import Base, SessionLocal, engine

# ── helpers ──────────────────────────────────────────────────────────────────

def pw(plain: str) -> str:
    return passlib.hash.bcrypt.hash(plain)

def dt(days_offset: int = 0, hour: int = 10, minute: int = 0) -> datetime.datetime:
    base = datetime.datetime.now(datetime.UTC).replace(
        hour=hour, minute=minute, second=0, microsecond=0
    )
    return base + timedelta(days=days_offset)


# ── reset ─────────────────────────────────────────────────────────────────────

print("Dropping all tables...")
Base.metadata.drop_all(bind=engine)
print("Creating all tables...")
Base.metadata.create_all(bind=engine)

db: Session = SessionLocal()

try:
    # ── roles ─────────────────────────────────────────────────────────────────
    admin_role   = models.Role(name="admin")
    teacher_role = models.Role(name="teacher")
    student_role = models.Role(name="student")
    db.add_all([admin_role, teacher_role, student_role])
    db.flush()

    # ── instruments ───────────────────────────────────────────────────────────
    instruments = [
        models.Instrument(name="Guitar"),
        models.Instrument(name="Piano"),
        models.Instrument(name="Drums"),
        models.Instrument(name="Violin"),
        models.Instrument(name="Ukulele"),
        models.Instrument(name="Bass Guitar"),
    ]
    db.add_all(instruments)
    db.flush()
    guitar, piano, drums, violin, ukulele, bass = instruments

    # ── users: admin ──────────────────────────────────────────────────────────
    admin = models.User(
        email="admin@smc.com",
        name="Admin User",
        username="admin",
        hashed_password=pw("admin123"),
        is_active=True,
        role_id=admin_role.id,
        email_verified=True,
        contact_number="09171234567",
    )
    db.add(admin)
    db.flush()

    # ── users: teachers ───────────────────────────────────────────────────────
    t1 = models.User(
        email="juan.santos@smc.com", name="Juan Santos", username="juansantos",
        hashed_password=pw("teacher123"), is_active=True, role_id=teacher_role.id,
        email_verified=True, contact_number="09181234567",
    )
    t2 = models.User(
        email="maria.reyes@smc.com", name="Maria Reyes", username="mariareyes",
        hashed_password=pw("teacher123"), is_active=True, role_id=teacher_role.id,
        email_verified=True, contact_number="09191234567",
    )
    t3 = models.User(
        email="carlos.diaz@smc.com", name="Carlos Diaz", username="carlosdiaz",
        hashed_password=pw("teacher123"), is_active=True, role_id=teacher_role.id,
        email_verified=True, contact_number="09201234567",
    )
    db.add_all([t1, t2, t3])
    db.flush()

    # teacher instruments
    db.add_all([
        models.UserInstrument(user_id=t1.id, instrument_id=guitar.id),
        models.UserInstrument(user_id=t1.id, instrument_id=bass.id),
        models.UserInstrument(user_id=t2.id, instrument_id=piano.id),
        models.UserInstrument(user_id=t2.id, instrument_id=violin.id),
        models.UserInstrument(user_id=t3.id, instrument_id=drums.id),
        models.UserInstrument(user_id=t3.id, instrument_id=ukulele.id),
    ])

    # ── users: students ───────────────────────────────────────────────────────
    students_data = [
        ("Miguel Torres",   "miguel.torres@email.com",   "migueltorres",   guitar.id,  t1.id, 8,  12),
        ("Sofia Cruz",      "sofia.cruz@email.com",      "sofiacruz",      piano.id,   t2.id, 5,  10),
        ("Liam Bautista",   "liam.bautista@email.com",   "liambautista",   drums.id,   t3.id, 10, 15),
        ("Isabella Flores", "isabella.flores@email.com", "isabellaflo",    violin.id,  t2.id, 3,  8),
        ("Ethan Mendoza",   "ethan.mendoza@email.com",   "ethanmendoza",   ukulele.id, t3.id, 6,  10),
        ("Chloe Garcia",    "chloe.garcia@email.com",    "chloegarcia",    guitar.id,  t1.id, 2,  12),
    ]

    students = []
    for name, email, uname, instr_id, teacher_id, sess_left, sess_enrolled in students_data:
        s = models.User(
            email=email, name=name, username=uname,
            hashed_password=pw("student123"), is_active=True, role_id=student_role.id,
            email_verified=True, sessions_left=sess_left, sessions_enrolled=sess_enrolled,
            birthday="2005-03-15", age=19, school="SMC Music Academy",
            parent_name=f"{name.split()[0]}'s Parent", parent_contact="09151234567",
        )
        db.add(s)
        db.flush()
        db.add(models.UserInstrument(user_id=s.id, instrument_id=instr_id))
        db.add(models.TeacherStudent(teacher_id=teacher_id, student_id=s.id))
        db.add(models.Enrollment(
            student_id=s.id, teacher_id=teacher_id,
            sessions_purchased=sess_enrolled, sessions_used=sess_enrolled - sess_left,
        ))
        students.append(s)

    db.flush()
    s1, s2, s3, s4, s5, s6 = students

    # ── sessions ──────────────────────────────────────────────────────────────
    now = datetime.datetime.now(datetime.UTC)

    def session(teacher, student, instr, days, hour=14, status="scheduled", notes=None, proposed_by=None):
        start = dt(days, hour)
        return models.Session(
            teacher_id=teacher.id, student_id=student.id,
            instrument_id=instr.id,
            start_time=start, end_time=start + timedelta(hours=1),
            status=status, notes=notes,
            proposed_by=proposed_by,
            created_at=now - timedelta(days=abs(days) + 1),
            updated_at=now,
        )

    sessions = [
        # Upcoming scheduled
        session(t1, s1, guitar,  2, 14, "scheduled"),
        session(t1, s6, guitar,  3, 10, "scheduled"),
        session(t2, s2, piano,   1, 15, "scheduled"),
        session(t2, s4, violin,  4, 11, "scheduled"),
        session(t3, s3, drums,   2, 16, "scheduled"),
        session(t3, s5, ukulele, 5, 13, "scheduled"),

        # Pending negotiation
        session(t1, s1, guitar,  6, 14, "pending_teacher",  "Rescheduling request", s1.id),
        session(t2, s2, piano,   7, 10, "pending_student",  "Counter proposal",     t2.id),
        session(t3, s3, drums,   8, 14, "pending_admin",    "Both parties agreed",  t3.id),

        # Overdue / verification
        session(t1, s6, guitar,  -3, 14, "overdue"),
        session(t2, s4, violin,  -2, 15, "pending_verification", "Proof uploaded"),
        session(t3, s5, ukulele, -4, 13, "overdue_rejected", notes="Proof was blurry"),

        # Completed (past sessions)
        session(t1, s1, guitar,  -7,  14, "completed"),
        session(t1, s1, guitar,  -14, 14, "completed"),
        session(t2, s2, piano,   -7,  15, "completed"),
        session(t2, s2, piano,   -10, 15, "completed"),
        session(t3, s3, drums,   -5,  16, "completed"),
        session(t3, s3, drums,   -12, 16, "completed"),
        session(t2, s4, violin,  -6,  11, "completed"),
        session(t3, s5, ukulele, -8,  13, "completed"),

        # Cancelled / rejected
        session(t1, s6, guitar, -1,  10, "cancelled"),
        session(t2, s2, piano,  -15, 14, "rejected"),
    ]
    db.add_all(sessions)
    db.flush()

    # Homework on a few completed sessions
    db.add_all([
        models.Homework(session_id=sessions[12].id, description="Practice C major scale 10 mins daily", is_completed=True),
        models.Homework(session_id=sessions[13].id, description="Learn intro riff of Wonderwall", is_completed=False),
        models.Homework(session_id=sessions[14].id, description="Practice Für Elise bars 1-16", is_completed=True),
        models.Homework(session_id=sessions[16].id, description="Work on kick-snare pattern at 80 BPM", is_completed=False),
    ])

    # ── payments ──────────────────────────────────────────────────────────────
    payment_data = [
        (s1.id, 300000, "bank_transfer", "completed", "10-session bundle"),
        (s2.id, 250000, "cash",          "completed", "5-session top-up"),
        (s3.id, 375000, "bank_transfer", "completed", "15-session bundle"),
        (s4.id, 200000, "cash",          "completed", "8-session bundle"),
        (s5.id, 250000, "card",          "completed", "10-session bundle"),
        (s6.id, 300000, "bank_transfer", "completed", "12-session bundle"),
        (s1.id, 300000, "cash",          "completed", "Renewal"),
        (s3.id, 375000, "bank_transfer", "pending",   "Pending clearance"),
    ]
    for student_id, amount, method, status, notes in payment_data:
        db.add(models.Payment(
            student_id=student_id, amount=amount,
            method=method, status=status, notes=notes,
            date=now - timedelta(days=30),
        ))

    # ── shop products ─────────────────────────────────────────────────────────
    products = [
        models.InstrumentProduct(name="Yamaha FG800 Acoustic Guitar", description="Solid spruce top, beginner-friendly", price_cents=1500000, stock=5, category_id=guitar.id),
        models.InstrumentProduct(name="Fender Squier Stratocaster",   description="Electric guitar starter pack",        price_cents=2200000, stock=3, category_id=guitar.id),
        models.InstrumentProduct(name="Yamaha P-45 Digital Piano",    description="88 weighted keys, compact",           price_cents=3500000, stock=2, category_id=piano.id),
        models.InstrumentProduct(name="Casio CT-X700 Keyboard",       description="61 keys, 600 tones",                  price_cents=900000,  stock=8, category_id=piano.id),
        models.InstrumentProduct(name="Pearl Roadshow Drum Kit",      description="5-piece complete set with cymbals",   price_cents=4800000, stock=2, category_id=drums.id),
        models.InstrumentProduct(name="Vic Firth 5A Drumsticks",      description="Hickory, standard size pair",         price_cents=35000,   stock=30, category_id=drums.id),
        models.InstrumentProduct(name="Cecilio CVN-300 Violin",       description="Solid wood, 4/4 size with case",      price_cents=1200000, stock=4, category_id=violin.id),
        models.InstrumentProduct(name="Kala KA-15S Ukulele",          description="Soprano, mahogany top",               price_cents=350000,  stock=10, category_id=ukulele.id),
        models.InstrumentProduct(name="Squier Affinity Jazz Bass",    description="4-string, sunburst finish",           price_cents=1800000, stock=3, category_id=bass.id),
        models.InstrumentProduct(name="D'Addario EXL110 Guitar Strings", description="Regular light 10-46", price_cents=45000, stock=50, category_id=guitar.id),
        models.InstrumentProduct(name="Guitar Capo (Universal)",      description="Spring tension, fits most guitars",   price_cents=25000,   stock=20, category_id=guitar.id),
    ]
    db.add_all(products)
    db.flush()

    # Shop orders
    order1 = models.Order(
        user_id=s1.id, status="approved", total_cents=1545000, notes="Need by next week",
        created_at=now - timedelta(days=5), updated_at=now - timedelta(days=4),
    )
    db.add(order1)
    db.flush()
    db.add_all([
        models.OrderItem(order_id=order1.id, product_id=products[0].id, quantity=1, price_cents_at_purchase=1500000),
        models.OrderItem(order_id=order1.id, product_id=products[9].id, quantity=1, price_cents_at_purchase=45000),
    ])

    order2 = models.Order(
        user_id=s3.id, status="pending", total_cents=4800000, notes="Drum kit for practice at home",
        created_at=now - timedelta(days=2), updated_at=now - timedelta(days=2),
    )
    db.add(order2)
    db.flush()
    db.add(models.OrderItem(order_id=order2.id, product_id=products[4].id, quantity=1, price_cents_at_purchase=4800000))

    # ── notifications ─────────────────────────────────────────────────────────
    notif_data = [
        (s1.id,  "Your session with Juan Santos is confirmed for tomorrow at 2:00 PM.", None),
        (s1.id,  "Homework assigned: Practice C major scale daily.", None),
        (t1.id,  "Miguel Torres has requested a schedule change.", None),
        (t1.id,  "Chloe Garcia's session is overdue — please follow up.", None),
        (admin.id, "New shop order from Miguel Torres is pending approval.", None),
        (admin.id, "Session proof uploaded by Isabella Flores — needs review.", None),
        (s2.id,  "Maria Reyes proposed a new session time. Please approve or counter.", None),
        (s3.id,  "Your session is confirmed for tomorrow at 4:00 PM.", None),
        (t2.id,  "Sofia Cruz has uploaded session proof.", None),
        (t3.id,  "Ethan Mendoza's session proof was rejected by admin.", None),
    ]
    for user_id, message, link in notif_data:
        db.add(models.Notification(user_id=user_id, message=message, link=link, is_read=False))

    # ── activity logs ─────────────────────────────────────────────────────────
    log_data = [
        ("session_completed",    admin.id,  "Admin User", "session",  sessions[12].id, f"Admin completed session #{sessions[12].id}"),
        ("payment_recorded",     admin.id,  "Admin User", "payment",  1,               "Payment of ₱3,000.00 recorded for Miguel Torres"),
        ("user_created",         admin.id,  "Admin User", "user",     s1.id,           "New student Miguel Torres registered"),
        ("session_status_change",t1.id,     "Juan Santos","session",  sessions[6].id,  "Session rescheduled by student Miguel Torres"),
        ("order_placed",         s1.id,     "Miguel Torres","order",  order1.id,       "Miguel Torres placed order #1 for ₱15,450.00"),
        ("order_approved",       admin.id,  "Admin User", "order",    order1.id,       "Admin approved order #1"),
        ("session_proof_upload", s4.id,     "Isabella Flores","session",sessions[10].id,"Isabella Flores uploaded proof for session"),
        ("recurring_series_created", admin.id,"Admin User","session", None,            "Admin created 6 recurring sessions for Juan Santos / Miguel Torres"),
    ]
    for action_type, actor_id, actor_name, target_type, target_id, description in log_data:
        db.add(models.ActivityLog(
            action_type=action_type, actor_id=actor_id, actor_name=actor_name,
            target_type=target_type, target_id=target_id, description=description,
            created_at=now - timedelta(days=1),
        ))

    # ── conversations / messages ───────────────────────────────────────────────
    # DM: admin ↔ teacher 1
    conv1 = models.Conversation(type="dm")
    db.add(conv1)
    db.flush()
    db.add_all([
        models.ConversationParticipant(conversation_id=conv1.id, user_id=admin.id),
        models.ConversationParticipant(conversation_id=conv1.id, user_id=t1.id),
    ])
    db.add_all([
        models.Message(conversation_id=conv1.id, sender_id=admin.id, body="Hi Juan, please remind Miguel about his homework."),
        models.Message(conversation_id=conv1.id, sender_id=t1.id,    body="Sure, will do. He still needs to practice the C major scale."),
        models.Message(conversation_id=conv1.id, sender_id=admin.id, body="Great, thanks!"),
    ])

    # DM: teacher 2 ↔ student 2
    conv2 = models.Conversation(type="dm")
    db.add(conv2)
    db.flush()
    db.add_all([
        models.ConversationParticipant(conversation_id=conv2.id, user_id=t2.id),
        models.ConversationParticipant(conversation_id=conv2.id, user_id=s2.id),
    ])
    db.add_all([
        models.Message(conversation_id=conv2.id, sender_id=t2.id, body="Sofia, don't forget our session tomorrow at 3 PM."),
        models.Message(conversation_id=conv2.id, sender_id=s2.id, body="Yes po, I'll be ready! I've been practicing Für Elise."),
    ])

    db.commit()
    print("\n✅ Database seeded successfully!")
    print("\nAccounts:")
    print("  admin     — admin@smc.com        / admin123")
    print("  teacher1  — juan.santos@smc.com  / teacher123")
    print("  teacher2  — maria.reyes@smc.com  / teacher123")
    print("  teacher3  — carlos.diaz@smc.com  / teacher123")
    print("  student1  — miguel.torres@email.com  / student123")
    print("  student2  — sofia.cruz@email.com     / student123")
    print("  student3  — liam.bautista@email.com  / student123")
    print("  student4  — isabella.flores@email.com / student123")
    print("  student5  — ethan.mendoza@email.com  / student123")
    print("  student6  — chloe.garcia@email.com   / student123")

except Exception as e:
    db.rollback()
    print(f"\n❌ Seed failed: {e}")
    raise
finally:
    db.close()
