# Architecture Research

**Domain:** Fantasy Football Analytics — Start/Sit Recommendation Tool
**Researched:** 2026-03-19
**Confidence:** MEDIUM (component patterns HIGH, API-specific integration details MEDIUM)

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                              │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ Player Search│  │ Player Detail│  │ Position List │           │
│  │   (input)    │  │  (rec card)  │  │  (QB/RB/WR…) │           │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘           │
│         │                 │                 │                   │
├─────────┴─────────────────┴─────────────────┴───────────────────┤
│                      APPLICATION LAYER                           │
│                                                                  │
│  ┌──────────────────────┐  ┌──────────────────────────────────┐  │
│  │    API Routes        │  │     Recommendation Engine        │  │
│  │  /api/players/[id]   │  │  - Matchup grade (DVP)           │  │
│  │  /api/search         │  │  - Injury weight                 │  │
│  │  /api/recommendations│  │  - Usage trend (snap/target)     │  │
│  └──────────┬───────────┘  │  - Composite start/sit signal    │  │
│             │              └──────────────────────────────────┘  │
├─────────────┴────────────────────────────────────────────────────┤
│                        DATA LAYER                                │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  Ingestion   │  │    Cache     │  │   Scheduled Jobs     │   │
│  │  (API calls) │  │  (KV store)  │  │  (refresh triggers)  │   │
│  └──────┬───────┘  └──────┬───────┘  └──────────────────────┘   │
│         │                 │                                      │
├─────────┴─────────────────┴──────────────────────────────────────┤
│                     EXTERNAL DATA SOURCES                        │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ Sleeper API │  │ ESPN API    │  │ Pro-Football-Reference   │  │
│  │ (player IDs,│  │ (unofficial)│  │ / FTN (DVP/DVOA data)   │  │
│  │ rosters)    │  │             │  │                         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| Player Search | Accept player name input, return matching players | Next.js Server Component + API route |
| Player Detail / Rec Card | Display recommendation, reasoning breakdown, signal badges | React Client Component (interactivity) |
| Position List | Browse all fantasy-relevant players by position | Next.js Server Component, server-fetched |
| API Routes | Proxy external API calls, apply server-side auth, enforce cache | Next.js Route Handlers (`/app/api/`) |
| Recommendation Engine | Combine signals into START / SIT / FLEX verdict with explanation | Pure TypeScript module, no UI coupling |
| Ingestion Client | Typed wrappers around each external API | One module per data source |
| Cache / KV Store | Avoid redundant API calls; serve stale data during outages | Vercel KV (Redis) or in-process LRU for dev |
| Scheduled Jobs | Refresh player, injury, and matchup data on a timer | Vercel Cron or GitHub Actions |

---

## Recommended Project Structure

```
src/
├── app/                       # Next.js App Router
│   ├── page.tsx               # Search / home page
│   ├── players/
│   │   └── [id]/
│   │       └── page.tsx       # Player detail + recommendation
│   ├── positions/
│   │   └── [pos]/
│   │       └── page.tsx       # Browse by position (QB, RB, etc.)
│   └── api/
│       ├── players/
│       │   └── [id]/route.ts  # Player data endpoint
│       ├── search/route.ts    # Player search endpoint
│       └── refresh/route.ts   # Cron-triggered data refresh
│
├── engine/                    # Recommendation engine (no UI imports)
│   ├── recommend.ts           # Entry point: player → START/SIT + reasons
│   ├── signals/
│   │   ├── matchup.ts         # DVP / opponent scoring allowed signal
│   │   ├── injury.ts          # Injury status weight
│   │   └── usage.ts           # Snap count, target share, carries trend
│   └── types.ts               # PlayerSignals, Recommendation, SignalGrade
│
├── ingestion/                 # External API clients
│   ├── sleeper.ts             # Sleeper API wrapper
│   ├── espn.ts                # ESPN unofficial API wrapper
│   ├── dvp.ts                 # Defense vs Position data scraper/client
│   └── normalize.ts           # Unified Player, MatchupData schemas
│
├── cache/
│   ├── kv.ts                  # KV adapter (Vercel KV or in-memory)
│   └── keys.ts                # Cache key constants + TTL values
│
├── components/
│   ├── RecommendationCard.tsx # START/SIT verdict with signal badges
│   ├── PlayerSearch.tsx       # Search input (Client Component)
│   ├── SignalBadge.tsx        # Matchup / Injury / Usage badge
│   └── PositionFilter.tsx     # QB / RB / WR / TE / K / DST tabs
│
└── lib/
    ├── nfl.ts                 # Week number, season utilities
    └── format.ts              # Grade display helpers
```

