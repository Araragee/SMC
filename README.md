# SMC - Music School Management System

A premium, modern web application for managing music schools, scheduling classes, tracking enrollments, and purchasing lessons.

## Core Features

### 📅 Session & Scheduling Engine
* **Negotiation Workflow**: Students and teachers can propose, counter-propose, and approve sessions.
* **Mediation Gate**: Caps counter-proposals at 3, automatically handing off deadlocked sessions to admins.
* **Working Hours**: Enforces session bookings to fall within designated operating hours (e.g., 08:00 - 22:00) for non-admins.
* **Drag-and-Drop**: Interactive calendar week/month/day view toggles with drag-and-drop session rescheduling for admins.
* **Self-Cancellation**: Allows participants to self-cancel sessions up to 24 hours before they start.

### 🔒 Privacy & Security Hardening
* **HMAC-Signed Uploads**: All proof of lesson and homework files are protected via secure, 1-hour expiring signed URLs.
* **HttpOnly Auth**: Session refresh tokens are stored securely in HttpOnly cookies, protecting the system from XSS token theft.
* **Strict Validation**: All input endpoints enforce rigid character length limits, range limits, and password strength checks.
* **Password Expiry Gate**: Forced change-password redirects for newly seeded accounts on first-time login.

### 🛍️ Shop & Enrollments
* **Lesson Package Purchasing**: Students can buy packages and enroll in courses.
* **Atomic Balances**: Prevent concurrent booking race conditions using database-level atomic increment/decrement operators.
* **Inventory Management**: Track stock levels with automated low-stock warnings for admins.

### 🖼️ Automatic Upload Optimization
* **WebP Normalization**: Uploaded images are automatically converted to WebP format to save bandwidth and storage.
* **Downscaling**: Automatically downscales high-resolution images to a maximum edge size of 2000px, stripping metadata and EXIF data.

---

## Technical Stack

* **Backend**: FastAPI (Python), SQLAlchemy ORM, SQLite (Development) / PostgreSQL (Production), Pillow, Pydantic, Alembic.
* **Frontend**: Vue 3 (Composition API), Vite, TypeScript, Pinia (State Management), Tailwind CSS.
* **Infrastructure**: Docker, Docker Compose.

---

## Setup & Running

### Backend
1. Go to `backend/`.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up environment variables in `.env` (use `.env.example` as a template).
4. Run migrations:
   ```bash
   alembic upgrade head
   ```
5. Run the server:
   ```bash
   uvicorn main:app --reload
   ```

### Frontend
1. Go to `frontend/`.
2. Install dependencies:
   ```bash
   npm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```
