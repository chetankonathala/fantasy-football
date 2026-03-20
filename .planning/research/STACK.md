# Stack Research

**Domain:** Fantasy football analytics web app (start/sit recommendations)
**Researched:** 2026-03-19
**Confidence:** HIGH (core framework, NFL data APIs verified via official docs and GitHub; supporting libraries verified via official sources)

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Next.js | 16.2 | Full-stack React framework | App Router + React Server Components lets data fetching live on the server, keeping API keys out of the browser and reducing round-trips. Server Actions replace a separate REST layer for mutations. Turbopack makes dev fast. The most hirable React skill in 2026. |
| React | 19.x | UI layer | Ships with Next.js 16. React 19 Server Components are the right model for a read-heavy analytics page: fetch data server-side, stream to client, no client-side waterfall. |
| TypeScript | 5.x | Type safety | Mandatory. ESPN player IDs, matchup grades, and injury enums benefit enormously from typed schemas shared between data layer and UI. |
| Tailwind CSS | 4.x | Styling | v4 ships with zero-config auto-detection and a CSS-first setup (`@import "tailwindcss"`, no `tailwind.config.js` needed). 5x faster full builds. Pairs natively with shadcn/ui. |
| shadcn/ui | latest (CLI-installed) | Component library | Not a dependency — components are copied into your `src/components/ui/`. Built on Radix UI primitives + Tailwind v4. Dashboards, tables, badges, and tooltips are exactly the components needed for a player card / recommendation UI. 75K+ GitHub stars; effectively the default for Next.js projects in 2026. |

### NFL Data APIs

This is the most consequential choice in the stack. Options compared below:

| API | Cost | Auth Required | What It Provides | Reliability | Verdict |
|-----|------|---------------|------------------|-------------|---------|
| **nflreadpy (nflverse)** | Free | None | Play-by-play, snap counts, target share, weekly stats, rosters, schedules, injury designations (from official NFL reports) | HIGH — backed by nflverse, CC-BY 4.0 licensed | **Primary source for historical and in-season usage stats** |
| **Sleeper API** | Free | None | Player metadata, injury status field, roster/league data | HIGH — public REST API, 1000 req/min limit | **Primary source for real-time injury status and player IDs** |
| **Tank01 (RapidAPI)** | Free tier: 1,000 req/month; Pro: $10/mo (1,000/day); Ultra: $25/mo (15,000/day) | RapidAPI key | Live in-game stats, injury updates, fantasy projections (hourly), matchup data | MEDIUM — third-party aggregator | **Optional: use for live game-day updates if needed** |
| **Fantasy Nerds API** | Paid (pricing not published, free trial available) | API key | Defense rankings by position, injury reports, weekly projections, matchup grades | MEDIUM | **Optional: best pre-built matchup difficulty grades if budget allows** |
| **ESPN unofficial API** | Free | ESPN cookies for private leagues | League/roster data, player IDs, weekly matchups | LOW — undocumented, ESPN can break it at any time; auth cookies expire | **Avoid for production data fetching. Use only for ESPN player ID cross-referencing.** |
| **SportRadar** | $500–$1000+/mo (enterprise contract) | API key | Authoritative NFL data, live stats | HIGH | **Overkill for a personal v1 tool. Revisit if commercializing.** |

**Recommended data strategy:**
- **Sleeper API** for player metadata + injury status (free, stable, no auth)
- **nflreadpy** (Python, run via a backend ingestion job) for snap counts, target share, weekly points, and schedule data — cache results in SQLite/Postgres
- Derive matchup grades yourself from nflverse's play-by-play: points allowed by position over the last 4 weeks is a reliable proxy for matchup difficulty
- Do NOT depend on the ESPN unofficial API for data — use it only to map player names to ESPN IDs if needed

### Backend

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python (FastAPI) | FastAPI 0.115+, Python 3.12 | Data ingestion API and scoring engine | Python is where nflreadpy, pandas, and data science tooling lives. FastAPI gives async HTTP endpoints with automatic OpenAPI docs. The start/sit scoring logic (matchup grade + injury weight + usage trend) is cleanest to write and test in Python. |
| APScheduler | 3.x | Background jobs for weekly data refresh | Lightweight cron-style scheduler that runs inside the FastAPI process. No message broker required. Sufficient for once-daily nflreadpy ingestion jobs and weekly schedule refreshes. Use Celery only if you scale to multi-worker background processing. |
| SQLite (dev) / PostgreSQL (prod) | SQLite 3 / Postgres 16 | Player stats and recommendation cache | SQLite is zero-config for local development. Migrate to Postgres when deploying. The data volume for one NFL season of weekly stats is tiny (< 5MB). |

### Frontend Data Fetching

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| TanStack Query (React Query) | v5 | Client-side data fetching, caching, background refresh | Use for any data the UI polls or refreshes (injury status, weekly recommendations). DevTools are invaluable for debugging stale-time behavior. 12.3M weekly downloads vs SWR's 7.7M; richer feature set (garbage collection, offline sync, fine-grained stale time). |

