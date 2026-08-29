# SMC System Structure & Architecture Guide

Use this document to quickly onboard and understand the codebase layout, data models, and architectural patterns without scanning the entire workspace.

---

## 📂 Key Directory Layout

```
├── backend/
│   ├── alembic/           # Alembic DB migrations
│   ├── routers/           # FastAPI routers (auth, sessions, activity, payments, shop)
│   ├── utils/             # Signed URLs, file upload handlers
│   ├── config.py          # Pydantic Settings & ENV configurations
│   ├── database.py        # SQLAlchemy engine & session maker
│   ├── dependencies.py    # FastAPI dependencies (auth, active user, roles)
│   ├── models.py          # SQLAlchemy DB models (SQLite and PostgreSQL compatible)
│   ├── schemas.py         # Pydantic schemas with length/range validation caps
│   └── main.py            # FastAPI app initialization, seeding, and middleware
│
├── frontend/
│   ├── src/
│   │   ├── components/    # Reusable Vue 3 components (BaseCalendar, modals)
│   │   ├── views/         # Page components mapped by role (admin, teacher, student)
│   │   ├── stores/        # Pinia stores (auth, schedule, notifications, shop)
│   │   ├── router/        # Vue Router config with password-redirect gates
│   │   └── main.ts        # App bootstrap and Axios default configurations
```

---

## 🗄️ Database Models (`backend/models.py`)

* **Role**: Dictates permissions (`admin`, `teacher`, `student`).
* **User**: Core user entity. Fields include `hashed_password`, `must_change_password`, and `sessions_left`.
* **TeacherStudent**: Association table defining student-teacher assignments.
* **Session**: Scheduling records. Tracks state transitions (`scheduled`, `pending_teacher`, `pending_student`, `pending_admin`, `completed`, `cancelled`). Stores `version` (optimistic locking) and `counter_count`.
* **SessionProof**: Files uploaded by students or teachers to verify completed lessons.
* **Enrollment**: Tracks bought lessons and usage (`sessions_used`, `is_active`).
* **Payment**: Billing transaction logs.
* **Product**: Items in the school shop (lessons, books) with `stock` tracking.
* **Homework**: Tasks assigned by teachers. Contains file links.
* **Message**: Peer-to-peer messages in active session chats.
* **Notification**: In-app notifications with unread states.
* **ActivityLog**: Immutable audit logs of actions (deletions, state changes, etc.).

---

## ⚙️ Core Architectural Flow & Contracts

### 1. Authentication & Session Cookies
* **JWT Refresh Tokens**: Stored in a secure `HttpOnly` cookie at path `/auth` named `smc_rt`. The frontend does not store or read the refresh token in JavaScript.
* **Password Change Gate**: Newly seeded users have `must_change_password = True` and are immediately routed to `/change-password` upon authentication. No dashboards are accessible until changed.

### 2. Timezone-Aware Dates
* All database datetimes are stored as timezone-aware UTC.
* Naive dates are automatically coerced to UTC in `_validate_session_window` before evaluation.

### 3. Signed File Access (`backend/utils/signed_urls.py`)
* File uploads (proofs and homework) are stored under non-public directories (`uploads/proofs/`, `uploads/homework/`).
* Access is granted via **HMAC-SHA256 Signed URLs** with a 1-hour expiration.
* Signed URL format: `/uploads/proofs/{filename}?exp={unix_timestamp}&sig={signature}`.
* Signature binds the exact request path to prevent URL transplantation.

### 4. Image Upload Normalization (`backend/utils/uploads.py`)
* Automatically intercept uploads with extensions `jpg, jpeg, png, webp`.
* Resizes the image using Pillow (max edge 2000px, keeping aspect ratio).
* Re-encodes the image as `WebP`, strips metadata/EXIF, and writes it to disk with a secure `.webp` filename.

### 5. Session Validation & Operating Hours
* `_validate_session_window` checks:
  - Duration is between 15 and 240 minutes.
  - If proposed by a non-admin, the start/end time must fall within `WORKING_HOURS_START` and `WORKING_HOURS_END` (in UTC hours).
  - Admins bypass working hours.
