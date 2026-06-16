# Pattern 4 — Optimistic Locking: Tech Demo Plan

**Scenario:** Concurrent **buy/sell adjustments** to a portfolio holding, protected by a no-oversell rule and weighted-average cost recompute.
**Audience:** Group of programmers (mixed familiarity with SQLAlchemy / concurrency)
**Duration:** ~30–45 minutes (standard session)
**Format:** Live, visual demo driven by **two browser tabs** acting as two traders on the same holding. One wins, the other receives an `HTTP 409 Conflict`, reloads, and re-applies its trade against fresh state.
**Stack:** FastAPI + SQLAlchemy + **PostgreSQL** (already the live DB per `.env` / docker-compose).
**Deliverable status:** Proposal only — no application code changed yet. Section 4 specifies the enhancement to build before the demo.

---

## 1. The story we want to tell

Two traders are working the same position at the same time. One submits **buy 5**, the other submits **sell 3**, and both started from a holding of **10 units**. The only correct end state is **12**. Yet a naive "read the row, set the new quantity, save" implementation will land on either 15 or 7 — one trade silently evaporates. That is the **lost update** problem, and here it is *money*, not a cosmetic glitch.

Optimistic locking fixes it without locking anyone out. Everyone reads freely; the collision is detected **at commit time** via a `version` number. The first trade to commit bumps the version; the second trade's update no longer matches the version it read, the `UPDATE` touches zero rows, and SQLAlchemy raises `StaleDataError`. We turn that into a clean `409 Conflict`, the client reloads the *current* quantity, re-runs its business rules, re-applies its delta, and the books balance at 12.

The reason this scenario beats "two people editing a price" is twofold. First, the new value is **computed from the old value** (a read-modify-write), so last-write-wins is provably *wrong*, not merely impolite. Second, there is real **business logic between the read and the write** — a no-oversell check and a cost-basis recompute — that must run against the truly-current state. That logic is exactly what optimistic locking protects, and it's why "just do it in one SQL statement" (the obvious objection) doesn't actually solve the problem. See Section 9.

---

## 2. Why a two-tab visual demo is the right vehicle

Concurrency bugs are abstract on a slide and invisible in a single terminal. Two side-by-side browser tabs map directly onto "two traders." The audience watches both quantities and version badges, sees one trade commit, sees the other turn red with a conflict, then watches the recovery produce the correct total. It's the difference between being *told* a race exists and *watching* one get caught.

The UI stays deliberately tiny (one static HTML page served by FastAPI, no build step) so it teaches the pattern instead of distracting from it.

---

## 3. Current state of the app (the "before")

The vulnerability is already in the codebase, which makes the opening honest and concrete:

- **`PortfolioHolding` has no concurrency control.** `app/models/portfolio_holding.py` defines `quantity` (`Numeric(18,8)`), `purchase_price` (per-unit cost basis, nullable), a unique `(portfolio_id, asset_id)` constraint — but **no `version` column** and **no `__mapper_args__`**.
- **The existing update is a blind overwrite.** `update_holding` in `app/routers/holdings.py` does `setattr(holding, "quantity", value)` then `db.commit()` — pure last-write-wins, no version check, no validation that you aren't overselling. Two concurrent calls clobber each other. This is the "before" we demo first.
- **No buy/sell concept yet.** Quantity is only ever *set* to an absolute value, never adjusted by a *delta*. There's also no no-oversell rule and no cost-basis recompute. We add those.
- **PostgreSQL is live.** `.env` → `postgresql://...:5432/pythontrio_live`; `docker-compose.yml` runs `postgres:16-alpine`. The demo runs on a real RDBMS.
- **House conventions to mirror:** services build work and let the caller own the commit boundary (`app/services/onboarding_service.py`); routers translate errors to HTTP. Tests use pytest under `tests/unit`, `tests/integration`, `tests/scripts` with a shared `conftest.py`.

Opening move: show `update_holding`, ask the room what happens when a buy and a sell hit it concurrently, and let them realize a trade will vanish.

---

## 4. How to enhance the app to demo this best

Five focused additions, all relative to `python_trio/`. Each mirrors existing conventions.

### 4.1 Add a `version` column to `PortfolioHolding`
In `app/models/portfolio_holding.py`:

