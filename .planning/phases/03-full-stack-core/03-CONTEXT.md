# Phase 3: Full-Stack Core - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire the recommendation engine end-to-end: FastAPI routes serving player search and recommendation data, a Next.js frontend with player search autocomplete, and a recommendation card showing all signals (verdict, reasoning, matchup grade, injury status, usage trends, projected points, scoring format selector, data freshness timestamp). No roster upload, no multi-user features — individual player lookup only.

</domain>

<decisions>
## Implementation Decisions

### Search Interaction
- Live autocomplete after 2+ characters typed — queries player DB on each keystroke
- Each result shows: player name + position + team (e.g., "Justin Jefferson — WR, MIN")
- Max 5 autocomplete suggestions shown
- Selecting a result navigates to `/player/[id]` — no inline card rendering
- If no players match: show "No players found" message in the dropdown (not silent)

### Page Structure
- Two routes only: `/` (home) and `/player/[id]` (player detail)
- Home page: centered search bar, minimal — no featured players, no clutter
- Player page: player name/team/position header, then recommendation card below
- Search bar persists in the nav/header on all pages — user can search another player without returning home
- Verdict is the hero element on the card — big, bold, color-coded at the top; reasoning and signals below

### Frontend Styling
- **Framework**: Next.js (locked from Phase 1)
- **Styling**: Tailwind CSS
- **Components**: shadcn/ui (copy-paste components, no vendor lock-in) or raw Tailwind — Claude's discretion
- **Mode**: Dark mode only
- **Theme**: Philadelphia Eagles
  - Primary: midnight green `#004C54`
  - Background: black / near-black
  - Accents: silver `#A5ACAF`, white
  - Verdict colors: START = green, SIT = red, FLEX = yellow/amber (contrast-safe on dark bg)

### Projected Points
- Fetch weekly projections from Sleeper API in Phase 3 — wire up now so the card shows projected points
- Add a `projected_points` fetch to the data layer (alongside existing Sleeper injury/status fetch in `src/fantasy/fetch/sleeper.py`)
- Pass fetched value into `score_player()` as `signals.projected_points`

### Scoring Format Selector
- Present on the recommendation card (not global/persistent)
- Changing format updates verdict + projected points without a page reload (client-side state)
- Default: PPR

### Data Freshness Timestamp
- Source: `Player.updated_at` column (already in DB, set on upsert)
- Display on card: human-readable relative time (e.g., "Updated 45 minutes ago")

### Claude's Discretion
- Exact card component layout and spacing
- Whether to use shadcn/ui vs raw Tailwind components
- API pagination/limit behavior for search endpoint
- Loading and error state design
- Exact Tailwind class values

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Engine contract (API must return this shape)
- `src/fantasy/engine.py` — `Recommendation` dataclass (verdict, score, reasons, low_confidence, scoring_format); `score_player()` function signature; `SkillSignals`, `KickerSignals`, `DSTSignals` input types
- `src/fantasy/db/models.py` — `Player` model (full_name, position, team, injury_status, practice_participation, updated_at, week1-4 snap/target/carry, matchup_id); `Matchup` model (opponent_rank, dvp_score)

### Data layer
- `src/fantasy/fetch/sleeper.py` — Existing Sleeper fetch client; projected_points fetch must be added here
- `src/fantasy/normalize.py` — Normalization layer; defines what data is guaranteed available from DB

### Requirements
- `.planning/REQUIREMENTS.md` — Phase 3 requirements: SRCH-01, SRCH-02, RECD-04, RECD-05, DATA-02
- `.planning/ROADMAP.md` §Phase 3 — Success criteria (5 criteria); defines exactly what must be true at phase completion

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/fantasy/engine.py` `score_player()` — ready to call from FastAPI route; accepts `PlayerSignals` + `ScoringFormat`, returns `Recommendation`
- `src/fantasy/db/models.py` `Player` — has all fields needed for search (full_name, position, team) and recommendation card (injury_status, practice_participation, snap/target/carry x4 weeks, updated_at)
- `src/fantasy/fetch/sleeper.py` — Sleeper API client already exists; extend it to fetch projected_points

### Established Patterns
- FastAPI chosen in Phase 1 as the web framework — `main.py` is currently a stub, Phase 3 wires it up
- SQLAlchemy session pattern established in Phase 1 — use same session factory for API queries
- `week1` = most recent, `week4` = oldest — maintain in API response field names

### Integration Points
- `main.py` — FastAPI app entry point; Phase 3 adds routes here
- `src/fantasy/db/base.py` — SQLAlchemy Base + session factory; API routes use this for DB access
- Engine output (`Recommendation`) is the Phase 3 API contract — shape is frozen, API serializes it as-is

</code_context>

<specifics>
## Specific Ideas

- Eagles theme: midnight green `#004C54`, black background, silver `#A5ACAF` accents — consistent across all pages
- Verdict should be the first thing the eye lands on — large, bold, color-coded (green/red/amber)
- "Updated 45 minutes ago" style freshness display (relative time, not raw ISO timestamp)
- Search should feel instant — 2-char trigger, no submit button needed

</specifics>

<deferred>
## Deferred Ideas

- **Roster upload + full lineup recommendation** — User wants to upload their fantasy team and get start/sit decisions for the whole roster at once, with position-group comparisons (who to start at RB2, etc.). Powerful feature, needs its own phase after Phase 3 foundation is proven.
- **Community platform** — Fan bases interacting, sharing start/sit opinions, debating rosters. Needs user accounts, feeds, comments, reactions, league affiliation. Future v2 scope. Foundation (no hardcoded single-user assumptions) should be kept in mind during Phase 3 to avoid blockers later.

</deferred>

---

*Phase: 03-full-stack-core*
*Context gathered: 2026-03-25*
