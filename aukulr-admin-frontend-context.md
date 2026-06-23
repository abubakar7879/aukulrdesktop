# Aukulr AI — Admin Dashboard: Context for Claude Code

## 1. Project Background

Aukulr AI runs a Python desktop launcher ("Aukulr Manager") that starts a stack
of local services on client machines. Licensing/activation is being redesigned
around a centralized model: a backend is the source of truth for which client
machines are allowed to run, and the desktop app calls a public API on startup
before launching anything.

Per the confirmed spec from the project supervisor: each client has a single
**user ID (hash value)** — there is no separate hardware ID / token pair. The
public endpoint (`api/{user_id}`) does no validation itself — it just returns
raw data (`currentDate`, `expiryDate`, `enabled`), and the **Python desktop
app** is responsible for comparing dates and checking the enabled flag.

This phase of work is the **admin web dashboard** — the internal tool staff
use to manage which clients are licensed.

## 2. Scope of THIS Build Phase

Build the **frontend admin dashboard only**, against a mock data layer.

**Explicitly deferred / NOT part of this phase:**
- Whether `userId` is admin-entered or system-generated at creation (open
  question for the supervisor — see §8)
- Real Postgres connection or schema migrations
- The public `api/{user_id}` endpoint consumed by the desktop app
- Any change to the Python desktop app

These are still being decided. Build the dashboard so swapping the mock data
layer for a real backend later requires touching only the data-access module,
not the UI components.

## 3. Tech Stack

- Next.js (App Router), TypeScript
- Tailwind CSS for styling
- Simple session-based auth (a single hardcoded admin credential via env var
  is fine for now — do not build multi-user roles/permissions yet)
- No real database yet — use an in-memory or local mock data module behind a
  clean service interface (see §6)

## 4. Required Screens & Features

1. **Login** — simple credential form, sets a session cookie, redirects to
   dashboard on success, shows an error on failure.
2. **Protected layout/shell** — nav, page title, logout button. Any dashboard
   route redirects to login if no valid session.
3. **Clients list** — table showing: name/label, user ID (masked/truncated if
   long), status badge (Enabled/Disabled), expiry date (flag visually if
   expired or expiring within 7 days), created date, row actions
   (Edit / Enable-Disable toggle / Remove).
4. **Add client** — form: name/label, expiry date. The user ID field should
   exist but as a **disabled/placeholder input** labeled "Assigned
   automatically" — do not implement real generation logic until it's
   confirmed whether this is system-generated or admin-entered (§8).
5. **Edit / client detail view** — view and edit name/expiry; show user ID
   as read-only/masked; show status.
6. **Enable / Disable** — toggle with a confirmation step.
7. **Remove client** — destructive action, must have a confirmation dialog.
8. **Summary cards** (optional, nice-to-have) — total clients, active,
   disabled, expired.

## 5. UX Constraints

- This is an internal tool, not a customer-facing product — prioritize clarity
  over visual flourish, but keep it clean and modern, not bare HTML defaults.
- Desktop-first (admin will use it from a laptop browser); mobile responsiveness
  is not a priority.
- Every destructive action (remove, disable) needs a confirmation step.
- Empty states, loading states, and error states should all be handled, not
  just the happy path.

## 6. Architecture Constraint — Mock Data Layer

Create a single module (e.g. `lib/clients.ts`) that exports the data-access
functions used by every page/component:

```ts
getClients(): Promise<Client[]>
getClient(id: string): Promise<Client | null>
addClient(input: { name: string; expiryDate: string }): Promise<Client>
updateClient(id: string, input: Partial<Client>): Promise<Client>
setClientStatus(id: string, enabled: boolean): Promise<Client>
deleteClient(id: string): Promise<void>
```

`Client` type:

```ts
type Client = {
  id: string;
  name: string;
  userId: string;              // hash value — uniquely identifies the client
  status: "enabled" | "disabled";
  expiryDate: string;          // ISO date
  createdAt: string;           // ISO date
};
```

Implement these functions against an in-memory array (seeded with a handful of
fake clients) for this phase. No UI component should ever read/write the mock
array directly — always go through this module, so it's a one-file swap later.

## 7. Step-by-Step Build Sequence

Work through these in order; confirm each step before moving to the next:

1. Scaffold the Next.js + TypeScript + Tailwind project.
2. Build the login page and session handling (hardcoded admin credential from
   env var, simple cookie-based session, protected-route middleware/wrapper).
3. Build the dashboard shell: layout, nav, logout.
4. Build `lib/clients.ts` mock data module with seeded fake data.
5. Build the clients list page, wired to `getClients()`.
6. Build the Add Client form, wired to `addClient()`.
7. Build Enable/Disable toggle (with confirmation) and Remove (with
   confirmation), wired to `setClientStatus()` / `deleteClient()`.
8. Build the client detail/edit view, wired to `getClient()` / `updateClient()`.
9. Add empty/loading/error states across the above.
10. (Optional) Add summary stat cards on the dashboard home.

## 8. Notes for Future Phases (do not build now)

- Swapping `lib/clients.ts` from mock to the real `api/{user_id}` GET endpoint
  backed by Postgres.
- **Open question for the supervisor**: is `userId` (the hash) generated by
  the system when a client is added, or entered manually by the admin? This
  affects whether the Add Client form's user-ID field is read-only or an
  input.
- Audit logging of admin actions.

**Separately (Python desktop app, not this phase):** the supervisor confirmed
the expiry-cleanup behavior (delete everything except the database and the
Node backend's `public/` folder) is a real requirement, not legacy code to
remove. That's being scoped precisely before it's implemented — it does not
affect this dashboard build.
