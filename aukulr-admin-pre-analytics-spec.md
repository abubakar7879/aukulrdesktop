# Aukulr Admin Portal — Feature Spec: Post-MVP, Pre-Analytics

Act as a Senior Product Designer / SaaS Admin Dashboard Architect. Use this
spec to design and implement the features below for the Aukulr licensing
portal. Do not write any analytics code yet — that section is a roadmap only.

## Current Build State

| Step | Status |
|---|---|
| 1 — Scaffold | ✅ |
| 2 — Login + session | ✅ |
| 3 — Dashboard shell | ✅ |
| 4 — `lib/clients.ts` mock data | ✅ |
| 5 — Clients list | ✅ |
| 6 — Add client form | next |
| 7 — Enable/Disable + Remove | after |

This spec covers what comes **after step 7** — replacing the vague "empty
states" / "optional summary cards" placeholders with a properly designed set
of features, in this order:

8. Client Details / Edit page
9. Search
10. Filters
11. Dashboard Summary Cards
12. Audit Information (MVP version)
13. Empty / loading / error states (apply across all of the above)

Analytics is **not** in this build phase — see the roadmap section at the end.

## Data Model Correction (read this before designing anything)

There is **no separate Hardware ID or License Token field.** Each client has
exactly one identifier:

```ts
type Client = {
  id: string;
  name: string;
  userId: string;        // hash of the client machine's CPU ID — single identifier
  status: "enabled" | "disabled";
  expiryDate: string;    // ISO date
  createdAt: string;     // ISO date
  notes?: string;
};
```

`userId` is produced by a separate onboarding script run on the client's
machine and is **entered manually by the admin** — it is not auto-generated
by this portal. Any UI element referencing "Hardware ID," "Token," or "Token
regeneration" should be removed from designs — they don't exist in this
architecture.

---

## Feature 8: Client Details / Edit Page

**Purpose:** the single place to view and manage everything about one client.
**Business value:** reduces support time — one screen answers "is this client
active, when do they expire, what's their identifier."

**Layout (top to bottom or grouped in cards):**
- **Header**: client name (editable inline), status badge (Enabled/Disabled),
  expiry badge if expired/expiring within 7 days.
- **Identity section**: `userId` (editable text field — changing it
  effectively re-points the license to a different machine, so this edit
  should require a confirmation step, not save silently), Created date
  (read-only), Last Updated (read-only).
- **License section**: Expiry date (editable date picker), Status toggle
  (Enable/Disable, with confirmation).
- **Notes**: free-text field, editable, optional.
- **Danger Zone** (visually separated, e.g. red-bordered card at the bottom):
  Remove Client — requires typed confirmation (e.g. type the client name) or
  a confirmation modal, not a single click.

**Editable fields:** name, userId, expiryDate, status, notes.
**Read-only fields:** createdAt, lastUpdated (id is internal, not shown).

**States:** loading skeleton while fetching; not-found state if the client
ID in the URL doesn't exist; save-success toast; save-error inline message
without losing the user's unsaved edits.

**Edge cases:** editing `userId` to a value that collides with another
client's — should be blocked with a clear error, not silently overwritten.

---

## Feature 9: Search

**Purpose:** find a client quickly once the list grows past a quick scan.
**Location:** a single search input above the clients table, full-width on
mobile, ~320px on desktop, left-aligned next to the Add Client button.
**Placeholder:** "Search by name or ID…"
**Searchable fields:** `name`, `userId` (partial match, case-insensitive).
**Behavior:** instant (debounced ~250–300ms) against the in-memory mock list
for now — this stays cheap with a small client count; flag in the code that
this should move to a server-side query once the client count or dataset
size makes client-side filtering noticeably slow.
**Empty results:** show a clear "No clients match '...'" message with a
"Clear search" action, not just a blank table.

---

## Feature 10: Filters

**Purpose:** quickly narrow the list to a specific status without typing.
**Pattern:** a row of filter chips/tabs above the table — All / Active /
Disabled / Expired / Expiring Soon — not a dropdown, since there are only 5
options and chips make the active filter visually obvious at a glance.
**Desktop:** horizontal row of chips, each showing a count badge (e.g.
"Active (12)").
**Mobile:** horizontal-scroll chip row, same chips, smaller padding.
**Interaction with search:** filters and search combine with AND logic — a
filter narrows by status, search narrows further by name/ID within that set.
**Empty state per filter:** e.g. "No expired clients" rather than a generic
empty table when a filter legitimately has zero matches.

---

## Feature 11: Dashboard Summary Cards

**Purpose:** an at-a-glance status check before scanning the full table.
**Metrics:** Total Clients, Active, Disabled, Expired, Expiring Soon (next 7
days).
**Arrangement:** single row of 5 cards on desktop, 2-column grid on mobile.
**Hierarchy:** Total is visually largest/leftmost; the other four are equal
size.
**Color coding:** Active — green accent; Disabled — gray/neutral; Expired —
red; Expiring Soon — amber/orange; Total — neutral brand color.
**Clickable:** yes — clicking a card applies the matching filter from
Feature 10 (e.g. clicking "Expired" sets the filter chip to Expired). Total
clears all filters.
**States:** loading skeleton per card; cards still render at 0 if a category
is empty (don't hide a card just because its count is zero).

---

## Feature 12: Audit Information (MVP)

**Purpose:** answer "who changed what, and when" for support and
accountability.
**Events to log:**
- Client created
- Client enabled / disabled
- Expiry date changed (old value → new value)
- User ID changed (old value → new value)
- Notes updated
- Client removed

**Where it appears (MVP):** on the Client Details page only, as a simple
reverse-chronological list ("Sept 3 — Expiry changed from Aug 1 to Sept 30 —
by admin"). A separate global audit log page is a future enhancement, not
MVP.

**Entry format:** timestamp, actor (admin username/email), action, and
before→after values where applicable.

**Retention (MVP recommendation):** keep all entries indefinitely for now —
volume will be low; revisit retention policy only if/when entry count becomes
a real storage concern.

---

## Feature 13: Empty / Loading / Error States

Apply consistently across the clients list, client details page, and summary
cards:
- **Empty:** no clients at all yet → friendly message + prominent "Add your
  first client" CTA, not a blank table.
- **Loading:** skeleton placeholders matching the shape of the eventual
  content (card/row skeletons), not a generic spinner.
- **Error:** inline message with a "Retry" action; never lose user-entered
  form data because of a failed save.

---

## Feature 14 (Roadmap Only — Do Not Build Yet): Analytics

This is a **future phase**, not part of this build. Capture it now only so
the data model doesn't need reworking later.

**Useful metrics for a licensing business:**
- Monthly client growth (new clients added per month)
- Renewal rate (expiry extended vs. allowed to lapse)
- Time-to-expiry distribution (how many clients expire in 30/60/90 days)
- Admin activity volume (actions per admin, from the audit log)

**Probably not useful here:** anything resembling product usage analytics
(this portal manages licenses, not end-user behavior) — avoid scope creep
into building a generic BI tool.

**Future layout direction:** KPI cards at top (mirroring the summary cards),
one trend chart (clients over time), one table (upcoming expirations), and a
CSV export action. No build work on this until Features 8–13 are complete
and stable in production use.
