---
phase: 02-recommendation-engine
plan: 01
subsystem: api
tags: [python, dataclasses, enum, pytest, tdd]

# Dependency graph
requires:
  - phase: 01-data-foundation
    provides: Player/Matchup ORM models — column names (injury_status, snap_pct, target_share, carry_share, opponent_rank) inform signal dataclass field design; engine never imports these

provides:
  - src/fantasy/engine.py with public API: score_player(), SkillSignals, KickerSignals, DSTSignals, Recommendation, Verdict, ScoringFormat
  - Constants: START_THRESHOLD=70.0, SIT_THRESHOLD=45.0, INJURY_VETO, SKILL_WEIGHTS
  - 16-test RED-phase suite with GREEN assertions commented for Plan 02

affects: [02-02-PLAN, phase 3 api routes, phase 3 rendering]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure function engine: PlayerSignals -> Recommendation with zero DB imports"
    - "TDD RED phase: NotImplementedError stubs + pytest.raises wrappers; GREEN assertions as comments"
    - "Frozen dataclass per position type (SkillSignals, KickerSignals, DSTSignals) for immutable inputs"
    - "Union[SkillSignals, KickerSignals, DSTSignals] dispatcher pattern for score_player()"

key-files:
  created:
    - src/fantasy/engine.py
    - tests/test_engine.py
  modified: []

key-decisions:
  - "score_player() public dispatcher routes by isinstance; three private stubs raise NotImplementedError until Plan 02"
  - "Recommendation dataclass is the Phase 3 API contract — shape frozen post-Phase 2"
  - "SkillSignals, KickerSignals, DSTSignals are separate frozen dataclasses to avoid meaningless None fields for K/DST"
  - "matchup_rank=1 means easiest (most pts allowed) — CONTEXT.md convention honored in engine docstrings"
  - "PROJECTED_POINTS_CEILING=30.0 established as constant for sub-score normalization in Plan 02"

patterns-established:
  - "Engine isolation: zero SQLAlchemy imports enforced; verify with assert 'sqlalchemy' not in sys.modules"
  - "RED-phase test pattern: pytest.raises(NotImplementedError) wraps each call; Plan 02 comment marks exact unwrap points"
  - "16 test functions map directly to 9 requirement IDs via VALIDATION.md per-task verification map"

requirements-completed: [RECD-01, RECD-02, RECD-03, RECD-06, RECD-07, RECD-08, POS-01, POS-02, POS-03]

# Metrics
duration: 2min
completed: 2026-03-25
---

# Phase 02 Plan 01: Recommendation Engine — Types, Stubs, and RED Test Suite Summary

**Pure Python engine module with typed signal dataclasses, Verdict/ScoringFormat enums, stub dispatcher, and 16-test TDD RED suite covering all 9 Phase 2 requirement IDs**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-25T17:57:57Z
- **Completed:** 2026-03-25T18:00:25Z
- **Tasks:** 2 of 2
- **Files modified:** 2

## Accomplishments

- Created `src/fantasy/engine.py` with all public types (ScoringFormat, Verdict, SkillSignals, KickerSignals, DSTSignals, Recommendation, PlayerSignals union), scoring constants, and `score_player()` dispatcher routing to stub private functions
- Zero SQLAlchemy imports verified — engine is fully isolated from db layer
- Created `tests/test_engine.py` with 16 test functions (19 test cases after parametrize expansion) — all passing in RED phase (1 real enum check + 15 NotImplementedError confirmations + 3 parametrized positions)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create engine types, enums, dataclasses, and stub functions** - `93cab61` (feat)
2. **Task 2: Create full test suite (16 tests, all RED)** - `146e0f7` (test)

## Files Created/Modified

- `src/fantasy/engine.py` — ScoringFormat/Verdict enums, SkillSignals/KickerSignals/DSTSignals/Recommendation dataclasses, constants, score_player() dispatcher, three NotImplementedError stubs
- `tests/test_engine.py` — 16 test functions with RED-phase pytest.raises wrappers; GREEN assertions commented for Plan 02

## Decisions Made

- Followed plan exactly — no discretionary decisions needed. All constant values (thresholds, weights, INJURY_VETO) match PLAN.md and CONTEXT.md specifications exactly.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `score_player()`, all signal dataclasses, and the `Recommendation` output dataclass are fully defined — Plan 02 can implement `_score_skill`, `_score_kicker`, `_score_dst` directly
- All 16 test GREEN assertions are in place as comments — Plan 02 unwraps pytest.raises and uncomments assertions to move from RED to GREEN
- Full test suite (Phase 1 + Phase 2) runs clean — no regressions introduced

---
*Phase: 02-recommendation-engine*
*Completed: 2026-03-25*
