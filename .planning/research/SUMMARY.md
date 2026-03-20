# Project Research Summary

**Project:** Fantasy Football Analytics — Start/Sit Recommendation Tool
**Domain:** Fantasy sports analytics web application
**Researched:** 2026-03-19
**Confidence:** MEDIUM-HIGH

## Executive Summary

This is a weekly decision-support tool for fantasy football managers: a user looks up a player, and the tool returns a clear START / SIT / FLEX verdict backed by visible reasoning drawn from three primary signals — matchup grade (how favorable the opponent defense is by position), injury and practice status, and recent usage trends (snap count, target share, carry share). The research is unanimous on one architectural decision: the recommendation engine must be a pure, isolated function that takes typed signal inputs and returns a structured output including the reasoning, not just the verdict. Every major risk in this project traces back to violating this principle — black-box scores erode trust, reasoning stored as raw stats computed at render time becomes inconsistent, and mixing business logic into UI components makes it untestable.

The recommended stack is a Next.js 16 frontend (App Router, React Server Components) backed by a Python FastAPI service that runs the data ingestion and scoring engine. The two-language split is justified: Python is where nflreadpy, pandas, and the data science tooling live, and the scoring logic is cleanest to write and test there. The frontend consumes a REST API from FastAPI and uses TanStack Query for client-side caching and polling. Data sources are Sleeper API (free, stable, documented — primary player metadata and injury status) and nflreadpy/nflverse (free, CC-BY licensed — snap counts, target share, weekly stats, schedules). The ESPN unofficial API should be treated as a fragile dependency used only when necessary, wrapped behind a single adapter, and never referenced in more than one file.

The three most consequential risks are: (1) building any part of the data pipeline directly against ESPN's undocumented endpoints without an abstraction layer — the API has broken without notice multiple times and a mid-season breakage with no fallback kills the product; (2) shipping a START/SIT verdict without structured reasoning signals stored in the data model — recovering from this mid-season requires a data migration and UI rebuild; (3) player ID fragmentation across data sources — never joining on player name, always on a canonical numeric ID using nflverse's `ff_playerids` crosswalk. All three of these must be addressed in the first development phase before any feature work begins.

---

## Key Findings

### Recommended Stack

The stack is well-defined and has high confidence. Next.js 16 with the App Router provides the right model for a read-heavy analytics dashboard: data fetching on the server via React Server Components, no client-side waterfall, and a clean separation between interactive UI (Client Components) and data-driven display (Server Components). Tailwind CSS v4 with shadcn/ui covers all needed UI primitives. The Python FastAPI backend is the correct choice because the scoring engine and data ingestion both benefit from the Python data science ecosystem — there is no equivalent of nflreadpy in Node.

The most consequential stack decision is data sourcing. `nfl_data_py` was archived September 25, 2025 and must not be used. Its successor is `nflreadpy` (v0.1.5, November 2025), which provides the same nflverse data. Sleeper API is free, documented, rate-limited at 1000 req/min, and stable — it is the correct primary source for player metadata and injury status. Tank01 on RapidAPI ($10/mo for 1,000 req/day) is an optional enhancement for live gameday updates.

**Core technologies:**
- Next.js 16.2 + React 19: Full-stack framework with App Router — RSC keeps API keys server-side and eliminates client-side waterfalls
- TypeScript 5.x: Mandatory — typed schemas shared between data layer and UI prevent silent mismatches across the multi-source data model
- Tailwind CSS v4 + shadcn/ui: Zero-config styling with production-ready components (cards, badges, tables, tooltips) — no dependency, components are copied in
- Python FastAPI 0.115+ / Python 3.12: Backend scoring engine and data ingestion — only viable choice given nflreadpy and pandas dependency
- nflreadpy (nflverse): Free, CC-BY licensed — snap counts, target share, weekly points, schedules, play-by-play; primary historical stats source
- Sleeper API: Free, no auth, documented — primary player metadata and real-time injury status
- TanStack Query v5: Client-side data fetching, caching, background refresh for polling-heavy UI (injury status updates)
- APScheduler 3.x (AsyncIOScheduler): Background job scheduler inside FastAPI — sufficient for once-daily or weekly data ingestion; no Redis required at v1
- SQLite (dev) / PostgreSQL 16 (prod): Data volume for one NFL season is tiny (<5MB); SQLite is zero-config for local work
- Recharts 2.x: SVG-based React charts for snap count trends, target share, scoring history — stay on 2.x (3.x is in alpha)
- Zod: Runtime validation of external API responses at ingestion boundary

