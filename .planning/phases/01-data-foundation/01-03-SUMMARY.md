---
phase: 01-data-foundation
plan: 03
subsystem: infra
tags: [python, sqlite, sqlalchemy, nflreadpy, cron, logging, tdd]

# Dependency graph
requires:
  - phase: 01-01
    provides: DB engine, session factory, upsert_players, upsert_matchups
  - phase: 01-02
    provides: fetch_sleeper_players, load_player_stats, load_snap_counts, load_pbp, compute_dvp, normalize_players, normalize_matchups

provides:
  - Standalone refresh.py orchestrator that ties full pipeline together
  - Off-season guard (DATA-03): returns early with season_active=False when week outside 1-22
  - Fetch failure isolation: exception caught at fetch layer; last good DB data retained
  - cron.example documenting 2-hour refresh schedule (DATA-01)
  - TimedRotatingFileHandler logging with 7-day rotation

affects:
  - 02-recommendation-engine
  - 03-api-layer
  - 04-ui

# Tech tracking
tech-stack:
  added: [logging.handlers.TimedRotatingFileHandler]
  patterns:
    - "Cron script uses absolute paths computed from __file__ for portability"
    - "Off-season guard at script entry: week outside 1-22 returns early without touching DB"
    - "Fetch layer wrapped in single except Exception block: any failure preserves last good data"
    - "setup_logging() adds handlers directly to root logger (not basicConfig) for idempotency in tests"

key-files:
  created:
    - scripts/refresh.py
    - scripts/__init__.py
    - tests/test_refresh.py
    - cron.example
  modified: []

key-decisions:
  - "setup_logging adds handlers directly to root logger rather than using logging.basicConfig — basicConfig is a no-op when handlers already exist, which breaks test isolation"
  - "Off-season guard uses week range 1-22 (not > 17) to include playoffs through conference championships"
  - "Cron fires unconditionally every 2 hours; refresh.py handles off-season detection internally (DATA-03)"

patterns-established:
  - "Pattern: Refresh script entry point uses PROJECT_ROOT = Path(__file__).resolve().parent.parent for absolute path computation"
  - "Pattern: Fetch phase wrapped in broad except Exception block — any network/parse failure skips upsert, preserving last good data"

requirements-completed:
  - DATA-01
  - DATA-03

# Metrics
duration: 5min
completed: 2026-03-22
---

# Phase 1 Plan 3: Refresh Orchestration Summary

**Cron-invoked refresh.py orchestrates the full pipeline (Sleeper + nflreadpy -> normalize -> SQLite upsert) with off-season guard, fetch failure isolation, and 7-day log rotation**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-03-22T20:13:58Z
- **Completed:** 2026-03-22T20:18:40Z
- **Tasks:** 2 (TDD: 3 commits for Task 1)
- **Files modified:** 4

## Accomplishments
- refresh.py orchestrates complete data pipeline: fetch from Sleeper + nflreadpy, normalize, upsert to SQLite
- Off-season guard returns season_active=False when NFL week is outside range 1-22 (DATA-03)
- Fetch failure isolation: any exception in the fetch phase is caught, error logged, upsert skipped — DB retains last good data
- cron.example documents the 2-hour schedule satisfying DATA-01
- All 30 tests pass across the full data-foundation test suite

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests for refresh orchestration** - `4746163` (test)
2. **Task 1 GREEN: Implement refresh orchestration script** - `f2ef15a` (feat)
3. **Task 2: Add cron example and verify full integration** - `d9ffd04` (feat)

_Note: TDD tasks have multiple commits (test RED -> feat GREEN)_

## Files Created/Modified
- `scripts/refresh.py` - Main orchestrator: off-season guard, fetch, normalize, upsert pipeline
- `scripts/__init__.py` - Package init to enable `from scripts.refresh import main`
- `tests/test_refresh.py` - 5 tests: off-season guard, in-season run, fetch failure, return stats, logging check
- `cron.example` - Crontab entry for 2-hour refresh with DATA-01 and DATA-03 comments

## Decisions Made
- `setup_logging` adds handlers directly to root logger instead of using `logging.basicConfig`. Reason: `basicConfig` is a no-op when the root logger already has handlers (common in test environments), causing `test_logging_configured` to fail. Direct handler assignment is always idempotent.
- Off-season range is weeks 1-22 (includes playoffs up to conference championships, week 22). Week 23 is bye before Super Bowl and off-season starts there.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed setup_logging idempotency for test isolation**
- **Found during:** Task 1 (test_logging_configured failing)
- **Issue:** `logging.basicConfig` is a no-op when handlers already exist on root logger; `test_logging_configured` found 0 TimedRotatingFileHandlers after calling `main()`
- **Fix:** Changed `setup_logging()` to call `root.addHandler()` directly instead of `logging.basicConfig`, so handlers are always added regardless of prior state
- **Files modified:** `scripts/refresh.py`
- **Verification:** `uv run pytest tests/test_refresh.py -v` — 5/5 pass
- **Committed in:** `f2ef15a` (Task 1 GREEN commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug)
**Impact on plan:** Auto-fix was necessary for correct test behavior. No scope creep.

## Issues Encountered
None beyond the logging idempotency fix documented above.

## User Setup Required
None - no external service configuration required for the script itself. Cron setup is documented in `cron.example`.

## Next Phase Readiness
- Phase 01 data-foundation is complete — all 3 plans executed, all 30 tests green
- DATA-01 (automatic refresh), DATA-02 (DB models + upsert), and DATA-03 (off-season guard) requirements satisfied
- Phase 02 (recommendation engine) can safely import from all `src.fantasy.*` modules
- SQLite database at `data/fantasy.db` is ready for the recommendation engine to query

---
*Phase: 01-data-foundation*
*Completed: 2026-03-22*
