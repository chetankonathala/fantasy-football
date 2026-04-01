---
phase: 04-reliability-enhancement
plan: "02"
subsystem: api
tags: [fastapi, sqlalchemy, pytest, tdd]

# Dependency graph
requires:
  - phase: 03-full-stack-core
    provides: Player and Matchup models, /player/{id} route, score_player engine
provides:
  - /compare route returning {player_a, player_b} recommendation payloads
  - _build_recommendation(player_id, format, db) private helper reused by both routes
  - 5 new /compare tests (15 total) with full coverage of 404 and format scenarios
affects: [05-trade-analyzer, 06-dynasty-draft-room]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Extract-helper-then-compose: shared logic extracted to private helper, route delegates entirely"
    - "Validate-all-before-build: both players validated for existence before any recommendation is built, preventing partial results"

key-files:
  created: []
  modified:
    - main.py
    - tests/test_api.py

key-decisions:
  - "Validate both players exist before calling _build_recommendation for either — no partial comparisons returned"
  - "Expose missing player IDs in 404 detail message for easier debugging (Player(s) not found: {ids})"

patterns-established:
  - "Private helper pattern: _build_recommendation is the canonical single-player payload builder; future routes should call it rather than duplicating logic"
  - "Dual-validation pattern: when an endpoint depends on multiple DB lookups, fetch and validate all before any expensive operations"

requirements-completed: [COMP-01]

# Metrics
duration: ~20min
completed: 2026-04-01
---

# Phase 4 Plan 02: /compare Endpoint Summary

**GET /compare endpoint with TDD — extracted _build_recommendation helper and side-by-side player comparison returning {player_a, player_b} with 404 on any missing player**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-04-01
- **Completed:** 2026-04-01
- **Tasks:** 1 (TDD: RED + GREEN commits)
- **Files modified:** 2

## Accomplishments
- Extracted `_build_recommendation(player_id, format, db)` helper from the existing `/player/{id}` route body, making recommendation-building reusable
- Added `GET /compare?a={id}&b={id}&format={format}` route returning both players' full payloads under `player_a` / `player_b` keys
- Simplified `/player/{player_id}` route body to a single delegation call
- Added 5 new compare tests (returning 200, 404 on invalid a, 404 on invalid b, format propagation, regression on /player/{id}) bringing total to 15 passing

## Task Commits

Each TDD task committed atomically:

1. **RED — failing compare tests** - `e21d3b7` (test)
2. **GREEN — _build_recommendation + /compare implementation** - `b5565e8` (feat)

## Files Created/Modified
- `main.py` - Added `_build_recommendation` helper and `compare_players` route; simplified existing `/player/{id}` route
- `tests/test_api.py` - Added `compare_fixture` and 5 `test_compare_*` functions

## Decisions Made
- Validate both players exist before building either recommendation — this prevents partial comparison responses where one player succeeds and one fails
- Return player IDs in 404 detail string so callers can identify which ID was invalid without guessing

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- /compare endpoint is live and fully tested; trade analyzer (Phase 5) can use it as the comparison primitive for head-to-head player evaluation
- No blockers

---
*Phase: 04-reliability-enhancement*
*Completed: 2026-04-01*