**What not to use:**
- `nfl_data_py` — archived, no updates or security fixes; use `nflreadpy`
- ESPN unofficial API as primary data source — undocumented, changed auth in August 2025, breaks without notice
- Redux Toolkit — TanStack Query handles all server state; Zustand for local UI state if needed; RTK is unjustified overhead
- SportRadar — enterprise pricing ($500–1000+/mo) inappropriate for a personal v1 tool

---

### Expected Features

All research points to the same MVP definition: the product's core purpose is "look up a player, get a clear recommendation with visible reasoning." Every feature that does not directly serve this loop is v2 or out of scope.

No competitor makes transparent reasoning the primary UI element. Most show data tables and leave the user to synthesize the story. That gap is the primary differentiator — the reasoning must be front-and-center, not buried in a tooltip or a "learn more" link.

**Must have (table stakes):**
- Player search by name — the entry point; without this nothing else is reachable
- Clear START / SIT / FLEX verdict — the actual decision users come for
- Injury/practice status (Q/D/Out) — a single wrong recommendation due to a missed injury designation destroys trust; must refresh through the week, not just once
- Matchup grade (opponent rank vs. position) — the most relied-upon single signal across all competitor platforms
- Usage trends (snap %, target share / carry share, last 3-4 weeks) — role stability predicts production; season averages alone are misleading
- Projected fantasy points — numeric anchor; can be computed from usage + matchup or sourced from an API
- Structured reasoning narrative (3-5 factors behind the call) — the differentiator; must ship with v1, not deferred
- All positions covered: QB, RB, WR, TE, K, DST — K and DST use matchup/defense-allowed signals, not player-level projections
- Scoring format awareness (PPR / half-PPR / standard) — target share weight changes materially by format

**Should have (competitive, add after core loop is validated):**
- Player comparison view (A vs. B side-by-side) — the most common real-world use case after individual lookup
- Floor / ceiling range alongside projected points — useful once projection accuracy is trusted
- Vegas implied team total overlay — correlated with fantasy scoring; free API tier available
- Weather flag for outdoor games — low-effort, genuine signal for pass game suppression; flag only, not a blocker
- Matchup grade visual (letter + color coding) — polish layer; logic must exist first

**Defer (v2+):**
- Historical recommendation accuracy tracking — requires a full season of logged recommendations and outcomes
- ESPN OAuth roster sync — auth complexity, ESPN ToS risk; marginal benefit for a personal tool
- Waiver wire recommendations — different product surface (requires roster context, FAAB strategy)
- Trade analyzer — different data problem entirely (dynasty value, rest-of-season rankings)
- AI chatbot / natural language interface — structured reasoning narrative achieves the same goal without LLM infrastructure cost and latency
- Social/community features — changes the product type; out of scope

**Hard out-of-scope (anti-features to resist):**
- League management (standings, transactions) — ESPN already does this
- DFS optimization — separate product surface
- Mobile native app — responsive web handles Sunday couch use without doubling dev surface

The data refresh pipeline is the dependency for everything. It must land in Phase 1 or every subsequent feature is blocked.

---

### Architecture Approach

The architecture follows a strict layered model with hard boundaries: ingestion clients wrap external APIs, a pure engine module computes recommendations from typed signal inputs, thin API route handlers compose ingestion and engine, and UI components only receive and render output. No layer bypasses the layer below it — components never import from the engine directly, routes never call external APIs directly, and the engine never imports from ingestion or UI. This boundary discipline is what makes the scoring logic independently testable and replaceable.

The two patterns that must be established before any feature work: cache-first ingestion (every external API call checks cache before hitting the network, with background Cron refresh so users never hit a cold miss) and the signal aggregation engine (independent signals scored 0-100 with position-aware weights producing a composite verdict and structured reasons array).

