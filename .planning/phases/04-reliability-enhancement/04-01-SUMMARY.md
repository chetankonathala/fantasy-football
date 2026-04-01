---
phase: 04-reliability-enhancement
plan: 01
subsystem: database
tags: [sqlalchemy, alembic, requests, the-odds-api, open-meteo, nfl, vegas-odds, weather]

# Dependency graph
requires:
  - phase: 03-full-stack-core
    provides: FastAPI backend with Player/Matchup ORM models and upsert pattern
provides:
  - GameLine SQLAlchemy model with Vegas odds + weather columns
  - upsert_game_lines() helper for atomic upsert-on-conflict
  - fetch_game_lines() from The Odds API with implied total computation
  - fetch_weather() from Open-Meteo with DOME_TEAMS skip and wind/precip thresholds
  - refresh.py integration calling both fetchers within session context
affects: [05-polish-deploy, api-layer, recommendation-engine]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - The Odds API implied total formula: home = (total/2) - (spread/2), away = (total/2) + (spread/2)
    - DOME_TEAMS frozenset for static dome detection — skip Open-Meteo API call entirely
    - Open-Meteo always requires wind_speed_unit=mph (default is km/h, Pitfall 2)
    - Day-of-week guard in fetch_game_lines: only call Wed-Sat (weekday 2-5) to protect 500/month quota
    - Weather thresholds: wind > 15 mph OR precip > 30% sets weather_flag=True

key-files:
  created:
    - src/fantasy/db/models.py (GameLine model added alongside Matchup/Player)
    - src/fantasy/db/upsert.py (upsert_game_lines added)
    - src/fantasy/fetch/odds.py
    - src/fantasy/fetch/weather.py
    - tests/test_upsert.py (5 GameLine tests)
    - tests/test_odds.py
    - tests/test_weather.py
  modified:
    - scripts/refresh.py (game lines fetch+persist block added inside session context)
    - alembic/versions/ (add_game_line_table migration)

key-decisions:
  - "GameLine table keyed by (week, home_team, away_team) — game-scoped data does not belong on Matchup (which is position-scoped)"
  - "DOME_TEAMS includes LAR and LAC (SoFi Stadium) — treat as dome for simplicity; occasional wind events accepted as acceptable error rate"
  - "Day-of-week guard for Odds API is in fetch module, not refresh.py — keeps quota protection co-located with the API client"
  - "fetch_weather enriches game_line dicts in-place — same list object returned for chaining into upsert_game_lines"
  - "Game lines failure is non-fatal — wrapped in try/except inside session block; players/matchups already committed, game_lines_count=0 on error"

patterns-established:
  - "Pattern: fetch module returns [] on missing API key or guard conditions — never raises"
  - "Pattern: dome teams short-circuit weather API call — set is_dome=True, weather_flag=False, wind/precip=None"
  - "Pattern: implied total math (game_total/2) +/- (home_spread/2) established as canonical formula"

requirements-completed: [ENRI-01, ENRI-02]

# Metrics
duration: 54min
completed: 2026-03-31
---

# Phase 4 Plan 01: GameLine Model, Odds Fetch, and Weather Fetch Summary

**GameLine SQLite table with Vegas implied totals (The Odds API) and weather flags (Open-Meteo), integrated into the refresh pipeline with dome-team skip logic and quota-protecting day-of-week guard**

## Performance

- **Duration:** 54 min
- **Started:** 2026-04-01T02:45:13Z
- **Completed:** 2026-04-01T03:39:00Z
- **Tasks:** 2 (Task 1 pre-completed; Task 2 executed this session)
- **Files modified:** 7

## Accomplishments

- GameLine ORM model with 13 columns covering Vegas odds, weather, and audit fields; Alembic migration applied
- fetch_game_lines() fetches NFL totals+spreads from The Odds API and computes implied team totals with a Wed-Sat quota guard
- fetch_weather() enriches game_line dicts with Open-Meteo wind/precip data, skipping the 11 DOME_TEAMS and flagging games with wind > 15 mph or precip > 30%
- scripts/refresh.py wires both fetchers inside the existing session context block; game lines failure is non-fatal
- 25 tests total across test_upsert.py (11), test_odds.py (6), test_weather.py (8) — all passing

## Task Commits

Each task was committed atomically:

1. **Task 1: GameLine model, upsert helper, and Alembic migration** - `359d91d` (feat)
2. **Task 2: Odds API fetch module and Open-Meteo weather fetch module** - `83feaa7` (feat)

_Note: TDD tasks have multiple commits (test RED phase then feat GREEN phase merged into task commit for Task 2)_

## Files Created/Modified

- `src/fantasy/db/models.py` - GameLine model added (id, week, home/away_team, game_total, home_spread, implied totals, is_dome, wind_mph, precip_probability, weather_flag, game_date, updated_at)
- `src/fantasy/db/upsert.py` - upsert_game_lines() added following existing upsert_matchups pattern
- `src/fantasy/fetch/odds.py` - fetch_game_lines() with ODDS_API_URL, _normalize_team(), _TEAM_MAP for all 32 NFL teams
- `src/fantasy/fetch/weather.py` - fetch_weather() with DOME_TEAMS frozenset, STADIUM_COORDS dict (32 teams), wind/precip thresholds
- `scripts/refresh.py` - imports + game lines fetch/weather/persist block inside session context
- `tests/test_upsert.py` - 5 new GameLine tests (insert, update-on-conflict, empty list, unique constraint)
- `tests/test_odds.py` - 6 tests (required keys, implied total math, empty response, no API key, day-of-week guard, team normalization)
- `tests/test_weather.py` - 8 tests (DOME_TEAMS contents, dome skip, high wind flag, high precip flag, normal conditions, request error, empty list, thresholds)
- `alembic/versions/` - add_game_line_table migration

## Decisions Made

- GameLine table is game-scoped (one row per week/home_team/away_team), not position-scoped like Matchup — avoids duplicating game data 6x per team per week
- DOME_TEAMS includes LAR and LAC (SoFi Stadium with open sides) — conservative choice, occasional wind events accepted as tolerable error rate vs. complexity of partial-dome handling
- Quota guard is inside fetch_game_lines(), not in refresh.py — keeps API-specific constraints co-located with the client
- Game lines failure is non-fatal — wrapped in try/except; players/matchups already committed before this block runs

## Deviations from Plan

None - plan executed exactly as written. The existing test_odds.py stub (RED phase artifact) was overwritten with complete tests before implementation.

## Issues Encountered

- The existing tests/test_odds.py had an incomplete datetime mock pattern from a prior RED stub. Rewrote with `mock_dt.now.side_effect = lambda tz=None: mock_now` which correctly handles the `datetime.now(timezone.utc)` call in the production code. This is TDD process, not a deviation.

## User Setup Required

**External services require manual configuration.**

The Odds API key must be set before game lines will be fetched:

1. Sign up at https://the-odds-api.com
2. Go to Dashboard → API Key
3. Add to environment: `export ODDS_API_KEY=your-key-here`
4. Verify: `python -c "import os; print(os.environ.get('ODDS_API_KEY'))"`

Open-Meteo requires no API key (free, no registration).

## Next Phase Readiness

- GameLine table populated by refresh pipeline on Wed-Sat during season
- API layer (Phase 04-02) can join Player -> Matchup -> GameLine to expose implied totals and weather flags on recommendation cards
- Pitfall 3 noted: GameLine join must check both home_team AND away_team for a given player's team

---
*Phase: 04-reliability-enhancement*
*Completed: 2026-03-31*