### Structure Rationale

- **engine/:** Isolated from all UI and HTTP concerns. Inputs are typed signal objects, output is a `Recommendation`. This makes the scoring logic independently testable and replaceable without touching routes or components.
- **ingestion/:** One file per external data source. Each wraps fetch, handles errors, and returns a normalized type. Routes never call external APIs directly — they call ingestion clients.
- **cache/:** Centralized so TTL policy is one place to change. Ingestion clients check cache before hitting external APIs.
- **app/api/:** Thin route handlers. They orchestrate ingestion + engine but contain no business logic themselves.
- **components/:** Split Server vs Client Components explicitly. Data-fetching components stay Server Components; interactive UI (search input, filter tabs) are Client Components.

---

## Architectural Patterns

### Pattern 1: Signal Aggregation with Weighted Composite Score

**What:** The recommendation engine computes independent signals (matchup grade, injury status, usage trend), scores each 0–100, applies position-aware weights, and produces a composite verdict.

**When to use:** When recommendations need transparent, explainable reasoning — each signal can be shown in the UI independently.

**Trade-offs:** Weights are opinionated and will need tuning. More accurate than a single metric but less accurate than an ML model. Right choice for v1: explainability > precision.

**Example:**
```typescript
// engine/recommend.ts
export function recommend(signals: PlayerSignals): Recommendation {
  const matchupScore  = scoreMatchup(signals.dvp);         // 0–100
  const injuryScore   = scoreInjury(signals.injuryStatus); // 0–100
  const usageScore    = scoreUsage(signals.usageTrend);    // 0–100

  const weights = POSITION_WEIGHTS[signals.position];
  const composite =
    matchupScore  * weights.matchup +
    injuryScore   * weights.injury  +
    usageScore    * weights.usage;

  return {
    verdict: composite >= 65 ? "START" : composite >= 45 ? "FLEX" : "SIT",
    composite,
    signals: { matchupScore, injuryScore, usageScore },
    reasons: buildReasons(signals, matchupScore, injuryScore, usageScore),
  };
}
```

### Pattern 2: Cache-First Ingestion

**What:** Every ingestion call checks cache before hitting the external API. On cache miss, fetch, normalize, write to cache with position-appropriate TTL, then return.

**When to use:** Always — external APIs have rate limits, can go down, and are slow. Caching also smooths out the difference between "data freshness the user needs" and "API call frequency."

**Trade-offs:** Stale data risk. Mitigated by Cron-triggered background refresh so cache is populated before users hit a cold miss.

**Example:**
```typescript
// ingestion/sleeper.ts
export async function getPlayer(playerId: string): Promise<Player> {
  const cached = await cache.get(keys.player(playerId));
  if (cached) return cached;

  const raw = await fetch(`https://api.sleeper.app/v1/players/nfl/${playerId}`);
  const player = normalize(await raw.json());

  await cache.set(keys.player(playerId), player, { ttl: TTL.PLAYER_PROFILE });
  return player;
}
```

### Pattern 3: Scheduled Background Refresh (not user-triggered)

**What:** A Vercel Cron job (or GitHub Actions schedule) hits `/api/refresh` on a fixed schedule to pull fresh injury reports, DVP rankings, and player status updates. UI reads from cache only.

**When to use:** Any data that changes on a known external schedule (NFL injury reports: Wed/Thu/Fri/Sat/Sun). Never make the user wait for an external API call inline.

**Trade-offs:** Data is slightly stale (minutes, not seconds). Acceptable for fantasy football — decisions are made on weekly cadence, not real-time. Keeps UI response times fast.

---

## Data Flow

### User Request Flow (Player Detail Page)

```
User searches "Justin Jefferson"
    ↓
PlayerSearch component (Client) → GET /api/search?q=justin+jefferson
    ↓
/api/search route → ingestion/sleeper.searchPlayers()
    ↓ (cache miss path)
Sleeper API → normalize → cache.set(TTL: 6h)
    ↓
Returns [{ id, name, position, team }]
    ↓
User clicks result → /players/[id] (Server Component)
    ↓
Parallel fetches:
  - ingestion/sleeper.getPlayer(id)       → Player profile
  - ingestion/dvp.getMatchupGrade(team, pos, week) → Matchup signal
  - ingestion/espn.getInjuryStatus(id)    → Injury signal
    ↓
