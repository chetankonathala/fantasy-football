# Phase 1: Data Foundation - Context

**Gathered:** 2026-03-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Ingest, normalize, and continuously refresh all player and matchup data. Current, well-structured player and matchup data is available for every fantasy-relevant player, refreshed automatically throughout the week, with a safe off-season state. The recommendation engine, API routes, and UI are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Tech Stack
- Language: Python (nflreadpy/nflverse are Python-native — no bridging layer needed)
- Web framework: FastAPI (async, auto-generates OpenAPI docs, standard pairing for Phase 3)
- Dependency management: uv + pyproject.toml
- Frontend (for Phase 3 planning alignment): Next.js (React)

### Database & Storage
- Database: SQLite (`/data/fantasy.db`) — zero-ops, single file, sufficient for ~2000 active NFL players
- ORM: SQLAlchemy ORM
- Migrations: Alembic (versioned schema changes across phases)
- Refresh strategy: Upsert by canonical player ID (INSERT OR REPLACE / ON CONFLICT DO UPDATE) — never full wipe
- History: Current snapshot only — no historical row retention (historical tracking is v2 scope per HIST-01/HIST-02)
- DB file lives in a separate `/data/` directory, gitignored

### Refresh Scheduling
- Mechanism: System cron job calling a standalone Python script (`scripts/refresh.py`)
- Failure handling: Log error, retain last good data — next scheduled run retries automatically
- Off-season behavior: Cron always fires; fetch logic checks if NFL season is active and returns early with a "season not active" flag
- Logging: `logs/refresh.log` with rotation (7-day retention)

### Schema & Normalization
- Player table stores both `nflverse_id` (canonical) and `sleeper_id` — crosswalk run once at setup, both IDs available for lookups
- Usage stats (snap %, target share, carry share) stored as 4 explicit week columns per stat: `week1_snap_pct`, `week2_snap_pct`, `week3_snap_pct`, `week4_snap_pct` (and equivalents for target/carry share)
- Matchup data (DVP grade, opponent rank by position) lives in a separate `matchup` table: `(week, team, position, opponent_rank, dvp_score)` — player table holds a foreign key to current week matchup; avoids duplicating matchup data per player
- Off-season state: app-level check via date logic against NFL season schedule — no DB flag

### Claude's Discretion
- Exact table column names and types beyond the patterns above
- Precise DVP score computation formula (points allowed vs. position, last 4 weeks from nflreadpy)
- nflreadpy version pinning and schema validation approach (pre-condition: pin to v0.1.5, validate play-by-play schema before committing)
- Exact cron schedule expression
- Log rotation implementation details

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

No external specs or ADRs exist yet — requirements are fully captured in decisions above and the planning docs below.

### Requirements
- `.planning/REQUIREMENTS.md` — DATA-01, DATA-03 are the Phase 1 requirements; defines injury refresh cadence and off-season state behavior
- `.planning/ROADMAP.md` — Phase 1 success criteria (4 criteria); defines exactly what must be true at phase completion

### Pre-conditions (from STATE.md)
- `.planning/STATE.md` — Blockers section: nflreadpy must be pinned to v0.1.5 and play-by-play schema validated against DVP computation approach before Phase 1 can be considered done

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project. No existing source code.

### Established Patterns
- None yet — Phase 1 establishes the patterns that subsequent phases inherit.

### Integration Points
- Phase 2 (Recommendation Engine) will read from the SQLite DB via SQLAlchemy models — the schema locked in Phase 1 is the contract Phase 2 builds against
- Phase 3 (Full-Stack Core) will add FastAPI routes on top of Phase 1's data layer — FastAPI chosen in Phase 1 so the foundation is already in place

</code_context>

<specifics>
## Specific Ideas

No specific UI or interaction references for this phase — it is a pure data pipeline phase with no user-facing surface.

Key specifics from pre-build decisions:
- Player ID joins MUST use nflverse ff_playerids crosswalk — never join on player name strings
- DVP matchup grades computed from nflreadpy play-by-play (points allowed by position, last 4 weeks) — not scraped from FantasyPros or another external grade source

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-data-foundation*
*Context gathered: 2026-03-20*
