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
- [x] **Phase 3: Full-Stack Core** - API routes, player search, and complete recommendation UI wired end-to-end (completed 2026-03-30)
- [ ] **Phase 4: Reliability & Enhancement** - Scheduled refresh automation, player comparison, Vegas overlay, and weather signals
- [ ] **Phase 5: Dynasty Trade Analyzer** - Full trade package builder with dynasty/keeper values, win/lose/fair verdict, and pick capital valuation
- [ ] **Phase 6: Dynasty Draft Room** - Full dynasty rankings, rookie grades, keeper analysis, and live snake-draft board

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
**Plans:** 4/4 plans complete
Plans:
- [ ] 03-01-PLAN.md — FastAPI routes (search + player detail) with TDD tests, Sleeper projected-points fetch
- [ ] 03-02-PLAN.md — Next.js scaffolding with Eagles dark theme, SearchBar autocomplete, home page
- [ ] 03-03-PLAN.md — RecommendationCard with verdict, signals, format selector, FreshnessStamp
- [ ] 03-04-PLAN.md — End-to-end verification checkpoint (servers + human visual review)

### Phase 4: Reliability & Enhancement
**Goal**: The core recommendation loop is hardened with automated background refresh and extended with player comparison, Vegas implied totals, and weather flags
**Depends on**: Phase 3
**Requirements**: COMP-01, ENRI-01, ENRI-02
**Success Criteria** (what must be TRUE):
  1. User can navigate to a comparison view, enter two players, and see their recommendation signals side-by-side (verdict, matchup grade, injury status, usage trend, projected points)
  2. The recommendation page shows a Vegas implied team total alongside the matchup grade so the user can factor game environment into the decision
  3. Outdoor games with meaningful weather (wind or precipitation) show a weather flag on the recommendation card as a pass-game suppression signal
**Plans:** 2/3 plans executed
Plans:
- [ ] 04-01-PLAN.md — GameLine model + migration, Odds API fetch, Open-Meteo weather fetch, refresh.py integration
- [ ] 04-02-PLAN.md — Refactor _build_recommendation helper, add /compare endpoint with tests
- [ ] 04-03-PLAN.md — Wire Vegas/weather into API responses, build comparison frontend page, visual verification

### Phase 5: Dynasty Trade Analyzer
**Goal**: A dynasty/keeper player can build full trade packages on both sides, get a win/lose/fair verdict with plain-English reasoning, and evaluate pick capital alongside player value
**Depends on**: Phase 4
**Requirements**: TRAD-01, TRAD-02, TRAD-03, TRAD-04, TRAD-05
**Success Criteria** (what must be TRUE):
  1. User can build a trade package by adding/removing multiple players and draft picks (with round + year) on each side
  2. Trade analyzer returns a win/lose/fair verdict with per-player and per-pick reasoning explaining who gains positional value, age-curve advantage, and pick capital
  3. Dynasty mode pulls live trade values from KeepTradeCut for all players and picks
  4. Keeper mode shows each player's keeper acquisition cost vs. dynasty value so the net gain/loss of a trade is clear
  5. Pick values use the KTC pick value chart with year and round (e.g., "2026 1st" scores higher than "2028 1st")
**Plans**: TBD

### Phase 6: Dynasty Draft Room
**Goal**: A dynasty/keeper player can review full dynasty and rookie rankings pre-draft, see keep/cut recommendations for their roster, and run a live snake draft board during their actual draft
**Depends on**: Phase 5
**Requirements**: DRFT-01, DRFT-02, DRFT-03, DRFT-04, DRFT-05
**Success Criteria** (what must be TRUE):
  1. Full dynasty rankings board displays all relevant players ranked by long-term value with age-curve grade and position tier label
  2. Rookie rankings tab shows incoming class with positional grade, landing spot assessment, and dynasty ceiling/floor rating
  3. Keeper analysis page shows each player with their keeper cost and dynasty value side-by-side, with a keep/cut recommendation
  4. Live draft board allows marking players as drafted in real-time, queuing targets, and tracking own picks across all rounds
  5. Draft board supports configurable snake format (8-14 teams) with round-by-round pick order computed automatically
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Data Foundation | 3/3 | Complete    | 2026-03-22 |
| 2. Recommendation Engine | 2/2 | Complete    | 2026-03-25 |
| 3. Full-Stack Core | 4/4 | Complete   | 2026-03-30 |
| 4. Reliability & Enhancement | 3/3 | Complete    | 2026-04-16 |
| 5. Dynasty Trade Analyzer | TBD/TBD | Complete    | 2026-04-16 |
| 6. Dynasty Draft Room | 3/3 | Complete    | 2026-04-17 |