**Major components:**
1. Ingestion layer (one module per data source: sleeper.ts, dvp.ts, espn.ts, normalize.ts) — wraps fetch, handles errors, returns normalized types; never called directly from components
2. Recommendation engine (engine/recommend.ts + engine/signals/) — pure TypeScript/Python function: PlayerSignals → Recommendation; no UI coupling, fully unit-testable
3. Cache/KV adapter (cache/kv.ts) — centralized TTL policy; in-process LRU for dev, Vercel KV (Redis) for prod; injury data refreshes every 2h, DVP/matchup data every 4h, player profiles every 6h
4. API route handlers (app/api/) — thin orchestrators; call ingestion, pass signals to engine, return Recommendation; no business logic lives here
5. Scheduled refresh job (Vercel Cron or APScheduler) — populates cache on a fixed schedule; weather data must refresh every 6h Thu-Sun, not once weekly
6. UI layer (RecommendationCard, PlayerSearch, SignalBadge, PositionFilter) — Server Components for data display, Client Components for interactivity; never imports from engine or ingestion

---

### Critical Pitfalls

1. **ESPN unofficial API treated as stable infrastructure** — wrap every ESPN call behind a single adapter; ESPN URL referenced in exactly one file; aggressive cache so the app serves last-known data if the API goes down; Sleeper API is the correct primary source, ESPN is a secondary fallback
2. **Recommendation verdict shipped without structured reasoning signals in the data model** — the recommendation record must carry injury_status, matchup_grade, snap_pct_trend, and target_share as first-class fields from day one; recovering this mid-season requires a data migration, UI rebuild, and retroactive backfill
3. **Player ID fragmentation across data sources** — commit to a canonical numeric player ID system early (ESPN IDs, since the product targets ESPN Fantasy); use nflverse `ff_playerids` crosswalk for cross-source joins; never join on player name string; store all known external IDs in a mapping table from day one
4. **Off-season vs. in-season data availability ignored** — build an explicit season-state model (off_season / preseason / regular_season / playoffs) before recommendation logic is built; show a clear "season not active" state during off-season rather than stale data
5. **Small sample recommendation accuracy collapse** — weight trailing performance over a minimum 4-6 game window; flag recommendations for players with fewer than 4 games of data as low-confidence; surface this flag visibly in the UI; TE and rookie positions require extra caution

---

## Implications for Roadmap

Based on the combined research, the architecture file's build order is validated by the feature dependency graph and the pitfall-to-phase mapping. All three sources converge on the same constraint: the data foundation must land before the engine, the engine before the routes, and the routes before the UI.

### Phase 1: Data Foundation

**Rationale:** Every user-facing feature depends on current, well-structured data. The ingestion layer, cache adapter, normalized player schema, player ID mapping table, and season-state model are all pre-conditions for everything else. The pitfall research is explicit: ESPN adapter, ID mapping, and season-state must be established here or the entire subsequent build is fragile. This phase has no UI output — it's pure infrastructure.

**Delivers:** Sleeper API ingestion client; nflreadpy data ingestion job (APScheduler, Python); cache adapter (in-process LRU for dev); normalized Player schema; player ID crosswalk table (nflverse ff_playerids); season-state model; ESPN adapter with fallback to Sleeper; database schema (SQLite/Postgres) with indexes on player_id, season, week

**Addresses features:** Data refresh pipeline (prerequisite for all features), injury/practice status (real-time), weekly matchup data, usage trend game logs

**Avoids pitfalls:** ESPN API instability (adapter pattern), player ID fragmentation (ID mapping table), off-season data gaps (season-state model)

**Research flag:** Needs phase-level research — the nflreadpy + ESPN/Sleeper multi-source ingestion pattern, ID crosswalk setup, and APScheduler configuration inside FastAPI are specific enough to warrant a focused research pass before implementation.

---

### Phase 2: Recommendation Engine

**Rationale:** The engine is a pure function — it can be built and tested in isolation before any HTTP or UI layer exists. Building it second (after ingestion provides typed input types) ensures signal schemas are locked before any UI consumes them. This is the phase where the most consequential design decisions are made: signal weights, composite scoring formula, position-specific weighting, and the structured reasons array format. Getting this wrong is expensive to fix later.

