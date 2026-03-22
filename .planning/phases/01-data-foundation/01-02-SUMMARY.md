---
phase: 01-data-foundation
plan: 02
subsystem: data-pipeline
tags: [sleeper, nflreadpy, polars, requests, normalization, dvp, carry-share, pytest, tdd]

# Dependency graph
requires:
  - phase: 01-data-foundation plan 01
    provides: Player/Matchup ORM models, upsert helpers, db_session fixture in conftest.py
provides:
  - Sleeper API client (fetch_sleeper_players, extract_player_data) with injury_status=None normalization
  - nflreadpy wrappers (load_player_stats, load_snap_counts, load_pbp, load_ff_playerids)
  - PBP schema validation guard (validate_pbp_schema) required before any DVP computation
  - carry_share derivation via polars groupby (player_carries / team_carries per week)
  - DVP computation (compute_dvp) — QB/RB/WR fantasy points allowed per defense over last 4 weeks
  - Normalization layer (normalize_players, normalize_matchups) — crosswalk join + 4-week rolling stats
  - Full test coverage: 14 new tests across test_sleeper.py, test_nflverse.py, test_normalize.py
affects:
  - 01-data-foundation plan 03 (refresh script uses fetch + normalize + upsert together)
  - 02-recommendation-engine (reads Player.week1-4 snap/target/carry columns set here)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - TDD (RED-GREEN): failing tests written first, confirmed failing, then implementation to pass
    - Polars groupby for carry_share derivation: group_by(["recent_team", "week"]).agg(sum)
    - validate_pbp_schema() called at top of compute_dvp — fail-fast guard for experimental PBP schema
    - Injury_status=None normalized to empty string on ingest (Pitfall 5 prevention)
    - Week slot mapping: week1=current_week-1 (most recent) through week4=current_week-4 (oldest)
    - id_lookup dict: sleeper_id -> gsis_id built once from crosswalk, used for all player iterations

key-files:
  created:
    - src/fantasy/fetch/sleeper.py
    - src/fantasy/fetch/nflverse.py
    - tests/test_sleeper.py
    - tests/test_nflverse.py
    - tests/test_normalize.py
  modified:
    - src/fantasy/normalize.py (was placeholder, now fully implemented)
    - tests/conftest.py (added mock_sleeper_response, mock_pbp_df, mock_stats_df fixtures)

key-decisions:
  - "compute_dvp derives QB/RB/WR positions from play type (passer_player_id = QB, rusher_player_id + no passer = RB, receiver_player_id = WR) rather than player position column — PBP rows don't carry position field"
  - "rank 1 = most points allowed (easiest matchup) implemented via polars rank(descending=True)"
  - "normalize_players skips players with no nflverse_id crosswalk entry — prevents name-based joins"
  - "week slot lookup uses dict-of-dicts (gsis_id -> {week: value}) built once before player iteration for O(1) per-player stats access"
  - "carry_share for players with zero carries gets 0.0 (not None) when their team has carries; players on teams with no carries get None via left join"

patterns-established:
  - "Pattern: validate_pbp_schema() before any DVP computation — call site in compute_dvp, returns (bool, missing_cols)"
  - "Pattern: Polars .to_dicts() (not .to_dict()) for converting nflreadpy DataFrames to Python dicts"
  - "Pattern: id_lookup dict for crosswalk join — build once from crosswalk_df, lookup per player"
  - "Pattern: week1=most recent, week4=oldest — consistent across snap/target/carry_share columns"

requirements-completed: [DATA-01]

# Metrics
duration: 12min
completed: 2026-03-22
---

# Phase 01 Plan 02: Data Fetch and Normalization Layer Summary

**Sleeper API client with injury normalization, nflreadpy PBP schema validation and DVP computation, carry_share derivation, and normalization layer joining sleeper_id to gsis_id with 4-week rolling stats — 25 total tests green**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-03-22T20:30:00Z
- **Completed:** 2026-03-22T20:42:00Z
- **Tasks:** 2 of 2
- **Files modified:** 7 files (5 created, 2 modified)

## Accomplishments
- Sleeper API client extracts injury fields with None-to-empty-string normalization (Pitfall 5 prevention)
- nflreadpy wrappers cover all 4 data loading functions (player_stats, snap_counts, pbp, ff_playerids)
- PBP schema validation guard — validate_pbp_schema() checks REQUIRED_PBP_COLUMNS before compute_dvp; returns (False, missing_cols) to fail fast
- carry_share computed via polars groupby (player_carries / team_total_carries per week) — not assumed pre-computed
- DVP computation identifies QB/RB/WR positions from play type columns, aggregates fantasy points allowed per defense, ranks 1-32 per position (rank 1 = easiest)
- normalize_players joins sleeper_id to gsis_id via crosswalk, attaches 4-week rolling snap/target/carry stats with week1=most recent mapping
- 25 tests pass including models, upsert, sleeper, nflverse, and normalize test modules

## Task Commits

Each task was committed atomically:

1. **Task 1: Sleeper API client, nflverse wrappers, and PBP schema validation** - `e55b027` (feat)
2. **Task 2: Normalization layer** - `7d7cdf1` (feat)

_Note: Both tasks used TDD (RED-GREEN): tests written before implementation, confirmed failing, then implementation to pass._

## Files Created/Modified
- `src/fantasy/fetch/sleeper.py` - fetch_sleeper_players() and extract_player_data() with injury_status normalization
- `src/fantasy/fetch/nflverse.py` - validate_pbp_schema, compute_carry_share, compute_dvp, nflreadpy load wrappers
- `src/fantasy/normalize.py` - normalize_players() with crosswalk join and 4-week stats, normalize_matchups()
- `tests/test_sleeper.py` - 4 tests: healthy/injured extraction, field completeness, db upsert integration
- `tests/test_nflverse.py` - 5 tests: PBP schema valid/invalid, carry_share computation, DVP shape and ranking
- `tests/test_normalize.py` - 5 tests: ID joining, week stats mapping, position filtering, missing stats, matchup passthrough
- `tests/conftest.py` - Added mock_sleeper_response, mock_pbp_df, mock_stats_df fixtures

## Decisions Made
- compute_dvp infers position from play type (passer_player_id present = QB play, rusher_player_id present and no passer = RB play, receiver_player_id present = WR play) because PBP rows don't include player position
- DVP rank uses polars rank(method="ordinal", descending=True) so rank 1 = team allowing most points = easiest matchup
- normalize_players uses a dict-of-dicts lookup for stats (gsis_id -> {week: float}) built once before the player iteration loop for O(1) per-player access
- Players without nflverse crosswalk entries are skipped with a debug log, not errored, since many Sleeper players (practice squad, IR) legitimately have no nflverse stats

## Deviations from Plan

None - plan executed exactly as written. Both tasks followed TDD RED-GREEN cycle as specified.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Fetch layer (sleeper.py + nflverse.py) and normalize layer are the locked contract for Plan 03 (refresh script)
- scripts/refresh.py can now import fetch_sleeper_players, load_player_stats, load_snap_counts, load_pbp, load_ff_playerids, compute_dvp, normalize_players, normalize_matchups
- All 25 tests pass — test suite is stable for Plan 03 to add test_refresh.py

---
*Phase: 01-data-foundation*
*Completed: 2026-03-22*