engine/recommend(signals) → Recommendation { verdict, reasons }
    ↓
RecommendationCard renders: START badge + 3 signal breakdowns
```

### Background Refresh Flow (Cron Job)

```
Cron trigger (e.g., every 4h during NFL season)
    ↓
GET /api/refresh (server-side, not user-facing)
    ↓
ingestion/dvp.refreshAll()    → cache.set(all DVP data, TTL: 4h)
ingestion/espn.refreshInjuries() → cache.set(injury statuses, TTL: 2h)
    ↓
Next user request hits warm cache → sub-100ms response
```

### Key Data Flows

1. **Player profile:** Sleeper API → normalize to `Player` schema → cache (6h TTL) → API route → Server Component
2. **Matchup grade:** DVP rankings source (FTN / FantasyPros scrape or paid API) → normalized `MatchupGrade { opponent, position, grade: A-F, percentileAllowed }` → cache (4h TTL) → matchup signal scorer
3. **Injury status:** ESPN unofficial API → normalized `InjuryStatus { status: "Active" | "Questionable" | "Doubtful" | "Out" | "IR" }` → cache (2h TTL, shorter because injuries update through the week) → injury signal scorer
4. **Usage trend:** Last N weeks of snap count / target share / carry share from Sleeper or ESPN → rolling average → usage signal scorer

---

## Build Order (Phase Dependencies)

The following ordering reflects hard dependencies — each layer must exist before the next can be built.

```
Phase 1: Data Foundation
  ingestion/ clients (Sleeper player search + profile)
  cache/ adapter (start in-memory, upgrade to KV later)
  normalize.ts (unified Player schema)

      ↓ (players are reachable before recommendations exist)

Phase 2: Engine Core
  engine/signals/ (matchup, injury, usage — each independently testable)
  engine/recommend.ts (composite score + verdict)

      ↓ (recommendations exist before they are displayed)

Phase 3: API Routes
  /api/search, /api/players/[id]
  /api/refresh (wire up to cron later)

      ↓ (routes exist before UI consumes them)

Phase 4: Frontend
  RecommendationCard (verdict + signal badges)
  PlayerSearch (Client Component)
  Player detail page, position list page

      ↓ (functional before scheduling is wired)

Phase 5: Reliability
  Vercel Cron / scheduled refresh
  Error states (API down, no data found)
  Cache TTL tuning per data type