**Delivers:** engine/signals/ (matchup.ts, injury.ts, usage.ts — each independently testable); engine/recommend.ts (composite weighted score → START/SIT/FLEX + reasons array); position-aware weight configuration (QB vs WR vs TE vs K/DST differ); confidence flag for low-sample players (<4 games); pytest test suite covering all signal combinations; DVP/matchup grade computation from nflreadpy play-by-play (points allowed by position, last 4 weeks)

**Implements:** Signal aggregation with weighted composite score (Architecture Pattern 1)

**Addresses features:** START/SIT verdict, structured reasoning narrative (the core differentiator), matchup grade, usage trends, scoring format awareness (PPR/standard weight adjustment)

**Avoids pitfalls:** No-reasoning black-box (structured reasons are part of the Recommendation type), small sample collapse (confidence flag + 4-game trailing window baked into signal scorers)

**Research flag:** Standard patterns — the weighted composite signal approach is well-documented in the architecture research. No additional research phase needed. Test coverage is the quality gate.

---

### Phase 3: API Routes and Backend Integration

**Rationale:** Routes are thin orchestrators — they compose ingestion clients and the engine and expose HTTP endpoints. They're built third because they depend on both the ingestion layer (Phase 1) and the engine (Phase 2) being stable. This phase also wires the FastAPI backend endpoints that the Next.js frontend will consume.

**Delivers:** FastAPI endpoints (GET /players/search, GET /players/{id}, GET /recommendations/{player_id}, POST /refresh); Next.js API route handlers (/api/search, /api/players/[id], /api/recommendations, /api/refresh); Zod schemas validating API response shapes; error handling and fallback to cached data when external APIs return non-200; health-check endpoint that validates ESPN response shape

**Uses:** FastAPI (Python), Next.js App Router Route Handlers, TanStack Query (configured), Zod validation

**Implements:** Cache-first ingestion (Architecture Pattern 2); background refresh endpoint (Architecture Pattern 3)

**Research flag:** Standard patterns — REST API design with FastAPI and Next.js Route Handlers is well-documented. No research phase needed.

---

### Phase 4: Frontend UI

**Rationale:** The UI is last among the core phases because it depends on stable routes (Phase 3) which depend on a stable engine (Phase 2) which depends on stable ingestion (Phase 1). Building UI before the API contract is stable means rebuilding the UI when the API changes — a common source of wasted effort.

**Delivers:** RecommendationCard (START/SIT/FLEX verdict + signal badges: matchup grade, injury status, usage trend); PlayerSearch (Client Component, autocomplete); Player detail page (/players/[id]); Position list page (/positions/[pos]); SignalBadge components; scoring format selector (PPR / half-PPR / standard); data freshness timestamp on every card; low-confidence flag display for small-sample players; responsive layout (mobile-usable without a native app); off-season state display

**Uses:** shadcn/ui (Card, Badge, Table, Tooltip), Tailwind CSS v4, Recharts (spark lines for snap count and target share trends), TanStack Query v5 (client-side polling for injury status)

**Avoids pitfalls:** Reasoning buried or deferred (surface inline, not in "learn more"), equal prominence for SIT and START verdicts, data freshness timestamp visible, off-season state shown clearly

**Research flag:** Standard patterns — shadcn/ui, Recharts, and TanStack Query integration with Next.js App Router are well-documented. No research phase needed.

---

### Phase 5: Reliability and Enhancement

**Rationale:** Operational concerns and v1.x differentiators are addressed after the core recommendation loop is working end-to-end. Wiring Cron scheduling before the underlying data pipeline is proven adds operational complexity without benefit. Enhancements (Vegas overlay, weather flag, player comparison) add differentiated value on top of a validated foundation.

**Delivers:** Vercel Cron (or APScheduler) for scheduled background refresh; weather integration (NWS API, 6h refresh Thu-Sun, dome stadiums excluded via is_dome flag); Vegas implied team total overlay (the-odds-api.com free tier); player comparison view (A vs. B side-by-side); matchup grade visual (letter + color coding A-F); floor/ceiling projection range; cache TTL tuning per data type; exponential backoff on ESPN API calls; error state UI (API down, no data found)

