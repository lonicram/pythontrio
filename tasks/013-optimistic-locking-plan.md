# Optimistic Locking — Implementation Plan

## 1. Overview

This plan adds optimistic concurrency control to `UserProfile` lifecycle transitions so two concurrent admins can never silently overwrite each other (the "resurrect a deleted account" lost-update bug). The mechanism is a single `version` integer column registered via SQLAlchemy's `version_id_col`, which makes every `UPDATE` carry `WHERE id = :id AND version = :expected` and auto-increment the version. A stale write touches zero rows and raises `StaleDataError`, which the transition router translates into a clean `HTTP 409 Conflict` carrying current state. The admin UI caches the version as a compare-and-swap token, submits it on each transition, and surfaces 409 conflicts distinctly from 400 business-rule rejections.

## 2. Architecture Decision

The concurrency guarantee lives in the database row, not application memory, and is enforced declaratively by the ORM rather than by hand-written checks scattered across write paths — this is the Single Responsibility and DRY win over per-endpoint conditional `UPDATE`s. The service keeps owning read-validate-write of the state machine (`ALLOWED_TRANSITIONS` + side effects) and the router keeps owning HTTP translation, preserving the existing "service builds, caller commits" boundary unchanged. Critically, `StaleDataError` fires at flush/commit time (in the router), not during the service call, so it must be caught around `db.commit()` — never inside the service. This keeps the 400-vs-409 distinction architecturally clean: business-rule failure validated up front, concurrency failure detected at write.

## 3. Implementation Steps

**Step 1 — Model** (`app/models/user_profile.py`)
Add `version` column and mapper config:
```python
from sqlalchemy import Integer

version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
__mapper_args__ = {"version_id_col": version}
```
Add `version` to the class docstring `Attributes`. This is the entire concurrency mechanism — no other write path changes.

**Step 2 — Migration** (`alembic/versions/<rev>_add_profile_version.py`, `down_revision='c00d7ae13f11'`)
```python
def upgrade() -> None:
    op.add_column(
        'user_profiles',
        sa.Column('version', sa.Integer(), nullable=False, server_default='1')
    )

def downgrade() -> None:
    op.drop_column('user_profiles', 'version')
```
Generate stub with `alembic revision -m "add profile version"` then fill the body manually.

**Step 3 — Router + schema**
- `app/schemas/responses.py`: add `version: int` to `UserProfileResponse`.
- `app/routers/user_profiles.py`:
  - `ProfileTransitionRequest` keeps only `target: ProfileStatus` — no `expected_version` field. The lock is enforced entirely server-side by SQLAlchemy's `version_id_col`; the client never needs to send a token.
  - Wrap `db.commit()` in `try/except sqlalchemy.orm.exc.StaleDataError`: call `db.rollback()`, re-fetch the current profile in a fresh query (not `db.refresh` on the rolled-back instance), return `HTTPException(409)` with body `{"detail": "...", "current_status": "...", "current_version": N}` and `Retry-After: 1` header.
  - Keep `IllegalTransitionError → 400` and `ProfileNotFound → 404` as separate except clauses around the service call, before the commit.

**Step 4 — Admin UI HTML** (`app/static/admin.html`)
In the detail panel:
- Add `<span id="versionBadge" class="version-badge"></span>` near `#stateIndicator`.
- Add a separate `<div id="conflictBanner" class="conflict-banner hidden">` containing a `<span id="conflictMsg"></span>` and a `<button class="btn-reload" onclick="reloadProfile()">Reload</button>`.

**Step 5 — Admin UI JS + CSS**
`app/static/admin.js`:
- `renderProfile(p)`: update `#versionBadge` to `v${p.version}`; hide `#conflictBanner`.
- `doTransition(target)`: POST body stays `{ target }` only — no version sent.
- Add 409 handling: parse the 409 body's `current_status` and `current_version`, set `#conflictMsg` to "Profile changed to `{current_status}` (v{current_version}) while you were deciding.", show `#conflictBanner`, hide `#errorBanner`.
- Add `reloadProfile()`: calls `openDetail(currentProfileId)` — re-fetches, re-renders. The state machine re-evaluates on fresh state.
- Keep `#errorBanner` (amber) for 400s only — two banners, two distinct failure modes.

`app/static/admin.css`:
- `.version-badge`: `font-family: monospace; font-size: 0.8rem; color: #94A3B8; margin-left: 0.5rem;`
- `.conflict-banner`: `border-left: 4px solid #DC2626; background: #FEF2F2; color: #991B1B;` (red — visually distinct from the amber 400 banner)
- `.btn-reload`: small inline button inside the conflict banner

---

## 4. Data Flow

On detail load, the UI `GET`s the profile and displays `v${version}` in `#versionBadge` (read-only — never sent back). On a transition the UI `POST`s `{target}` only; the router calls `ProfileLifecycleService.transition()` (reads the current row — including its DB `version` — validates against `ALLOWED_TRANSITIONS`, runs side effects, sets status), then `db.commit()`. At flush SQLAlchemy emits `UPDATE user_profiles SET status=?, version=<new> WHERE id=? AND version=<loaded>` and bumps `version`; a zero-row match raises `StaleDataError`, caught by the router, which rolls back, re-fetches, and returns 409 with fresh `current_status`/`current_version`. The UI's Reload button re-fetches, re-renders, and re-runs the state machine on current state — which may now yield a 400 (e.g. `deleted → verified` is forbidden).

## 5. Concerns & Mitigations

- **`StaleDataError` caught in wrong layer**: must be caught only around `db.commit()` in the router, never inside the service — catching it there would couple domain logic to HTTP concerns and break the 400-vs-409 separation.
- **Stale ORM identity-map after rollback**: use a fresh `db.query(UserProfile)...` for the 409 body, not `db.refresh()` on the rolled-back instance — the session state is invalid after rollback.
- **Bulk/Core updates bypass `version_id_col`**: all current write paths use the ORM unit of work and are covered; document as a known caveat for any future bulk operations.
- **Backfill safety**: `server_default='1'` ensures existing rows upgrade without a `NOT NULL` violation.
- **Two banners**: `#errorBanner` (400, amber) and `#conflictBanner` (409, red) must be independently cleared to prevent one masking the other — `renderProfile()` hides both, individual handlers show only their own.

---

## Files touched

| File | Action |
|------|--------|
| `app/models/user_profile.py` | Add `version` column + `__mapper_args__` |
| `alembic/versions/<rev>_add_profile_version.py` | Create — `down_revision='c00d7ae13f11'` |
| `app/schemas/responses.py` | Add `version: int` to `UserProfileResponse` |
| `app/routers/user_profiles.py` | Remove sleep, add 409 handler; request schema unchanged |
| `app/static/admin.html` | Add `#versionBadge`, `#conflictBanner` with Reload button |
| `app/static/admin.js` | Display version badge, handle 409, `reloadProfile()` |
| `app/static/admin.css` | Add `.version-badge`, `.conflict-banner`, `.btn-reload` |

`app/services/profile_lifecycle_service.py` — **no changes**. `version_id_col` enforces the check automatically at flush.
