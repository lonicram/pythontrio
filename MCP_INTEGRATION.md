# Adding MCP to PythonTrio — Architecture Overview & Feature Roadmap

This document analyzes the current PythonTrio API and proposes how to best incorporate the **Model Context Protocol (MCP)** so that AI agents (Claude Desktop, Cursor, your own agents, etc.) can read and act on portfolio data.

---

## 1. What you have today

PythonTrio is a clean FastAPI + SQLAlchemy + Alembic application for tracking crypto/stock portfolios. The API surface, grouped by router, is:

| Router | Prefix | Endpoints |
|--------|--------|-----------|
| `user_profiles` | `/user-profiles` | list, get, create, update, delete |
| `portfolios` | `/portfolios` | list, get, create, update, delete |
| `holdings` | `/portfolios/{id}/holdings` | list, add, update, remove |
| `assets` | `/assets` | list, get, create, update, delete |
| `asset_prices` | `/assets/{id}/prices` | create price, get history (paginated/filtered), get latest |
| `onboarding` | `/users/onboard` | atomic user + portfolio + holdings creation |
| `main` | `/`, `/health` | root + health check |

Data model (from `db_erd.mermaid`): `ASSET` → `ASSET_PRICE` (1:N price history), `PORTFOLIO` → `PORTFOLIO_HOLDING` → `ASSET`, plus `USER_PROFILE` owning portfolios.

**Architectural observations relevant to MCP:**

- Business logic mostly lives **inside the routers** (e.g. `assets.py`, `holdings.py`). Only onboarding has been extracted into a real service (`OnboardingService`) — a pattern worth replicating.
- Pydantic schemas are defined per-router and already describe inputs/outputs precisely. This is exactly what MCP needs to auto-generate tool schemas.
- `scripts/sync_prices.py` already demonstrates the "external client talks to the REST API" decoupling pattern — a useful precedent for how an MCP server could be deployed separately.
- There is currently **no authentication** anywhere. This is the single most important thing to address before exposing write operations through MCP.

---

## 2. A quick primer: what MCP gives you

MCP is a standard protocol that lets an LLM client discover and call your capabilities. A server exposes three primitives:

- **Tools** — callable functions the model can invoke (your CRUD + analytics). This is where most of the value is.
- **Resources** — read-only context the client can load (e.g. a portfolio snapshot, the asset catalog, the DB schema).
- **Prompts** — reusable prompt templates ("analyze my portfolio risk") that bundle instructions with data.

Transport: use **Streamable HTTP** for a web-deployed server (it supersedes the old HTTP+SSE). **stdio** is for local-only servers launched directly by a desktop client.

---

## 3. Three integration approaches (and which to pick)

### Option A — Auto-expose the existing API (`fastapi-mcp`)
One import turns your existing endpoints into MCP tools. It talks to your app over ASGI (no extra HTTP hop) and reuses your `Depends()` for auth.

```python
# app/main.py
from fastapi_mcp import FastApiMCP

mcp = FastApiMCP(app, name="PythonTrio MCP")
mcp.mount()   # served at /mcp
```

- **Pros:** fastest possible path; tools stay in sync with the API automatically; preserves your Pydantic schemas and docstrings.
- **Cons:** tools mirror the *CRUD shape* of your REST API, which is not always the shape an LLM works best with (e.g. there is no single "what is my portfolio worth" call). Exposes everything unless you filter with `include_operations` / `exclude_tags`.
- **Best for:** a working prototype this week, and for read-only endpoints.

### Option B — A curated MCP server (`FastMCP` / official `mcp` SDK)
Hand-write a small set of well-designed tools that call your **service layer**, optimized for how an agent thinks.

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("PythonTrio")

@mcp.tool()
def get_portfolio_value(portfolio_id: int) -> dict:
    """Return current market value, cost basis, and unrealized P&L of a portfolio."""
    ...
```

- **Pros:** clean, agent-friendly tool design; you control exactly what is exposed; natural home for analytics tools that don't map to a single endpoint.
- **Cons:** a bit more code; you must keep it aligned with the domain (mitigated by reusing services).
- **Best for:** the production target.

### Option C — Hybrid (recommended)
Mount a curated FastMCP server onto the existing FastAPI app so one process serves both REST and MCP:

```python
app.mount("/mcp", mcp.streamable_http_app())
# IMPORTANT: pass the FastMCP lifespan into FastAPI, or the
# session manager won't initialize.
```

**Recommendation:** Start with **Option A** for a quick demo, then converge on **Option C**: a curated FastMCP server that calls a refactored service layer, mounted at `/mcp`. Use a separate deployment (like `sync_prices.py` does) only if you want to scale or secure the agent surface independently.

---

## 4. Target architecture

```
                    ┌─────────────────────────────────────────┐
                    │              FastAPI app                  │
   REST clients ───▶│  /assets /portfolios /users ... (routers)│
                    │                    │                      │
   MCP clients  ───▶│  /mcp  (FastMCP) ──┤                      │
   (Claude,         │                    ▼                      │
    Cursor,         │            Service layer                  │
    agents)         │  AssetService / PortfolioService /        │
                    │  HoldingService / AnalyticsService        │
                    │                    │                      │
                    │                    ▼                      │
                    │        SQLAlchemy models + session        │
                    └────────────────────┬──────────────────────┘
                                         ▼
                                   PostgreSQL
