# SMC Music Clinic - Remediation Plan & Task Prompt

This document summarizes the findings from the system audit and provides a roadmap for stabilizing and completing the platform.

---

## 1. Audit Findings

### 🛡️ Stability & Technical Debt
*   **Database Migrations:** The backend relies on manual `ALTER TABLE` statements in `main.py`. This is fragile and lacks versioning.
*   **Hardcoded Configuration:** JWT `SECRET_KEY` and CORS `allow_origins` are hardcoded in the source code rather than using environment variables.
*   **Type Mismatch:** Entity IDs (e.g., `user_id`) are typed as `string` in many frontend interfaces but are `int` in the backend and database, leading to potential runtime casting errors.
*   **Directory Naming:** (Resolved) Historical references to `@typscript` alias and misspelled directories have been cleaned up in the current build, but remaining references should be checked in legacy scripts.

### 🔗 Broken Links & Navigation
*   **Admin Ledger:** The sidebar contains a link to "Ledger" (`/admin/payments`), but the route is not defined in the router, and the component is missing.
*   **Placeholder Views:** Routes such as Teacher Payments or specific Student views sometimes fallback to `PlaceholderView.vue`.
*   **Inactive UI Elements:** The "View All Activity" button on the Admin Dashboard is a placeholder that only displays a toast notification.

### 🏗️ Incomplete Features
*   **Activity Logging:** No database-backed activity log exists to track administrative changes.
*   **Shop Fulfillment:** The Instrument Shop lacks a complete workflow for admins to manage stock levels and fulfill orders once approved.
*   **Payment Tracking:** While payment models exist, the UI lacks detailed status history and printable receipts.

---

## 2. Implementation Roadmap

### Phase 1: Stability & Security
1.  **Initialize Alembic:** Move all schema definitions and manual migrations from `main.py` to Alembic.
2.  **Environment Variables:** Implement `pydantic-settings` to manage secrets and CORS configurations.
3.  **Type Standardization:** Ensure all entity IDs are treated as `number` across the entire frontend stack.

### Phase 2: Navigation & Core Admin
1.  **Build Ledger:** Implement `AdminPayments.vue` and register the `/admin/payments` route.
2.  **Activity Log:** Create a functional Activity Log view and connect it to the Dashboard "View All Activity" button.
3.  **Router Audit:** Ensure 1:1 mapping between `SidebarNav.vue` and `router/index.ts`.

### Phase 3: Feature Polish
1.  **Shop Completion:** Finalize the fulfillment UI for admins and add stock level notifications.
2.  **Payment History:** Add transaction status tracking and success/fail states to the payments module.

---

## 3. Task Prompt for Future Implementation

**Task: SMC Platform Stability & Feature Remediation**

**Objective:** Address technical debt, fix broken navigation, and complete missing administrative modules.

**Requirements:**
1.  **Technical Debt:** Standardize entity IDs as `number` across all frontend types and stores.
2.  **Navigation:** Implement the missing `AdminPayments.vue` (Ledger) view and register the `/admin/payments` route. Replace the Admin Dashboard's "View All Activity" toast with a functional activity log page.
3.  **Stability:** Initialize **Alembic** for backend migrations. Move hardcoded secrets (JWT, CORS) to environment variables using `pydantic-settings`.
4.  **Refactoring:** Remove manual `Base.metadata.create_all` and seeding logic from `backend/main.py` into standalone scripts or migrations.
5.  **Audit:** Ensure no sidebar links point to `PlaceholderView.vue` and all dashboard stats reflect live database data.

**Verification:** Confirm all sidebar links navigate to functional pages and the frontend build completes without type errors (`npm run build`).
