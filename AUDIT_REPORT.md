# Music School Platform - Audit Report & Remediation Plan

## 1. Identified Issues

### Stability & Security
*   **Fragile Database Schema Management:** Backend uses manual `ALTER TABLE` in `startup_event`. This is non-idempotent and risky for production.
*   **Hardcoded Secrets:** Fallback `SECRET_KEY` in `main.py` and hardcoded API URLs (e.g., `http://localhost:8000`) in frontend components (e.g., `StudentRecords.vue`).
*   **Inconsistent ID Types:** Backend uses `Integer` IDs, while frontend types/stores often use `string`, leading to manual casting and potential bugs.
*   **Monolithic Backend:** `main.py` is bloated and contains all logic, making it hard to maintain. It should be refactored into modular routers.

### Broken Links & Missing Navigation
*   **Teacher Sidebar:** Links to `/teacher/students`, `/teacher/instruments`, and `/teacher/payments` are in the UI but lead to a `PlaceholderView` as they are not defined in the router.
*   **Student Sidebar:** Link to `/student/homework` is in the UI but missing from the router.
*   **Auth Logic:** Some redirections in the router redirect based on `auth.userRole` which might be null during initial load.

### Incomplete Functions & Dashboards
*   **Missing Modules:** "Instrument Shop" and "Payments" mentioned in the design/sidebar are not implemented (no models, no routers).
*   **Dashboard Placeholders:**
    *   **Admin:** "View All Activity" button is dead.
    *   **Teacher:** "View All Roster" and "Enroll New" are non-functional.
    *   **Student:** "Manage Subscription" and "Notice Board" links are dummy.
*   **Homework Workflow:** Backend supports homework, but there's no dedicated student view to list and submit them.

---

## 2. Remediation Plan

### Phase 1: Foundation, Refactoring & Security
*   **Alembic Integration:** Implement proper database migrations.
*   **Backend Refactor:** Split `main.py` into domain-specific routers (Auth, Users, Sessions, Shop, etc.).
*   **Environment Configuration:** Ensure all secrets and URLs are strictly pulled from `.env`.
*   **Type Standardization:** Standardize ID handling as integers throughout the frontend stores.

### Phase 2: Navigation & Routing Fixes
*   **Router Registration:** Add all missing routes for Teacher and Student modules.
*   **View Scaffolding:** Create functional base views for Students, Instruments, Payments, and Homework to replace `PlaceholderView`.

### Phase 3: Core Module Implementation
*   **Instrument Shop:** Implement `InstrumentProduct` models, checkout logic, and frontend shop UI.
*   **Payments & Subscriptions:** Integrate payment tracking and subscription management (Credits/Enrollment).

### Phase 4: Dashboard Polish & Feature Completion
*   **Interactive Dashboards:** Wire up all "Quick Assign", "Enroll New", and "View All" buttons to functional logic.
*   **Homework Portal:** Build a full homework management system for teachers to assign and students to track/upload.

---

## 3. Scheduled Task Prompt

**Task Prompt:**
> Refactor the Music School Platform for production readiness and feature parity.
> 1. **Stability:** Implement Alembic migrations, refactor `main.py` into modular routers, and move all hardcoded secrets/URLs to environment variables.
> 2. **Navigation:** Fix all broken/placeholder links in the Teacher and Student sidebars by implementing the missing routes and views.
> 3. **Missing Features:** Build out the "Instrument Shop" and "Payments" modules from backend to frontend.
> 4. **Dashboard Completion:** Ensure all interactive buttons on the Admin, Teacher, and Student dashboards are functional, and implement the full Homework management workflow.
