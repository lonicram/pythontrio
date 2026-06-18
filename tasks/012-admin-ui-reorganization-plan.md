# Admin UI Reorganization Plan

## 1. Overview

This plan replaces the single-card profile admin page with a proper `/admin` console built around a left sidebar and a content area that swaps between a users-list view and a user-detail view. The list view drives discovery (no more typing IDs by hand), and the detail view preserves today's transition workflow exactly. Everything runs in one HTML document with vanilla JS toggling view visibility — no router, no build step. The existing transition/badge logic is retained and reused; only the navigation shell and list view are new.

## 2. Architecture Decision

The new `/admin` route belongs in `app/main.py`, not in `user_profiles.py`. Reasoning: the admin shell is a top-level application concern that will host multiple future domains (Portfolios, Assets), so coupling it to the user-profile router would violate Single Responsibility and create a misleading ownership boundary. Serving it from `main.py` keeps it a sibling of `/`, `/health`, and the `/static` mount, all of which are cross-cutting app concerns. On the client, JS follows a thin separation: a small view-controller (show/hide) plus per-view render functions, keeping each function single-purpose (SRP) and avoiding any framework (KISS).

## 3. Implementation Steps

1. **Remove the old route and assets.** In `app/routers/user_profiles.py`, delete the `/admin` route, the `FileResponse` import, the `os` import, and the `_ADMIN_HTML` constant. Delete `app/static/profile_admin.{html,js,css}`.

2. **Add the `/admin` route in `app/main.py`.** Add `from fastapi.responses import FileResponse`, define a module-level `_ADMIN_HTML = os.path.join(_static_dir, "admin.html")`, and register `@app.get("/admin", response_class=FileResponse, include_in_schema=False)` returning `FileResponse(_ADMIN_HTML, media_type="text/html")`. Reuse the existing `_static_dir` and `/static` mount.

3. **Create `app/static/admin.html`.** A two-column layout: a `<nav class="sidebar">` with one "Users" item, and a `<main class="content">` holding two sibling sections — `#usersView` (a `<table>` with a `<tbody id="usersTableBody">`) and `#detailView` (a "← Back to Users" link, email/username fields, `#statusBadge`, the four transition buttons reusing IDs `btnVerify/btnSuspend/btnReinstate/btnDelete`, and `#errorBanner`). Link `/static/admin.css` and `/static/admin.js`.

4. **Create `app/static/admin.js`.** Port the existing `ALLOWED` map, `showError/clearError`, `renderProfile`, and `doTransition` functions unchanged. Add: `showView(name)` toggling a `.hidden` class on the two view sections; `loadUsers()` fetching `GET /user-profiles/` and rendering rows (ID, email, username, status badge, "Manage" button calling `openDetail(id)`); `openDetail(id)` fetching `GET /user-profiles/{id}`, calling `renderProfile`, and switching to the detail view; a back handler returning to the list (and re-running `loadUsers()` so the table reflects any change). Initialize by showing the users view on load.

5. **Create `app/static/admin.css`.** Add sidebar/content grid layout and a `.hidden { display: none }` utility for view switching. Carry over the badge palette (`.badge-new/verified/suspended/deleted`), transition-button colors, banner, and disabled-button styles from `profile_admin.css`; add table styling for the list.

## 4. Data Flow

On load, `admin.js` calls `loadUsers()` → `GET /user-profiles/` → renders one table row per profile, each carrying its `id`. Clicking "Manage" calls `openDetail(id)` → `GET /user-profiles/{id}` → `renderProfile()` populates fields, sets the badge class from `status`, and toggles button `disabled` state via the `ALLOWED` map, then `showView("detail")`. A transition button calls `doTransition(target)` → `POST /user-profiles/{id}/transition` with `{ target }`; on success the response profile re-renders the badge and buttons in place, on 400 the error banner shows `detail`. "← Back to Users" calls `showView("users")` and refreshes the list.

## 5. Concerns & Mitigations

- **Stale list after transition:** re-fetch via `loadUsers()` on every "Back" navigation rather than caching rows.
- **`currentProfileId` source:** `openDetail` must set it from row data (not a text input) so `doTransition` targets the right profile.
- **Large user lists:** `GET /user-profiles/` is unpaginated — fine for a demo; note as future work.
- **Dynamic row handlers:** bind "Manage" click handlers in JS rather than inline `onclick` strings to avoid escaping issues with email values.
- **Old path references:** confirm no tests reference `/user-profiles/admin` or `profile_admin.*` before deleting.

---

## Files touched

| File | Action |
|------|--------|
| `app/routers/user_profiles.py` | Remove `/admin` route, `FileResponse`/`os` imports, `_ADMIN_HTML` constant |
| `app/main.py` | Add `GET /admin` route serving `admin.html` |
| `app/static/admin.html` | Create — two-column shell (sidebar + content area) |
| `app/static/admin.js` | Create — view controller + list/detail logic |
| `app/static/admin.css` | Create — layout + carried-over badge/button/banner styles |
| `app/static/profile_admin.html` | Delete |
| `app/static/profile_admin.js` | Delete |
| `app/static/profile_admin.css` | Delete |
