# SMC Completion Plan

## Phase 1 — Postgres Migration
> Swap SQLite → Postgres. No feature work.

- [ ] Add `psycopg2-binary` to `requirements.txt`
- [ ] Provision Postgres (local or Docker via `docker-compose.yml`)
- [ ] Set `DATABASE_URL=postgresql+psycopg2://...` in `.env`
- [ ] Run `alembic upgrade heads`
- [ ] Run `seed_fresh.py`
- [ ] Update `start.sh` — remove `/tmp` copy trick
- [ ] Smoke test: login, create session, check notifications

---

## Phase 2 — 2FA Frontend
> Wire existing TOTP backend (`/auth/2fa/*`) to frontend UI.

### Backend (already done)
- [x] `POST /auth/2fa/setup`
- [x] `POST /auth/2fa/enable`
- [x] `POST /auth/2fa/disable`
- [x] `POST /auth/2fa/verify`

### Frontend (all missing)
- [ ] `auth.ts` — handle `challenge_token` response from `/login`, route to verify step
- [ ] `Login.vue` — show `TwoFAVerifyModal` when `challenge_token` returned
- [ ] `TwoFAVerifyModal.vue` (new) — TOTP code input, calls `/auth/2fa/verify`
- [ ] `TwoFASetupModal.vue` (new) — show QR code + confirm code input, calls `/auth/2fa/enable`
- [ ] Settings section (all 3 roles) — enable/disable 2FA toggle, trigger setup modal

---

## Phase 3 — Bulk Session Ops
> Admin selects multiple sessions → bulk action.

### Backend (missing)
- [ ] `POST /sessions/bulk-action` — `{ session_ids: int[], action: "approve"|"cancel"|"complete" }`
- [ ] `GET /sessions/stats` — counts per status for dashboard
- [ ] `BulkActionRequest` schema in `schemas.py`

### Frontend (missing)
- [ ] `admin/Schedule.vue` — checkbox column on session list
- [ ] `admin/Schedule.vue` — bulk action toolbar (shows when ≥1 selected)
- [ ] `admin/Dashboard.vue` — wire stats cards to `GET /sessions/stats`
- [ ] `schedule.ts` store — `bulkAction()` fn + `fetchStats()` fn

---

## Phase 4 — Shop Fulfillment UI
> Admin order management UX polish. Backend already complete.

### Backend (already done)
- [x] `pending → approved → fulfilled → cancelled` flow
- [x] Stock deduction on approve
- [x] Push notifications on status change

### Frontend (missing)
- [ ] `admin/Instruments.vue` — status filter tabs (All / Pending / Approved / Fulfilled)
- [ ] `admin/Instruments.vue` — order detail modal (items, student info, action buttons + confirm dialog)
- [ ] `admin/Instruments.vue` — low stock badge on product cards (warn at ≤ 3)
- [ ] `teacher/Instruments.vue` — order history with status tracking
- [ ] `ShopView.vue` — student order history with status tracking

---

## Timeline (estimate)

| Phase | Scope | Est. | Status |
|---|---|---|---|
| 1 — Postgres | Infra only, no UI | 1-2 hrs | ⬜ Not started |
| 2 — 2FA Frontend | Modal + auth store flow | 3-4 hrs | ⬜ Not started |
| 3 — Bulk Ops | Backend + admin UI | 2-3 hrs | ⬜ Not started |
| 4 — Shop UI | Frontend only | 2-3 hrs | ⬜ Not started |
