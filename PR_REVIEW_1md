# PR Review — Expiry Defang + Admin Dashboard (Step 2)

## Changes in this PR

### 1. `ppe_manager_lite.py` — Neutralise destructive expiry cleanup

**Problem:** `perform_expiry_cleanup()` called `shutil.rmtree()` and `item.unlink()` on
the contents of `redis_dir` and `orchestrator_dir` when the online date passed `expiry_date`.
This was a silent, irreversible disk wipe triggered by three free public time APIs and a
locally-editable date string.

**Fix:**
- Replaced the entire deletion loop with a single `log.warning(...)` — no files are touched.
- Updated the expiry error dialog message to match the full client: *"Application expired —
  services were not started. Please contact support."*
- The date-check gate itself is unchanged; the expiry condition still blocks startup.

**Files changed:** `ppe_manager_lite.py`

---

### 2. `ppe_manager.py` — Switch from date-expiry to license API

**Problem:** Same expiry-via-public-time-API pattern; additionally the `expiry_date` was
a hardcoded string in the config, editable by anyone with master-password access.

**Fix:** Replaced the `expiry_date` + `DATETIME_APIS` approach with a call to
`license.aukulr.ai/api/license/validate`. The desktop app now sends a `license_token`
to a centrally controlled endpoint; the server is the source of truth for validity.

**Files changed:** `ppe_manager.py`

---

### 3. `aukulr-admin-dashboard/` — Admin dashboard: Step 2 (Login + Session)

**What was built (Step 2 of 10 per spec):**

| File | Purpose |
|---|---|
| `lib/session.ts` | JWT encrypt/decrypt via `jose`; `createSession`, `deleteSession`, `verifySession` |
| `app/actions/auth.ts` | `login` and `logout` Server Actions |
| `proxy.ts` | Route protection (Next.js 16 renames `middleware.ts` → `proxy.ts`) |
| `app/login/page.tsx` | Login form — `useActionState`, error display, loading state |
| `app/page.tsx` | Root redirects to `/login` |
| `.env.local` | *(git-ignored)* Admin credentials + session secret |

**Behaviour verified (curl against live dev server):**
- `GET /` → `307 /login`
- `GET /login` → 200, form renders
- `POST /login` wrong creds → 200 + "Invalid username or password" error
- `POST /login` correct creds → `303 /dashboard` + `Set-Cookie: session=<JWT>; HttpOnly; SameSite=lax`
- `GET /dashboard` without cookie → `307 /login` (proxy fires)
- `GET /dashboard` with valid cookie → passes through (404 expected — page not built yet)
- `GET /login` with valid cookie → `307 /dashboard` (proxy bounces already-authenticated users)

**Not built yet (Steps 3–10):** dashboard shell, client list, add/edit/enable/disable/remove.

---

## What was NOT changed

- `build_exe.py`, `build_exe_lite.py`, `AukulrManager.spec` — untouched.
- Real Postgres, public `api/{user_id}` endpoint, mock data layer — deferred per spec.
