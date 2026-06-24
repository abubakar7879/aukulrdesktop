# PR Review — Admin Dashboard Shell + Client List

## Summary
This PR adds the protected dashboard experience that follows the login flow. It introduces the dashboard shell, the first client-list experience, and a shared mock data layer that keeps the UI decoupled from storage details.

## What changed

### 1. Protected dashboard shell
- Added a dashboard layout with a top navigation bar and logout action.
- Enforced session-based protection so authenticated users can access dashboard routes while unauthenticated users are redirected to login.
- Kept the shell simple and clean, which fits the internal-admin-tool use case.

### 2. Client list experience
- Built the main dashboard page that renders the client list.
- Added row actions for editing, enabling/disabling, and removal.
- Presented the list in a clear table layout with status and expiry visibility.

### 3. Shared mock data layer
- Introduced a dedicated mock client data module so pages/components do not touch state directly.
- Seeded the module with representative client records to support UI development before backend integration.

## What looks good
- The route protection is straightforward and easy to reason about.
- The mock data abstraction is a strong fit for the current phase and should make future backend replacement much easier.
- The dashboard shell is clean and consistent with the rest of the admin UI.

## Recommended follow-ups
- Add explicit loading and error states around the client list once data fetching becomes more realistic.
- Keep the current mock data module as the only storage boundary so the rest of the app remains stable when the real backend arrives.
- Consider server-side pagination or filtering later if the client count grows beyond a small internal dataset.

## Notes for the team
This is a solid foundation for the next phase of the admin portal. The implementation is aligned with the spec and gives the team a clear path toward CRUD operations and richer management workflows.
