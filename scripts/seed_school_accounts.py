"""Create the school's real teacher/student accounts and their enrollments.

Idempotent: re-running skips users and enrollments that already exist, so it is
safe to run against production more than once.

  python scripts/seed_school_accounts.py --dry-run   # show what would happen
  python scripts/seed_school_accounts.py             # apply
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend import models
from backend.database import SessionLocal
from backend.dependencies import pwd_context

TEMP_PASSWORD = "SMCTemp2026!"
EMAIL_DOMAIN = "smc.edu"

# (teacher name, instrument or None, [student names])
ROSTER = [
    ("Sernan", "Drum", [
        # active
        "Samantha Sapphire Pascual",
        "Gab Villorente",
        "Ethan Hasegawa",
        "Jhoelle Francis Canlas",
        "Aj Noche",
        # inactive (remaining sessions) — created active, status sorted in admin UI
        "Rex Garabillo",
        "Christian Beks",
        "Francis Fermin",
        "Raven Cruz",
        "Dylan Bautista",
        "Tyler Dela Cruz",
        "Althea Inez",
        "Rizza Marie Domingo",
        "Rica Marie Domingo",
        "Samantha Marcos",
        "Nathan",
    ]),
    ("Marco Silvestre", "Drum", [
        "Jose Mari Francisco M. Miclat",
        "Marcus M. Lundang",
        "Aiden Jaidiel A. Aguas",
    ]),
    ("Jerry A. Talay", "Keyboard", [
        "Jose Mari Sebastian M. Miclat",
        "Xion Sabado",
        "Ysabella Sabado",
        "Gabriel Sabado",
        "Zuri Park",
    ]),
    ("Mark Daniel Valete", None, [
        "Lucas Miguel Pilario",
        "Zachary Guo",
        "Aniela",
    ]),
]


def slug(name: str) -> str:
    """First + last word, letters only: 'Jerry A. Talay' -> 'jerrytalay'."""
    words = [re.sub(r"[^a-z]", "", w.lower()) for w in name.split()]
    words = [w for w in words if w]
    return words[0] if len(words) == 1 else words[0] + words[-1]


def unique_username(db, base: str, taken: set[str]) -> str:
    candidate, n = base, 1
    while candidate in taken or db.query(models.User).filter(models.User.username == candidate).first():
        n += 1
        candidate = f"{base}{n}"
    taken.add(candidate)
    return candidate


def main() -> None:
    dry = "--dry-run" in sys.argv
    db = SessionLocal()
    created_users, created_enrollments, skipped = [], [], []
    try:
        roles = {r.name: r for r in db.query(models.Role).all()}
        for name in ("admin", "teacher", "student"):
            if name not in roles:
                roles[name] = models.Role(name=name)
                db.add(roles[name])
        db.flush()

        instruments = {i.name: i for i in db.query(models.Instrument).all()}
        hashed = pwd_context.hash(TEMP_PASSWORD)
        taken: set[str] = set()

        def get_or_create(display: str, role_name: str, instrument):
            existing = db.query(models.User).filter(models.User.name == display).first()
            if existing:
                skipped.append(f"{role_name} {display} (exists, id={existing.id})")
                return existing
            username = unique_username(db, slug(display), taken)
            user = models.User(
                email=f"{username}@{EMAIL_DOMAIN}",
                username=username,
                name=display,
                hashed_password=hashed,
                role_id=roles[role_name].id,
                is_active=True,
                email_verified=True,
                must_change_password=True,
                sessions_left=0,
            )
            db.add(user)
            db.flush()
            if instrument is not None:
                db.add(models.UserInstrument(user_id=user.id, instrument_id=instrument.id))
            created_users.append((role_name, username, user.email, display))
            return user

        for teacher_name, instrument_name, student_names in ROSTER:
            instrument = instruments.get(instrument_name) if instrument_name else None
            if instrument_name and instrument is None:
                raise SystemExit(f"instrument {instrument_name!r} not in DB: {sorted(instruments)}")
            teacher = get_or_create(teacher_name, "teacher", instrument)

            for student_name in student_names:
                student = get_or_create(student_name, "student", instrument)
                link = db.query(models.Enrollment).filter(
                    models.Enrollment.student_id == student.id,
                    models.Enrollment.teacher_id == teacher.id,
                ).first()
                if link:
                    skipped.append(f"enrollment {student_name} -> {teacher_name} (exists)")
                    continue
                db.add(models.Enrollment(
                    student_id=student.id,
                    teacher_id=teacher.id,
                    sessions_purchased=0,
                    sessions_used=0,
                    status="active",
                    is_active=True,
                ))
                created_enrollments.append(f"{student_name} -> {teacher_name}")

        if dry:
            db.rollback()
        else:
            db.commit()
    finally:
        db.close()

    for line in skipped:
        print(f"skip  {line}")
    print(f"\n{'WOULD CREATE' if dry else 'CREATED'} {len(created_users)} users, "
          f"{len(created_enrollments)} enrollments\n")
    print(f"  {'role':<8} {'username':<22} {'email':<32} name")
    print("  " + "-" * 90)
    for role_name, username, email, display in created_users:
        print(f"  {role_name:<8} {username:<22} {email:<32} {display}")
    print(f"\n  password for every account above: {TEMP_PASSWORD}  (must change on first login)")
    for line in created_enrollments:
        print(f"  link  {line}")


if __name__ == "__main__":
    main()