### Data Visualization

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Recharts | 2.x | Usage trend sparklines, points-per-game bars | Best balance of DX and customizability for React. Declarative API, SVG-based. Use for snap count trends, target share over last 4 weeks, and scoring history. Not for real-time streaming charts — that would need a Canvas library. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| pnpm | Package manager | Faster than npm, better monorepo support if you split frontend/backend |
| ESLint + Prettier | Linting and formatting | Use `eslint-config-next` (ships with Next.js); add `prettier-plugin-tailwindcss` to auto-sort class names |
| Zod | Schema validation | Validate API responses from Sleeper and Tank01 at runtime. Share Zod schemas between FastAPI response models and Next.js fetch calls. |
| Vitest | Unit testing | Faster than Jest for Next.js/Vite-adjacent projects. Test recommendation scoring logic in Python with pytest; test UI logic with Vitest. |
| pytest | Python testing | Test the scoring engine (start/sit logic) and data ingestion functions |
| uv | Python package manager | Recommended by nflreadpy maintainers; significantly faster than pip |

---

## Installation

```bash
# Frontend — create Next.js 16 app with Tailwind v4 and TypeScript
npx create-next-app@latest fantasy-analytics --typescript --tailwind --app --turbopack
cd fantasy-analytics

# UI components
npx shadcn@latest init
npx shadcn@latest add card badge table tooltip

# Data fetching
npm install @tanstack/react-query @tanstack/react-query-devtools

# Charts
npm install recharts

# Validation
npm install zod

# Dev dependencies
npm install -D vitest @vitejs/plugin-react prettier prettier-plugin-tailwindcss eslint-config-next
```

