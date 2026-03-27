---
phase: 03-full-stack-core
plan: 01
subsystem: api
tags: [fastapi, uvicorn, sqlalchemy, sleeper, cors, tdd]

# Dependency graph
requires:
  - phase: 01-data-foundation
    provides: Player/Matchup ORM models and SQLAlchemy session factory
  - phase: 02-recommendation-engine
    provides: score_player() pure function and Recommendation dataclass as API contract
provides:
  - FastAPI app in main.py with /search and /player/{id} routes
  - CORS enabled for localhost:3000
  - fetch_projected_points and extract_projected_points in sleeper.py
  - Full test coverage via FastAPI TestClient (11 API tests + 1 sleeper test)
affects: [03-02-frontend-scaffold, 03-03-player-card, 03-04-integration]

# Tech tracking
tech-stack:
  added: [uvicorn[standard]==0.42.0, httpx==0.28.1]
  patterns: [FastAPI dependency injection for DB sessions, StaticPool in-memory SQLite for test isolation, TDD RED/GREEN cycle]

key-files:
  created:
    - main.py
    - tests/test_api.py
  modified:
    - src/fantasy/fetch/sleeper.py
    - tests/test_sleeper.py
    - pyproject.toml

key-decisions:
  - "FastAPI get_db dependency uses get_session_factory() from base.py — tests override via app.dependency_overrides[get_db]"
  - "StaticPool used for in-memory SQLite test isolation so all sessions share same connection"
  - "injury_status converted with 'or None' to avoid passing empty string to engine (Pitfall 4)"
  - "fetch_projected_points catches all exceptions and returns {} — Sleeper projections endpoint is undocumented and unreliable"

patterns-established:
  - "Dependency override pattern: app.dependency_overrides[get_db] = override_get_db in test fixtures"
  - "StaticPool + check_same_thread=False for threaded TestClient with in-memory SQLite"
  - "Position-gated usage_share_l4w: WR/TE uses target_share, RB uses carry_share, QB uses [None, None, None, None]"

requirements-completed: [SRCH-01, SRCH-02, RECD-04, RECD-05, DATA-02]

# Metrics
duration: 3min
completed: 2026-03-27
---

# Phase 3 Plan 01: FastAPI Backend Summary

**FastAPI app with /search (ilike, 5-result cap) and /player/{id} (SkillSignals dispatch, ScoringFormat enum) routes, CORS for localhost:3000, and Sleeper projected-points fetch with graceful fallback**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-27T14:18:54Z
- **Completed:** 2026-03-27T14:21:54Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Replaced main.py stub with full FastAPI app serving /search and /player/{id} endpoints
- Added CORS middleware allowing GET from localhost:3000
- Extended sleeper.py with fetch_projected_points and extract_projected_points functions
- 12 new tests (11 API + 1 sleeper fallback) all pass GREEN; 60 total tests pass with no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Install uvicorn, write TDD tests for API routes** - `a2001e9` (test)
2. **Task 2: Implement FastAPI routes and fetch_projected_points** - `d819153` (feat)

**Plan metadata:** (docs commit below)

_Note: TDD tasks have test commit (RED) followed by feat commit (GREEN)_

## Files Created/Modified

- `main.py` - FastAPI app with /search, /player/{id}, get_db dependency, CORSMiddleware
- `tests/test_api.py` - 11 FastAPI route tests via TestClient with in-memory SQLite (StaticPool)
- `src/fantasy/fetch/sleeper.py` - Added fetch_projected_points, extract_projected_points, SLEEPER_PROJECTIONS_URL
- `tests/test_sleeper.py` - Added test_fetch_projected_points_fallback (HTTPError -> empty dict)
- `pyproject.toml` - Added uvicorn[standard] and httpx dependencies

## Decisions Made

- FastAPI `get_db` dependency pattern allows tests to override with in-memory database via `app.dependency_overrides`
- `StaticPool` used in test fixtures to ensure all sessions (test + app) share the same in-memory SQLite connection — required because TestClient runs in a separate thread
- `injury_status=player.injury_status or None` converts empty string from Sleeper normalization back to None before passing to engine (Pitfall 4 from RESEARCH.md)
- `fetch_projected_points` wraps all exceptions in a bare `except Exception: return {}` because the Sleeper projections endpoint is undocumented and can fail silently

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed missing httpx dependency**
- **Found during:** Task 1 (TDD test setup)
- **Issue:** `fastapi.testclient.TestClient` requires `httpx` package; starlette raised `RuntimeError` at import
- **Fix:** Ran `uv add httpx`
- **Files modified:** pyproject.toml
- **Verification:** TestClient import succeeds, test collection proceeds
- **Committed in:** a2001e9 (Task 1 commit)

**2. [Rule 1 - Bug] Used StaticPool to fix in-memory SQLite cross-thread isolation**
- **Found during:** Task 2 (GREEN phase, first test run)
- **Issue:** Default connection pool creates a new in-memory database per connection — the test fixture's session and the app's session saw different databases (no tables in app's connection)
- **Fix:** Added `poolclass=StaticPool, connect_args={"check_same_thread": False}` to test engine creation
- **Files modified:** tests/test_api.py
- **Verification:** All 11 API tests pass GREEN
- **Committed in:** d819153 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking dependency, 1 bug)
**Impact on plan:** Both auto-fixes required for correct test behavior. No scope creep.

## Issues Encountered

- In-memory SQLite cross-thread isolation: TestClient spawns a thread; default SQLite pool creates per-connection databases, so test session and app session saw different (empty) databases. Fixed with StaticPool.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- FastAPI backend is ready for the frontend (plans 02-03) to consume
- `/search?q=...` returns JSON array of `{id, full_name, position, team}`
- `/player/{id}` returns full recommendation including verdict, score, reasons, injury/usage fields
- uvicorn can serve the app: `uv run uvicorn main:app --host 0.0.0.0 --port 8000`

---
*Phase: 03-full-stack-core*
*Completed: 2026-03-27*