```

**The key refactor:** move logic out of the routers into a `app/services/` layer (you already started this with `OnboardingService`). Then both the REST routers and the MCP tools become thin adapters over the same services. This avoids duplicating validation/business rules across two interfaces — the single most important design decision here.

Suggested services to extract:
- `AssetService` — CRUD + symbol search.
- `PortfolioService` — CRUD + ownership checks.
- `HoldingService` — add/update/remove with the existing duplicate/FK guards.
- `PriceService` — append price, history queries, latest price.
- `AnalyticsService` — **new**, the high-value layer (valuation, P&L, allocation, trends).

---

## 5. Proposed MCP features

### Tier 1 — Read tools (safe, high value, build first)
These are low-risk and immediately useful for "talk to your portfolio" experiences.

- `list_assets` / `search_assets(query, asset_type)` — find assets by name/symbol/type.
- `get_asset(asset_id)` — details incl. current price.
- `get_price_history(asset_id, from_date, to_date)` — time series for analysis.
- `get_latest_price(asset_id)`.
- `list_portfolios` / `get_portfolio(portfolio_id)`.
- `get_holdings(portfolio_id)` — positions with asset info.

### Tier 2 — Analytics tools (the real differentiator)
These don't exist as REST endpoints yet and are where MCP shines, because an agent can ask one question instead of orchestrating many calls.

- `get_portfolio_value(portfolio_id)` — sum of `quantity × latest_price`, total cost basis, and unrealized P&L.
- `get_portfolio_pnl(portfolio_id)` — per-holding and total gain/loss using `purchase_price` vs current price.
- `get_allocation(portfolio_id)` — breakdown by `asset_type` and by position (concentration / diversification).
- `get_asset_trend(asset_id, period)` — % change, simple volatility, high/low over a window.
- `compare_portfolios(ids)` — side-by-side value, P&L, allocation.
- `rebalancing_suggestions(portfolio_id, target_allocation)` — gap analysis vs a target mix (advisory only — see safety note).

### Tier 3 — Write tools (gate carefully)
Expose these only with authentication and explicit user confirmation in the client.

- `create_asset`, `add_holding`, `update_holding`, `remove_holding`, `create_portfolio`, `onboard_user`.
- Keep destructive operations (delete asset/portfolio) **out** of MCP, or behind a separate, clearly-flagged tool — deletes cascade to price history and holdings.

### Resources
- `portfolio://{id}/snapshot` — current holdings + valuation as read-only context.
- `assets://catalog` — the full asset list.
- `schema://erd` — the data model (`db_erd.mermaid`) so agents understand relationships.

### Prompts
- `analyze_portfolio` — "Given this portfolio snapshot, summarize performance, concentration risk, and notable movers."
- `investment_review` — structured periodic review template.

---

## 6. Cross-cutting concerns

**Authentication & authorization (do this before Tier 3).** The app has no auth today. MCP for remote servers supports OAuth 2.1; at minimum add API-key or token auth and scope every portfolio/holding tool to the owning `user_profile`. With `fastapi-mcp` you can reuse FastAPI `Depends()` for this.

**Read/write separation.** Ship read tools first. For any write or advisory-financial tool, design the client interaction so the **user confirms** before execution — agents should not silently mutate holdings or move value.

**Not financial advice.** `rebalancing_suggestions` and similar must be framed as informational analysis, not personalized investment advice, and labeled as such in the tool description and output.

**Determinism & money.** Keep all monetary math in `Decimal` (the models already use `Numeric(18,8)`) — never let valuation/P&L drift into float. Note `asset_prices.py` currently types price as `float` in its schema; standardize on `Decimal` in the analytics layer.

**Observability.** Log tool invocations (you already have a logging pattern in `sync_prices.py`). This matters more for MCP because calls originate from an autonomous agent.

**Testing.** You have solid pytest integration tests per router. Mirror that with tests that call the service layer directly, so both REST and MCP inherit the coverage.

---

## 7. Suggested rollout

1. **Refactor** router logic into `app/services/` (start with `AnalyticsService`, since it's net-new).
2. **Prototype** with `fastapi-mcp` mounted at `/mcp`, exposing only Tier 1 read tools (`include_tags`). Connect Claude Desktop / Cursor to validate the loop.
3. **Build** `AnalyticsService` + Tier 2 tools as a curated FastMCP server (Option C), mounted alongside REST.
4. **Add auth**, then carefully enable Tier 3 write tools with per-user scoping and client-side confirmation.
5. **Add** resources + prompts to make agents context-aware.
6. **Harden:** logging, rate limiting, tests, and a decision on co-located vs separate deployment.

---

## 8. Dependencies to add

```text
# Option A
fastapi-mcp

# Option B/C
mcp            # official SDK (includes FastMCP)
# or
fastmcp        # gofastmcp.com, the extended framework
```

Both reuse your existing Pydantic schemas, so there is no schema duplication.