```bash
# Backend — Python environment
uv init fantasy-analytics-api
cd fantasy-analytics-api

# Core dependencies
uv add fastapi uvicorn[standard] nflreadpy pandas apscheduler httpx

# Database
uv add sqlalchemy alembic

# Dev dependencies
uv add --dev pytest pytest-asyncio httpx ruff
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Next.js 16 | Remix | If you prioritize progressive enhancement and server-first routing over ecosystem size. Remix is arguably a better mental model for loader/action data patterns. For v1 solo project, Next.js wins on ecosystem and documentation breadth. |
| Next.js 16 | SvelteKit | If you prefer Svelte's simpler component model and smaller bundle. No strong reason to switch here; React is better for the shadcn/ui + Recharts ecosystem. |
| TanStack Query v5 | SWR | If you need minimal bundle size. SWR is simpler but lacks garbage collection, fine-grained stale time, and DevTools. Not worth the feature tradeoff for a polling-heavy analytics app. |
| FastAPI (Python) | Express/Node.js backend | If you want a single-language stack. Node cannot run nflreadpy directly. You'd lose the Python data science ecosystem for scoring logic. Not recommended. |
| APScheduler | Celery + Redis | Use Celery if you need multi-worker task distribution or a dedicated task queue with retries and failure tracking. Overkill for once-daily data refresh at v1. |
| Recharts | Chart.js | Chart.js is canvas-based (better for mobile), but requires a React wrapper. Recharts is built for React and uses SVG, which is easier to style with Tailwind. |
| Recharts | Victory | Victory supports React Native. No need here — web-first. Recharts has a gentler API. |
| SQLite/Postgres | Firebase / Supabase | Supabase is fine if you want hosted Postgres with a REST API for free. Adds infrastructure dependency. For a personal v1 tool, local SQLite → Postgres on a $5/mo VPS is simpler to own. |
| nflreadpy | nfl_data_py | nfl_data_py was archived September 25, 2025. Do not use it. nflreadpy is the active successor. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `nfl_data_py` | Archived by maintainer September 25, 2025. No future updates or security fixes. | `nflreadpy` — same nflverse data, actively developed, v0.1.5 released November 2025 |
| ESPN unofficial API as primary data source | Undocumented endpoints change without notice. ESPN changed auth requirements in August 2025 (now requires `espn_s2` cookie from browser session). Any production data fetch depending on this will break silently mid-season. | Sleeper API for player metadata + injury, nflreadpy for stats |
| Redux Toolkit | Significant boilerplate overhead for a read-heavy analytics dashboard. TanStack Query handles all server state; Zustand handles the tiny amount of local UI state (selected player, active week). RTK's complexity is not justified at v1 scale. | TanStack Query v5 for server state; Zustand for local UI state if needed |
| `pages/` router in Next.js | Legacy. App Router with Server Components is the current model — it's what shadcn/ui, TanStack Query integration patterns, and all 2025+ Next.js documentation targets. | App Router (`app/` directory) |
| SportRadar NFL API | Enterprise pricing ($500–$1000+/mo) is not appropriate for a personal analytics tool. | nflreadpy (free) + Tank01 RapidAPI ($10/mo for 1K req/day) covers all needed data at a fraction of the cost |
| React Class Components | Dead pattern in 2026. shadcn/ui, TanStack Query, and Recharts all expect functional components with hooks. | Functional components + hooks |

---

## Stack Patterns by Variant

**If this stays a personal tool (v1 scope):**
- Frontend: Next.js 16 + shadcn/ui + Tailwind v4, deployed on Vercel (free tier)
- Backend: FastAPI + SQLite, running locally or on a $5/mo VPS (Railway, Fly.io)
- Data: Sleeper API (free) + nflreadpy ingested weekly via APScheduler
- No auth, no database migrations needed for a season's worth of data

**If this opens to other users (v2 scope):**
- Add Postgres (Neon or Supabase for managed hosting)
- Add Clerk or Auth.js for authentication
- Add Celery + Redis for background job queuing
- Consider Tank01 Ultra ($25/mo) for real-time injury updates during gameday
- Consider Fantasy Nerds API for pre-computed matchup grades (reduces own scoring engine complexity)

**If matchup grades need to be computed live:**
- Build a weekly ingestion job (APScheduler, Friday morning) that pulls nflverse pbp data
- Compute "points allowed to position over last 4 weeks" per team per position
- Store as a `matchup_grades` table; serve via FastAPI endpoint
- This is fully achievable with nflreadpy + pandas — no paid API required

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| Next.js 16.2 | React 19.x, Tailwind CSS 4.x, shadcn/ui latest | Tailwind v4 requires `@tailwindcss/postcss` instead of `postcss` plugin — check shadcn init output |
| shadcn/ui (latest) | React 19, Next.js 16, Tailwind CSS v4 | shadcn officially supports React 19 as of 2025; use `npx shadcn@latest` not `shadcn-ui` (old package name) |
| TanStack Query v5 | React 18 and 19 | v5 is a breaking change from v4; do not mix with older React Query docs |
| Recharts 2.x | React 18 and 19 | Recharts 3.x is in alpha as of 2025 — stay on 2.x for stability |
| nflreadpy 0.1.5 | Python 3.10+ | Marked "experimental" lifecycle; pin to a version, check GitHub for breaking changes each season |
| APScheduler 3.x | FastAPI (any), Python 3.9+ | Use `AsyncIOScheduler` (not `BackgroundScheduler`) inside an async FastAPI app |

---

## Sources

- [nflreadpy GitHub — nflverse/nflreadpy](https://github.com/nflverse/nflreadpy) — version confirmed (v0.1.5, Nov 2025), archived status of nfl_data_py confirmed (Sep 25, 2025). HIGH confidence.
- [Sleeper API docs — docs.sleeper.com](https://docs.sleeper.com/) — injury status fields confirmed, rate limits confirmed (1000 req/min). HIGH confidence.
- [Next.js 16.2 release notes — nextjs.org/blog/next-16-2](https://nextjs.org/blog/next-16-2) — current stable version confirmed (16.2, March 18 2026). HIGH confidence.
- [Tailwind CSS v4 release — tailwindcss.com/blog/tailwindcss-v4](https://tailwindcss.com/blog/tailwindcss-v4) — v4 stable, CSS-first config, auto content detection. HIGH confidence.
- [shadcn/ui docs — ui.shadcn.com](https://ui.shadcn.com/docs/react-19) — React 19 compatibility confirmed. HIGH confidence.
- [TanStack Query comparison — tanstack.com/query/v5/docs/react/comparison](https://tanstack.com/query/v5/docs/react/comparison) — feature comparison with SWR official. HIGH confidence.
- [Tank01 NFL API — RapidAPI](https://rapidapi.com/tank01/api/tank01-fantasy-stats) — pricing and features confirmed. MEDIUM confidence (third-party aggregator).
- [Fantasy Nerds API docs — api.fantasynerds.com/docs/nfl](https://api.fantasynerds.com/docs/nfl) — endpoints confirmed, pricing unclear. MEDIUM confidence.
- [ESPN unofficial API — community docs](https://gist.github.com/nntrn/ee26cb2a0716de0947a0a4e9a157bc1c) — auth changes (espn_s2 cookie) confirmed. LOW confidence (unofficial, undocumented).
- [Zustand vs RTK 2026 — frontend-junction.com](https://www.frontend-junction.com/blog/zustand-vs-redux-toolkit-2026) — trend data. MEDIUM confidence.
- [APScheduler FastAPI patterns — FastAPI docs](https://fastapi.tiangolo.com/tutorial/background-tasks/) — background task patterns. HIGH confidence.
- [Strapi: Next.js vs Remix 2025](https://strapi.io/blog/next-js-vs-remix-2025-developer-framework-comparison-guide) — framework comparison. MEDIUM confidence.

---

*Stack research for: Fantasy Football Analytics — start/sit recommendation web app*
*Researched: 2026-03-19*