```python
version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

__mapper_args__ = {"version_id_col": version}
```

This single `__mapper_args__` line is the heart of the demo. Every `UPDATE` SQLAlchemy emits for a holding now carries `... WHERE id = :id AND version = :expected` and auto-increments `version`. If zero rows match, SQLAlchemy raises `StaleDataError`. **No hand-written version checks anywhere** — the ORM and DB enforce it. (We lock the *holding*, not the asset, because the holding's quantity is the contested, per-portfolio state.)

### 4.2 Alembic migration for the new column
Add `version` with a server default so existing rows backfill to 1:

```python
op.add_column('portfolio_holdings',
    sa.Column('version', sa.Integer(), nullable=False, server_default='1'))
```

Showing the migration makes clear this is a real schema change, run with `alembic upgrade head`.

### 4.3 A buy/sell adjust service with the business rules
New `app/services/trading_service.py`, in the existing "service builds, caller commits" style. One method does the read-modify-write that optimistic locking protects:

```python
def adjust_holding(self, holding_id: int, side: str, qty: Decimal,
                   price: Decimal | None, expected_version: int) -> PortfolioHolding:
    holding = self.db.get(PortfolioHolding, holding_id)   # reads current version
    if side == "sell" and qty > holding.quantity:
        raise OversellError(holding_id, holding.quantity, qty)   # no-oversell rule
    if side == "buy":
        holding.purchase_price = weighted_avg(                  # cost-basis recompute
            holding.quantity, holding.purchase_price, qty, price)
        holding.quantity += qty
    else:
        holding.quantity -= qty
    # caller commits; version_id_col enforces expected_version at flush
```

Two pieces of logic live here that **cannot be pushed into a single SQL statement**: the no-oversell guard and the weighted-average cost recompute on buys. That's what makes this a genuine optimistic-locking scenario rather than a counter (Section 9).

Add an exception type alongside the plan's existing exception design, e.g. `OversellError(TransactionError)` carrying `holding_id`, `available`, `requested`.

### 4.4 A conflict-aware endpoint
`POST /tx-demo/holdings/{id}/adjust` in a new router `app/routers/transaction_demos.py` (prefix `/tx-demo`, registered in `app/main.py`). Request body: `{ "side": "buy"|"sell", "quantity": <decimal>, "price": <decimal|null>, "expected_version": <int> }`. Behaviour:

- Call `trading_service.adjust_holding(...)`, then `db.commit()`.
- On `sqlalchemy.orm.exc.StaleDataError` → roll back, return **`409 Conflict`** with the current quantity/version in the body, a **`Retry-After: 1`** header, and a "reload and re-apply your trade" message.
- On `OversellError` → **`400 Bad Request`** ("cannot sell N, only M available"). This is a *different* failure from the concurrency conflict, and showing both teaches the distinction.
- On success → return the holding with its **new** quantity and version.

### 4.5 The minimal two-tab UI (the visual centerpiece)
Serve one self-contained HTML page at `GET /tx-demo/ui` (vanilla JS, no framework). For a chosen holding it shows:

- Asset symbol + portfolio name.
- Current **quantity** and a prominent **version badge** (e.g. `v3`).
- **Buy** and **Sell** buttons with a quantity input (and a price input used on buys).
- A color-coded **status banner** and a small **event log**.

Flow the page implements:

1. On load, `GET` the holding and cache `quantity` + `expected_version` locally.
2. On Buy/Sell, `POST .../adjust` with the side, delta, price, and cached `expected_version`.
3. On `200`: banner **green**, update displayed quantity + version, log "BUY 5 → qty 15 (v4)".
4. On `409`: banner **red**, "Someone traded this while you were deciding — now qty X (vN)," plus a **Reload** button that re-fetches and refreshes the cached version.
5. On `400` (oversell): banner **amber**, show the no-oversell message.

Open the page in two tabs → two independent traders. Color + version badge make the collision legible from the back row.

### 4.6 A presenter-friendly way to guarantee the race
Live races are timing-dependent; make the headline collision deterministic:

- **Manual staleness (recommended):** simply don't reload Tab B. Tab A buys (version 3→4); Tab B still holds `expected_version=3`; Tab B's sell → guaranteed `409`. No timing luck required.
- **Optional `?delay_ms=` hook**, gated behind an `ENABLE_DEMO_ENDPOINTS` flag, to hold the transaction open and show a genuine overlap from `curl` for the deeper-dive crowd. Never reaches production.

> Guardrail to say out loud: everything lives under `/tx-demo` behind a demo flag, per the parent plan's Section 7.

---

## 5. Session agenda (~30–45 min)

| # | Segment | Time | What happens |
|---|---------|------|--------------|
| 1 | Hook: the vanishing trade | 4 min | Show `update_holding`'s blind `setattr`. Pose buy-5 + sell-3 from qty 10. Ask the room for the result; let them spot that a trade disappears. |
| 2 | Concept | 5 min | Optimistic vs. pessimistic in one line each. Sequence diagram: two readers, one winner. "Detect, don't prevent." |
| 3 | The mechanism | 6 min | The 2-line change: `version` column + `version_id_col`. The generated `WHERE version = :expected` + auto-increment. No hand-written checks. |
| 4 | **Live demo** | 10 min | Two-tab buy/sell collision + recovery + oversell case (run-sheet in Section 6). |
| 5 | Under the hood | 6 min | Echoed SQL showing `WHERE ... AND version = ?`; the `StaleDataError`; router mapping to `409` + `Retry-After`; contrast with the `400` oversell path. |
| 6 | Retry & UX strategy | 4 min | Reload-and-reapply, exponential backoff + jitter, idempotency keys, when a 409 should be invisible vs. surfaced. |
| 7 | Trade-offs & "why not just SQL?" | 4 min | The atomic-`UPDATE` objection (Section 9); optimistic vs. pessimistic (forward-ref Pattern 6); the high-read/low-write sweet spot. |
| 8 | Q&A | 3–6 min | Section 8. |

---

## 6. Live demo run-sheet (the 10-minute core)

**Pre-flight (off-screen):** `docker compose up -d`; `alembic upgrade head` (version column present); seed a portfolio holding a recognizable asset (e.g. BTC) at **quantity 10, cost basis 50,000**. App running. Open `GET /tx-demo/ui?holding=<id>` in **two tabs** side by side; confirm both show qty 10, `v1`. Font size up.

**Act 1 — Baseline (≈2 min)**
1. Both tabs show qty 10 and the same version badge.
2. **Tab A: Buy 5** → green, qty 15, version ticks to v2.
3. Note **Tab B still shows qty 10 / v1** — it never learned about the buy. "Tab B is now stale. Watch."

**Act 2 — The collision (≈3 min)**
4. **Tab B: Sell 3** (still sending `expected_version=1`).
5. Tab B banner goes **red: 409 Conflict** — "position changed to 15 (v2) while you were deciding."
6. Drive it home: "Without optimistic locking, Tab B would have written 10 − 3 = 7, silently erasing Tab A's buy. The correct answer is 12, and we just prevented the wrong one."

**Act 3 — Recovery → correct books (≈2 min)**
7. Tab B: click **Reload** → sees qty 15, v2.
8. Re-issue **Sell 3** → succeeds, qty **12**, v3. "That's the retry loop a real client implements — and the books now balance."

**Act 4 — The other failure mode + under the hood (≈3 min)**
9. From the current qty 12, **Sell 100** → **amber 400**, "cannot sell 100, only 12 available." Distinguish: 400 = business rule, 409 = concurrency conflict.
10. Switch to the terminal with SQL echo on. Show `UPDATE portfolio_holdings SET quantity=?, version=? WHERE id=? AND version=?`, point at the `AND version=?` and the zero-row-count that raised `StaleDataError`, then the `except StaleDataError -> 409` handler. UI → ORM → SQL → HTTP, closed loop.

**Fallback:** Acts 1–2 depend only on *not reloading Tab B*, so the 409 is deterministic regardless of timing. Keep a ~90s screen recording as backup in case the app won't start.

---

## 7. Key talking points to land

- **Detect, don't prevent.** No locks on the happy path; you only pay a retry on the rare collision.
- **Read-modify-write is the tell.** Because the new quantity is derived from the old one, last-write-wins is provably wrong — this is why a counter/balance is the textbook optimistic-locking case.
- **The version is a compare-and-swap.** `WHERE version = :expected` + increment is CAS expressed in SQL; naming it connects to lock-free programming the audience may already know.
- **409 is a feature.** It's the system defending data integrity; the client's job is reload → reapply, ideally with backoff.
- **Business logic is why the ORM approach earns its keep.** The no-oversell check and cost-basis recompute must run in Python against current state — see Section 9.
- **Zero hand-written checking.** `version_id_col` enforces it on every update across all app servers, because the guarantee lives in the DB row, not app memory.

---

## 8. Anticipated questions (prep)

- **"Why not just lock the row?"** Pessimistic locking (Pattern 6) blocks other writers and hurts throughput; optimistic wins for high-read/low-write and avoids contention. Forward-ref the Pattern 6 demo.
- **"What about two requests in the same microsecond?"** The DB serializes the two `UPDATE`s; the first bumps the version, the second's `WHERE version=` matches nothing → `StaleDataError`. The row is the single source of truth; no tie.
- **"Isn't `updated_at` enough to detect change?"** No — timestamp resolution and clock skew make it an unreliable concurrency token. An integer version incremented atomically by the DB is exact.
- **"How do retries avoid a thundering herd / infinite loop?"** Bounded retries + exponential backoff + jitter; surface to the user after N attempts; we return `Retry-After: 1`.
- **"Does this hold across multiple app servers?"** Yes — the check is in the DB row, so it holds across processes and hosts.
- **"What's the difference between the 400 and the 409 here?"** 400 = a business rule said no (oversell); 409 = the data moved under you (stale version). Different causes, different client responses.
- **"What about bulk updates?"** `version_id_col` triggers per row via the unit of work; bulk `UPDATE` bypasses it and needs explicit handling. Note as a caveat.

---

## 9. The "why not just one SQL statement?" objection (handle it head-on)

Someone will ask: *"Why not `UPDATE portfolio_holdings SET quantity = quantity + :delta WHERE id = :id` and skip the version column?"* For a **pure counter**, that's a legitimate atomic solution and you wouldn't need optimistic locking at all. Say so plainly — it earns credibility.

The reason it doesn't solve *this* problem is the business logic wrapped around the write:

1. **No-oversell rule.** "Quantity must not go negative" can't be expressed as a blind `quantity = quantity - :delta`. You could bolt on `AND quantity >= :delta` and inspect the row count, but that gets unwieldy fast and pushes invariant-enforcement into ad-hoc SQL.
2. **Weighted-average cost recompute on buys.** `new_avg = (old_qty*old_avg + buy_qty*buy_price)/(old_qty+buy_qty)` reads *two* current columns and writes one — a genuine read-modify-write that depends on consistent current values.
3. **Realistic services do more than arithmetic** — emit events, enforce limits, log audit trails — all needing the current state in application code.

Optimistic locking lets you keep that logic in clean Python and still be concurrency-safe: read current state, run the rules, write, and let `version_id_col` guarantee nothing changed underneath you. If it did, you get a 409 and re-run the rules on fresh state. That's the honest, defensible case for the pattern.

---

## 10. Pre-demo checklist

- [ ] Implement 4.1–4.5 (version column, migration, `trading_service`, `/tx-demo/holdings/{id}/adjust`, two-tab UI).
- [ ] `docker compose up -d`; `alembic upgrade head`; confirm `version` exists on `portfolio_holdings`.
- [ ] Seed a holding at qty 10 / cost 50,000 on a recognizable asset.
- [ ] Enable SQL echo for the "under the hood" segment (demo engine only, off by default).
- [ ] Verify the deterministic 409 path (Tab A buy → Tab B stale sell) and the 400 oversell path end-to-end.
- [ ] Confirm `/tx-demo` is behind the demo flag and absent from any prod profile.
- [ ] Record a ~90s backup screencast of the four acts.
- [ ] Add integration tests (matching `tests/integration` style) for: successful buy, 409-on-stale-version, 400-on-oversell — so the demo doubles as regression coverage.

---

## 11. Scope notes / out of scope

Covers Pattern 4 only; pessimistic locking (Pattern 6) is the referenced contrast and a separate demo. The two-tab UI is intentionally throwaway-grade (single HTML file, no auth, no framework) to keep focus on the concurrency mechanism. The optional `?delay_ms=` hook (4.6) and the SQL-level walkthrough (Act 4) are the extension paths for a deeper-dive audience without lengthening the core demo.
