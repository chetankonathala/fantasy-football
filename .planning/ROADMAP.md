# Roadmap: Fantasy Football Analytics

## Overview

This roadmap delivers a personal start/sit recommendation tool in four phases, each completing a coherent capability. The dependency chain is strict: the data pipeline must be proven before the engine, the engine must lock its output schema before any API route exposes it, and the routes must be stable before the frontend is built against them. Enhancements (player comparison, Vegas overlay, weather flag) land last, on top of a validated core.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Data Foundation** - Ingest, normalize, and continuously refresh all player and matchup data (completed 2026-03-22)
- [x] **Phase 2: Recommendation Engine** - Pure scoring function that converts signals into a verified START/SIT/FLEX verdict with structured reasoning (completed 2026-03-25)
- [ ] **Phase 3: Full-Stack Core** - API routes, player search, and complete recommendation UI wired end-to-end
- [ ] **Phase 4: Reliability & Enhancement** - Scheduled refresh automation, player comparison, Vegas overlay, and weather signals

## Phase Details

### Phase 1: Data Foundation
**Goal**: Current, well-structured player and matchup data is available for every fantasy-relevant player, refreshed automatically throughout the week, with a safe off-season state
**Depends on**: Nothing (first phase)
**Requirements**: DATA-01, DATA-03
**Success Criteria** (what must be TRUE):
  1. Injury and practice status for all active NFL players can be fetched from Sleeper API and stored in the local database with correct field types
  2. Weekly matchup data (opponent rank vs. position) and usage stats (snap %, target share, carry share) for the last 4 weeks can be retrieved via nflreadpy and joined to players using the nflverse canonical player ID crosswalk
  3. The data refresh job runs on a schedule and updates injury status at least every 2 hours during the NFL week without manual intervention
  4. Querying the system during the NFL off-season returns a clear "season not active" flag rather than stale or empty data
**Plans:** 3/3 plans complete
Plans:
- [ ] 01-01-PLAN.md — Project scaffolding, DB models (Player + Matchup), Alembic, upsert helpers, test infrastructure
- [ ] 01-02-PLAN.md — Fetch layer (Sleeper API client, nflreadpy wrappers, DVP computation) and normalization layer
- [ ] 01-03-PLAN.md — Refresh orchestration script with off-season guard, error handling, logging, and cron schedule

### Phase 2: Recommendation Engine
**Goal**: A pure, isolated scoring function takes typed player signals and returns a deterministic START/SIT/FLEX verdict plus a structured 3-5 factor reasoning array, covering all six fantasy positions
**Depends on**: Phase 1
**Requirements**: RECD-01, RECD-02, RECD-03, RECD-06, RECD-07, RECD-08, POS-01, POS-02, POS-03
**Success Criteria** (what must be TRUE):
  1. Given typed signal inputs (matchup grade, injury status, usage trend, projected points), the engine returns a single START / SIT / FLEX verdict and a reasons array of 3-5 plain-English factors
  2. The scoring logic applies position-aware weights: skill positions (QB, RB, WR, TE) use the full signal set; K and DST use matchup-only signals
  3. Scoring format (PPR / half-PPR / standard) changes the target share weight and updates the projected points and verdict accordingly
  4. Players with fewer than 4 games of data receive a low-confidence flag in the output that surfaces in the recommendation
  5. The engine is covered by a test suite that verifies each signal combination in isolation and the composite verdict for representative inputs per position
**Plans:** 2/2 plans complete
Plans:
- [ ] 02-01-PLAN.md — Type contracts (enums, dataclasses, stubs) and full RED test suite (16 tests)
- [ ] 02-02-PLAN.md — Complete engine implementation (scoring logic, reasoning builder, format modifiers) — all tests GREEN

### Phase 3: Full-Stack Core
**Goal**: A user can search for any NFL player by name, select them, and see a complete recommendation card with all signals — verdict, reasoning, matchup grade, injury status, usage trends, projected points, scoring format selector, and data freshness timestamp — sourced from live data
**Depends on**: Phase 2
**Requirements**: SRCH-01, SRCH-02, RECD-04, RECD-05, DATA-02
**Success Criteria** (what must be TRUE):
  1. User can type a partial player name into a search field and see autocomplete suggestions drawn from the player database
  2. User can select a player from search results and land on a recommendation page showing the START/SIT/FLEX verdict and 3-5 plain-English reasoning factors
  3. The recommendation page shows the player's injury and practice status (Q/D/Out) and usage trends (snap %, target share or carry share) for the last 3-4 weeks
  4. Every recommendation card displays a data freshness timestamp so the user can see how current the underlying data is
  5. The scoring format selector (PPR / half-PPR / standard) is present and changing it updates the verdict and projected points without a page reload
**Plans**: TBD

### Phase 4: Reliability & Enhancement
**Goal**: The core recommendation loop is hardened with automated background refresh and extended with player comparison, Vegas implied totals, and weather flags
**Depends on**: Phase 3
**Requirements**: COMP-01, ENRI-01, ENRI-02
**Success Criteria** (what must be TRUE):
  1. User can navigate to a comparison view, enter two players, and see their recommendation signals side-by-side (verdict, matchup grade, injury status, usage trend, projected points)
  2. The recommendation page shows a Vegas implied team total alongside the matchup grade so the user can factor game environment into the decision
  3. Outdoor games with meaningful weather (wind or precipitation) show a weather flag on the recommendation card as a pass-game suppression signal
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Data Foundation | 3/3 | Complete    | 2026-03-22 |
| 2. Recommendation Engine | 2/2 | Complete    | 2026-03-25 |
| 3. Full-Stack Core | 0/TBD | Not started | - |
| 4. Reliability & Enhancement | 0/TBD | Not started | - |
