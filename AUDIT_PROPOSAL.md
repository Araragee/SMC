# System Audit & Optimization Proposal

This document outlines the findings of a system-wide audit of the Music School platform and proposes optimizations to enhance security, maintainability, and architectural integrity.

---

## 1. Identified Issues

### 🛡️ Security
| Issue | Location | Impact |
| :--- | :--- | :--- |
| **Logic Backdoor** | `backend/routers/users.py` | Critical. The login logic allows a bypass if a specific string is appended to the password. |
| **Fallback Secrets** | `backend/dependencies.py` | High. Hardcoded JWT `SECRET_KEY` fallback posing a risk if env vars are missing. |
| **Hardcoded CORS** | `backend/main.py` | Medium. `allow_origins` is hardcoded to localhost, complicating production deployment. |

### 🛠️ Technical Debt
| Issue | Location | Impact |
| :--- | :--- | :--- |
| **Misspelled Directory** | `frontend/src/typscript/` | Low. Misspelled "typscript" (missing 'e') used across all stores and components. |
| **Type Inconsistency** | `frontend/src/types/index.ts` | Medium. IDs are defined as `string` in frontend types but are `int` in backend and DB. |
| **Manual Migrations** | `backend/main.py` | Medium. Manual `ALTER TABLE` statements in startup event are fragile and not versioned. |
| **Hardcoded URLs** | `backend/routers/sessions.py` | Medium. `http://localhost:8000` is hardcoded for file uploads and proof images. |

### 🏗️ Infrastructure & DevOps
| Issue | Location | Impact |
| :--- | :--- | :--- |
| **Build-time Env Vars** | `frontend/Dockerfile` | Medium. `VITE_API_BASE_URL` is baked in at build time, preventing configuration at runtime. |
| **Direct SQLite Path** | `docker-compose.yml` | Low. Hardcoded path for SQLite DB limits flexibility in multi-stage environments. |

---

## 2. Optimization Proposals

### 1. Architectural Improvements
- **Standardize Configuration:** Implement `pydantic-settings` in the backend to manage environment variables and secrets consistently.
- **Adopt Alembic:** Replace the manual migration logic in `main.py` with Alembic for robust, versioned database schema changes.
- **Runtime Frontend Configuration:** Modify the Nginx setup to serve a dynamic `env-config.js` or use a placeholder replacement strategy to allow `API_BASE_URL` to be changed without re-building the Docker image.

### 2. Code Quality & Consistency
- **Rename Directory:** Rename `frontend/src/typscript/` to `frontend/src/typescript/` and update the Vite alias and all related imports.
- **Unified ID Mapping:** Standardize ID types across the stack (either consistently string or consistently number) to prevent casting bugs in Pinia stores.
- **Refactor Auth Store:** Standardize the user role extraction logic in `auth.ts` to reduce complexity and potential for `undefined` errors.

### 3. Security Hardening
- **Remove Backdoors:** Eliminate the "notreallyhashed" bypass logic in the user login endpoint.
- **Password Policies:** Implement minimum password complexity requirements during user creation and profile updates.
- **Secure File Serving:** Use relative paths for file URLs and let the frontend or a proxy handle the base URL.

### 4. UI/UX Enhancements
- **Form Validation:** Introduce `VeeValidate` or `Zod` on the frontend to provide immediate feedback before hitting the API.
- **Loading States:** Standardize skeleton loaders across all views to improve perceived performance during data fetching.

---

## 3. Implementation Roadmap (Draft)

1. **Phase 1: Security & Hygiene** (Remove backdoors, fix misspelling, fix hardcoded URLs).
2. **Phase 2: Configuration & Infra** (Pydantic Settings, Runtime Env Vars for Frontend).
3. **Phase 3: Database & Logic** (Alembic Integration, Type Standardization).
