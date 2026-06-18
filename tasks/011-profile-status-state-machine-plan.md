# Plan: Profile Status State Machine (the vulnerable "before")

## 1. Overview

This change introduces a real `ProfileStatus` lifecycle (`new → verified → suspended → deleted`) onto `UserProfile`, a transition service that validates moves against a single transition table and runs per-transition side effects, a `POST /user-profiles/{id}/transition` endpoint, and a self-contained admin UI to drive transitions visually. It deliberately ships **without** any concurrency control: no `version` column, no `__mapper_args__`, no `StaleDataError` handling. Writes are blind last-write-wins, which is precisely the vulnerability the follow-up optimistic-locking plan will demonstrate and fix. Everything else (state machine, side effects, validation, error mapping) is real and production-shaped so the "before" is honest rather than a strawman.

## 2. Architecture Decision

Business rules (the transition table + side effects) live in a dedicated `ProfileLifecycleService` (SRP), keeping the router as a thin HTTP-translation layer and the model as pure persistence state — Clean Architecture's separation of concerns. The service mirrors the established "service builds and flushes, caller owns the commit boundary" convention from `OnboardingService`, so the transaction boundary stays in the router. Domain failures are expressed as typed exceptions (`IllegalTransitionError`, `ProfileNotFound`) raised by the service and mapped to HTTP status in the router, decoupling domain logic from FastAPI. The transition table is a single source of truth (open/closed: new states cost one dict entry, not scattered `if` branches).

## 3. Implementation Steps

**Step 1 — Model: enum + status column** (`app/models/user_profile.py`)
- Add `ProfileStatus(str, enum.Enum)` with `NEW="new"`, `VERIFIED="verified"`, `SUSPENDED="suspended"`, `DELETED="deleted"`.
- Add `status: Mapped[ProfileStatus] = mapped_column(SAEnum(ProfileStatus, name="profile_status"), nullable=False, default=ProfileStatus.NEW, server_default=ProfileStatus.NEW.value)`.
- **No `version` column, no `__mapper_args__`** — those are added in the follow-up optimistic-locking plan.

**Step 2 — Migration** (`alembic/versions/<rev>_add_profile_status.py`, `down_revision = 'a1b2c3d4e5f6'`)
- `upgrade()`: create the enum type (`sa.Enum('new','verified','suspended','deleted', name='profile_status')`, `.create(op.get_bind(), checkfirst=True)`), then `op.add_column('user_profiles', sa.Column('status', <that enum>, nullable=False, server_default='new'))`.
- `downgrade()`: `op.drop_column('user_profiles', 'status')`, then drop the enum type (`sa.Enum(..., name='profile_status').drop(op.get_bind(), checkfirst=True)`).

**Step 3 — Exceptions package** (`app/exceptions/__init__.py`)
- The package is currently empty (only stale `.pyc`). Create `__init__.py` with: `ProfileNotFound(Exception)` carrying `profile_id`; `IllegalTransitionError(Exception)` carrying `profile_id`, `current_status`, `requested_status`, with a human-readable `__str__` ("cannot transition `deleted` → `verified`"). Export both via `__all__`. The next plan's larger design references a `TransactionError` base — keep these standalone now; a base class can be introduced later without breaking callers.

**Step 4 — Lifecycle service** (`app/services/profile_lifecycle_service.py`)
- `ProfileLifecycleService` with `__init__(self, db: Session)` matching `OnboardingService`.
- Module-level `ALLOWED_TRANSITIONS: dict[ProfileStatus, set[ProfileStatus]]`: `NEW→{VERIFIED,DELETED}`, `VERIFIED→{SUSPENDED,DELETED}`, `SUSPENDED→{VERIFIED,DELETED}`, `DELETED→set()`.
- `transition(profile_id, target) -> UserProfile`: `db.get(UserProfile, profile_id)` → raise `ProfileNotFound` if missing; raise `IllegalTransitionError` if `target not in ALLOWED_TRANSITIONS[profile.status]`; call `_run_side_effects(profile, target)`; set `profile.status = target`; **return profile uncommitted** — no version check anywhere.
- `_run_side_effects(profile, target)`: `verify` → create a `Portfolio(owner_id=profile.id, name="Starter Portfolio")` and `db.add`; `suspend`/`reinstate` → log stub; `delete` → log stub (`Portfolio` has no `is_deleted` field). Use `logging`, not `print`.