```

**Rationale for this order:** The engine is a pure function — it can be built and tested before any HTTP layer or UI exists. Ingestion clients produce the inputs the engine needs. Routes are thin orchestrators that compose ingestion + engine. The frontend is last because it depends on all other layers being stable. Cron setup is last because it's operational concern, not feature concern.

---

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1 user (personal tool) | In-process LRU cache, no Cron — manual refresh button is fine |
| 10-100 users | Vercel KV (Redis) cache, Vercel Cron for background refresh |
| 1k+ users | Dedicated cache layer, consider edge caching responses at CDN level, rate-limit /api routes |

### Scaling Priorities

1. **First bottleneck:** External API rate limits. Sleeper is generous but ESPN unofficial API is undocumented and may throttle. Cache aggressively. Cache misses should be the exception, not the rule.
2. **Second bottleneck:** DVP data source. If scraped, it breaks on site changes. Migrate to a paid provider (SportsDataIO, FantasyNerds API) before scaling to real users.

---

## Anti-Patterns

### Anti-Pattern 1: Calling External APIs Inline in Server Components

**What people do:** `fetch("https://api.sleeper.app/v1/players/nfl")` directly inside a Server Component on every page render.

**Why it's wrong:** Sleeper's full player endpoint returns ~3MB of data. Every render pays this cost. Latency spikes on every user request. No error handling, no caching.

**Do this instead:** All external calls go through `ingestion/` clients that check cache first. Server Components call ingestion clients, never external APIs directly.

### Anti-Pattern 2: Encoding Recommendation Logic in the UI

**What people do:** Computing the START/SIT verdict or matchup grade inside a React component or a route handler.

**Why it's wrong:** Logic is untestable in isolation, duplicates across pages, and can't be reused for a future API or CLI. Changes to scoring rules require touching UI files.

**Do this instead:** `engine/recommend.ts` is a pure function — `PlayerSignals → Recommendation`. Components and routes only receive and display the output.

### Anti-Pattern 3: Relying Solely on the ESPN Unofficial API

**What people do:** Build the entire ingestion layer on ESPN's undocumented v3 API endpoints, assuming they'll stay stable.

**Why it's wrong:** ESPN broke their API format after the 2023 season with no notice. The API requires browser-cookie auth (`espn_s2`) that can change. Using it as a sole source makes the entire product fragile.

**Do this instead:** Use Sleeper API as the primary player data source (it's documented, stable, and free). Use ESPN only for injury status where needed, with a fallback to Sleeper's injury data. Abstract the data source behind the `ingestion/` interface so the underlying API can be swapped without touching the engine or UI.

### Anti-Pattern 4: Treating DVP as the Only Signal

**What people do:** Grade a matchup solely on points allowed to a position, and ignore player usage.

**Why it's wrong:** A WR with 3 targets in a great matchup is a worse start than a WR with 12 targets in a tough matchup. Usage (target share, snap rate) is predictive; matchup multiplies on top of it. Single-signal recommendations erode user trust when they're obviously wrong.

**Do this instead:** The weighted composite signal architecture above. Surface all three signals to the user so they can assess the tradeoff themselves.

---

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Sleeper API | REST, no auth required, JSON | Primary player data source. Well-documented. Returns full player list on `/v1/players/nfl`. Cache aggressively — full list is large. |
| ESPN Unofficial API | REST, requires `espn_s2` cookie header | Used for injury status. Undocumented. Wrap in try/catch with Sleeper fallback. Endpoints change without notice. |
| DVP / Matchup Data | REST (FantasyNerds) or scrape (FantasyPros, FTN) | Defense vs Position data. FantasyNerds API has a free tier and documents DVP. FTN requires scraping. Recommend FantasyNerds for reliability. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Ingestion → Engine | Direct TypeScript import, normalized types | `ingestion/normalize.ts` defines the contract. Engine never imports from `ingestion/`. Routes assemble signals and pass to engine. |
| Route → Ingestion | Direct import | Routes call ingestion functions. Never the reverse. |
| Route → Engine | Direct import | Routes pass assembled signals to engine, receive Recommendation. |
| Component → Route | HTTP fetch (Server Component) or SWR (Client Component) | Components never import engine or ingestion directly. |
| Cron → Route | HTTP GET to `/api/refresh` | Cron is external — it triggers the route the same way a user would, no special coupling. |

---

## Sources

- [Fantasy Sports Platform Architecture: Real-Time Data Pipelines, Scoring Engines, and AI Analytics](https://www.isportsapi.com/en/blog/others-2279-fantasy-sports-platform-architecture:-real-time-data-pipelines,-scoring-engines,-and-ai-analytics.html) — component layer patterns, scoring engine design (MEDIUM confidence)
- [Sleeper API Documentation](https://docs.sleeper.com/) — official, stable, free NFL player data API (HIGH confidence)
- [ESPN Hidden API Guide — Zuplo](https://zuplo.com/learning-center/espn-hidden-api-guide) — ESPN API undocumented nature, auth requirements (MEDIUM confidence)
- [Fantasy Sports Data APIs: Sleeper vs Others — SportsFirst](https://www.sportsfirst.net/post/fantasy-sports-data-apis-sleeper-api-vs-other-sports-apis-compared) — API comparison (MEDIUM confidence)
- [DVOA Explainer — FTN Fantasy](https://ftnfantasy.com/nfl/dvoa-explainer) — matchup grading methodology (HIGH confidence)
- [Defense vs. Position Rankings — Establish the Run](https://establishtherun.com/establish-the-run-nfl-dvp/) — DVP as standard matchup signal (HIGH confidence)
- [Next.js Best Practices 2025 — Raftlabs](https://www.raftlabs.com/blog/building-with-next-js-best-practices-and-benefits-for-performance-first-teams/) — Server/Client Component split, caching patterns (HIGH confidence)
- [React Server Components 2025 — CoderTrove](https://www.codertrove.com/articles/react-server-components-2025-nextjs-performance) — RSC data fetching patterns (HIGH confidence)
- [ESPN API endpoints gist — GitHub](https://gist.github.com/nntrn/ee26cb2a0716de0947a0a4e9a157bc1c) — community-maintained ESPN endpoint list (LOW confidence — community, not official)

---
*Architecture research for: Fantasy Football Analytics — Start/Sit Tool*
*Researched: 2026-03-19*