**Avoids pitfalls:** Stale weather at game time (6h refresh cadence + dome exclusion), scope creep (weather/Vegas/comparison are scoped enhancements, not new product surfaces)

**Research flag:** Weather integration (dome venue data model, NWS API structured fields) and Vegas odds API may benefit from a focused research pass before implementation to confirm free tier limits and data structure.

---

### Phase Ordering Rationale

- Phase 1 before everything else: the pitfall research identifies three data-layer risks (ESPN instability, ID fragmentation, off-season gaps) that must be mitigated before any feature is built on top — building in any other order bakes these risks into the architecture permanently
- Phase 2 (engine) before Phase 3 (routes): the engine is a pure function testable in isolation; locking the Recommendation type (including the reasons array) before routes are built ensures the API contract is stable and the frontend won't need to reconstruct reasoning from raw stats
- Phase 3 (routes) before Phase 4 (UI): the API contract must be stable before UI components are built against it; building UI against a moving API is the primary source of rework in analytics tools
- Phase 5 last: Cron scheduling and enhancement features are operational/polish concerns; they add the most value on top of a validated core, not alongside a speculative one

---

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1:** nflreadpy ingestion patterns + APScheduler inside async FastAPI (async vs. sync scheduler configuration is non-obvious); nflverse ff_playerids crosswalk table structure and join approach; ESPN espn_s2 cookie handling server-side
- **Phase 5:** NWS weather API structured fields and update cadence; the-odds-api.com free tier limits; dome/retractable-roof venue data source

Phases with standard patterns (skip research-phase):
- **Phase 2:** Weighted composite signal engines are well-understood; pytest test patterns are standard; no external API integration complexity
- **Phase 3:** FastAPI REST endpoint patterns and Next.js Route Handlers are comprehensively documented
- **Phase 4:** shadcn/ui + Recharts + TanStack Query integration with Next.js App Router is well-covered by official docs and community examples

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Core framework versions verified via official docs (Next.js 16.2 March 2026, Tailwind v4, shadcn/ui React 19 support). nflreadpy successor status confirmed via GitHub. Sleeper API rate limits confirmed via official docs. |
| Features | MEDIUM-HIGH | Competitor analysis via WebFetch of live sites (FantasyPros, DraftSharks, KTC, StartBench). No direct user interviews. The "transparent reasoning as differentiator" finding is supported by multiple competitor comparisons but is a qualitative judgment. |
| Architecture | MEDIUM | Component layer patterns have high confidence. DVP data source specifics (whether to scrape FantasyPros vs. use FantasyNerds API vs. compute from nflreadpy play-by-play) are MEDIUM confidence — the research recommends computing from nflreadpy which avoids external API cost but is the more complex path. ESPN API integration patterns are LOW confidence (community-sourced, undocumented). |
| Pitfalls | MEDIUM | ESPN breaking-change history is documented via community sources (not ESPN official docs). Recommendation accuracy benchmarks (54-67% accuracy range) sourced from published analyses. Player ID fragmentation pattern is from nflverse documentation. All pitfalls are credible but some are inferred from domain knowledge rather than direct evidence. |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **DVP computation vs. sourcing decision:** Research recommends computing matchup grades from nflreadpy play-by-play (points allowed by position, last 4 weeks) rather than scraping FantasyPros or paying for FantasyNerds. This is achievable but requires pandas work in the engine phase. Validate the nflreadpy play-by-play schema during Phase 1 before committing to this approach.
- **ESPN espn_s2 cookie rotation:** The research identifies ESPN cookies as ephemeral and potentially expiring. For a personal tool, manually refreshing the cookie is acceptable. If the tool opens to other users, this becomes a blocker — Sleeper-only for injury status may be the correct v2 path. Document this decision gate.
- **nflreadpy "experimental" lifecycle:** nflreadpy is marked experimental by nflverse maintainers. Pin to v0.1.5, monitor GitHub for breaking changes at season transitions, and have a contingency plan (nfl_data_py is archived; the contingency would be direct nflverse S3/GitHub data file ingestion).
- **FantasyNerds API pricing:** Pricing is not publicly published. If the DVP-from-play-by-play approach proves too complex, FantasyNerds has a free trial and pre-computed matchup grades. Confirm pricing before Phase 2 if compute approach is deprioritized.
- **Scoring format configuration scope:** The MVP should default to half-PPR (most common ESPN league format) and allow PPR and standard selection. The research confirms this is P1 but doesn't specify where the configuration lives (user preference stored locally vs. per-query parameter). Decide during requirements definition.