**Step 5 — Transition endpoint + schema** (`app/routers/user_profiles.py`, update schema)
- Add `status: ProfileStatus` to `UserProfileResponse` so all GET/PUT responses surface it (`from_attributes` already set).
- Add request model `ProfileTransitionRequest(BaseModel)` with `target: ProfileStatus` only — **no `expected_version`**.
- Add `POST /{user_id}/transition`: instantiate service, call `transition`, `db.commit()`, `db.refresh`, return profile. Map `ProfileNotFound → HTTPException(404)`, `IllegalTransitionError → HTTPException(400, detail=str(e))`. **No `StaleDataError` / 409 handling.**

**Step 6 — Admin UI** (`app/routers/user_profiles.py`)
- Add `GET /user-profiles/admin` returning `HTMLResponse` with a self-contained inline-CSS/vanilla-JS page. No static file mount exists in `app/main.py`, so an inline string in the router is the right fit.
- Register this route **before** `GET /{user_id}` — `user_id` is already typed `int` so `/admin` won't coerce, but explicit ordering avoids any ambiguity.
- Page behaviour:
  - Profile-ID input + Load button → `GET /user-profiles/{id}`; renders email, username, and a color-coded status badge (new=grey, verified=green, suspended=amber, deleted=black).
  - Four action buttons (Verify / Suspend / Reinstate / Delete) enabled per a client-side copy of `ALLOWED_TRANSITIONS` for the current status.
  - Each button POSTs `{ "target": "..." }` to `POST /user-profiles/{id}/transition`.
  - On `200`: refreshes the displayed status and re-evaluates button enablement.
  - On `400`: shows the error message in an amber banner.
  - **No version display, no 409 handling** — those are added in the optimistic-locking follow-up.

## 4. Data Flow

The admin page loads a profile via `GET /user-profiles/{id}` and renders its `status`, deriving which action buttons are enabled from a client-side copy of the transition rules. Clicking an action POSTs `{target}` to `/user-profiles/{id}/transition`; the router delegates to `ProfileLifecycleService.transition`, which reads the row, validates against `ALLOWED_TRANSITIONS`, runs side effects (e.g. inserts a Starter Portfolio on verify), mutates `profile.status`, and returns the uncommitted entity. The router commits and refreshes, returning the updated `UserProfileResponse`; the browser re-renders the badge. Errors propagate as typed exceptions translated to 404/400. Because no version travels with the write, two concurrent transitions both read the same status and the second commit silently overwrites the first — the intentional vulnerability.

## 5. Concerns & Mitigations

- **Route shadowing**: `/admin` could be swallowed by `GET /{user_id}` — mitigate by registering the literal route first. `user_id: int` already prevents coercion, but ordering is the belt-and-suspenders fix. Verify with a manual hit after wiring.
- **Enum drift between DB and UI**: the JS transition map duplicates `ALLOWED_TRANSITIONS`; keep both small and document that the server is authoritative (UI enablement is a hint; the 400 is the real guard).
- **Intentional concurrency hole**: last-write-wins is deliberate. Mark it with a code comment so it isn't mistaken for an oversight or silently "fixed" before the demo — the optimistic-locking plan removes it explicitly.
- **Side-effect / commit coupling**: side effects (portfolio insert) only persist if the router commits; an exception after `_run_side_effects` requires a rollback. Keep the commit immediately after the service call with no intervening logic, matching the `OnboardingService` pattern.
- **Migration enum on Postgres**: the native `profile_status` type is created; `downgrade()` must drop the column *then* the type, and use `checkfirst=True` to stay idempotent.

---

## Files touched

| File | Action |
|------|--------|
| `app/models/user_profile.py` | Add `ProfileStatus` enum + `status` column |
| `app/exceptions/__init__.py` | Create — `ProfileNotFound`, `IllegalTransitionError` |
| `app/services/profile_lifecycle_service.py` | Create — `ALLOWED_TRANSITIONS` + `ProfileLifecycleService` |
| `app/routers/user_profiles.py` | Add transition endpoint + admin UI route; update response schema |
| `alembic/versions/<rev>_add_profile_status.py` | Create — `down_revision='a1b2c3d4e5f6'` |
