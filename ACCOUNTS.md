# SMC Test Accounts

All accounts use the same password for easy testing.

**Password:** `password123`

## Primary Test Accounts
Use these for most functional testing (Schedule, Sessions, Enrollments).

| Role | Login / Username | Email | Name |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin` | `admin@smc.edu` | System Admin |
| **Teacher** | `teacher` | `teacher@smc.edu` | Default Teacher |
| **Student** | `student` | `student@smc.edu` | Default Student |

## Faculty (5 Teachers)
| Email | Name |
| :--- | :--- |
| `sarah.jenkins@smc.edu` | Dr. Sarah Jenkins |
| `marcus.vane@smc.edu` | Marcus Vane |
| `eleanor.rigby@smc.edu` | Dr. Eleanor Rigby |
| `arthur.brown@smc.edu` | Arthur Brown |
| `aris.thorne@smc.edu` | Dr. Aris Thorne |

## Students (40 Total)
Students are **randomly assigned** to 1-2 teachers each and have fake schedules with various session statuses.

| Email | Name |
| :--- | :--- |
| `elena.rodriguez0@smc.edu` | Elena Rodriguez |
| `julian.chen1@smc.edu` | Julian Chen |
| `sarah.mitchell2@smc.edu` | Sarah Mitchell |
| `marcus.johnson3@smc.edu` | Marcus Johnson |
| `james.williams4@smc.edu` | James Williams |
| `sophie.brown5@smc.edu` | Sophie Brown |
| `oliver.jones6@smc.edu` | Oliver Jones |
| `emma.garcia7@smc.edu` | Emma Garcia |
| `liam.miller8@smc.edu` | Liam Miller |
| `ava.davis9@smc.edu` | Ava Davis |
| `noah.martinez10@smc.edu` | Noah Martinez |
| `isabella.hernandez11@smc.edu` | Isabella Hernandez |
| `ethan.lopez12@smc.edu` | Ethan Lopez |
| `mia.gonzalez13@smc.edu` | Mia Gonzalez |
| `lucas.wilson14@smc.edu` | Lucas Wilson |
| `harper.anderson15@smc.edu` | Harper Anderson |
| `mason.thomas16@smc.edu` | Mason Thomas |
| `evelyn.taylor17@smc.edu` | Evelyn Taylor |
| `logan.moore18@smc.edu` | Logan Moore |
| `abigail.jackson19@smc.edu` | Abigail Jackson |
| `aiden.martin20@smc.edu` | Aiden Martin |
| `emily.lee21@smc.edu` | Emily Lee |
| `jackson.perez22@smc.edu` | Jackson Perez |
| `elizabeth.thompson23@smc.edu` | Elizabeth Thompson |
| `sebastian.white24@smc.edu` | Sebastian White |
| `avery.harris25@smc.edu` | Avery Harris |
| `benjamin.sanchez26@smc.edu` | Benjamin Sanchez |
| `ella.clark27@smc.edu` | Ella Clark |
| `michael.ramirez28@smc.edu` | Michael Ramirez |
| `scarlett.lewis29@smc.edu` | Scarlett Lewis |
| `daniel.robinson30@smc.edu` | Daniel Robinson |
| `victoria.young31@smc.edu` | Victoria Young |
| `matthew.walker32@smc.edu` | Matthew Walker |
| `grace.hall33@smc.edu` | Grace Hall |
| `alexander.allen34@smc.edu` | Alexander Allen |
| `chloe.king35@smc.edu` | Chloe King |
| `jacob.wright36@smc.edu` | Jacob Wright |
| `lily.scott37@smc.edu` | Lily Scott |
| `joseph.torres38@smc.edu` | Joseph Torres |
| `zoe.peterson39@smc.edu` | Zoe Peterson |

**Notes:**
- Students are randomly enrolled with 1-2 teachers each
- All students have 20 sessions available initially
- Fake schedules generated with mixed statuses: `scheduled`, `completed`, `pending_verification`, `overdue`
- Run `python3 backend/seed_data.py` to regenerate with new random assignments