---

## Sources

### Primary (HIGH confidence)

- [nflreadpy GitHub — nflverse/nflreadpy](https://github.com/nflverse/nflreadpy) — successor to archived nfl_data_py; v0.1.5 confirmed Nov 2025
- [Sleeper API docs — docs.sleeper.com](https://docs.sleeper.com/) — injury fields, rate limits (1000 req/min), player endpoints
- [Next.js 16.2 release notes — nextjs.org/blog/next-16-2](https://nextjs.org/blog/next-16-2) — current stable version confirmed March 2026
- [Tailwind CSS v4 — tailwindcss.com/blog/tailwindcss-v4](https://tailwindcss.com/blog/tailwindcss-v4) — CSS-first config, zero-config auto-detection
- [shadcn/ui docs — ui.shadcn.com/docs/react-19](https://ui.shadcn.com/docs/react-19) — React 19 compatibility confirmed
- [TanStack Query comparison — tanstack.com/query/v5/docs/react/comparison](https://tanstack.com/query/v5/docs/react/comparison) — feature comparison with SWR
- [nflreadr ff_playerids — nflreadr.nflverse.com](https://nflreadr.nflverse.com/articles/dictionary_ff_playerids.html) — cross-source player ID mapping
- [DVOA/DVP methodology — FTN Fantasy](https://ftnfantasy.com/nfl/dvoa-explainer) — matchup grading standard signal
- [Next.js App Router patterns — Raftlabs](https://www.raftlabs.com/blog/building-with-next-js-best-practices-and-benefits-for-performance-first-teams/) — Server/Client Component split, caching

### Secondary (MEDIUM confidence)

- [Tank01 NFL API — RapidAPI](https://rapidapi.com/tank01/api/tank01-fantasy-stats) — pricing confirmed; third-party aggregator
- [Fantasy Nerds API docs — api.fantasynerds.com/docs/nfl](https://api.fantasynerds.com/docs/nfl) — DVP endpoints confirmed; pricing unpublished
- [FantasyPros start/sit tool](https://support.fantasypros.com/hc/en-us/articles/26339296287899-What-tools-do-you-have-for-Start-Sit-decisions) — competitor feature analysis
- [DraftSharks start/sit tool](https://www.draftsharks.com/kb/fantasy-football-start-sit) — competitor feature analysis (floor/ceiling approach)
- [StartBench.com](https://startbench.com/) — Vegas odds integration pattern
- [Recommendation accuracy benchmarks — LinkedIn/Kurt Scherf](https://www.linkedin.com/pulse/whose-fantasy-football-start-em-sit-advice-most-accurate-kurt-scherf) — 54-67% accuracy range
- [Fantasy Football Analytics projection bias](https://fantasyfootballanalytics.net/2025/07/fantasy-football-projections-exploring-positional-bias-in-projections.html) — recency bias, small sample risks
- [nflverse/nfl_data_py GitHub](https://github.com/nflverse/nfl_data_py) — archived status confirmed Sep 25, 2025
- [Zuplo ESPN Hidden API Guide](https://zuplo.com/learning-center/espn-hidden-api-guide) — ESPN API instability history
- [Zuplo Sleeper API guide](https://zuplo.com/learning-center/sleeper-api) — Sleeper reliability comparison

### Tertiary (LOW confidence — community or inferred)

- [ESPN unofficial API gist — nntrn/GitHub](https://gist.github.com/nntrn/ee26cb2a0716de0947a0a4e9a157bc1c) — community-maintained endpoint list; undocumented and subject to change
- [ESPN API cwendt/espn-api GitHub](https://github.com/cwendt94/espn-api) — auth cookie (espn_s2) change history; community-sourced
- [Steven Morse ESPN Fantasy v3 migration](https://stmorse.github.io/journal/espn-fantasy-v3.html) — v2→v3 silent migration history

---
*Research completed: 2026-03-19*
*Ready for roadmap: yes*
