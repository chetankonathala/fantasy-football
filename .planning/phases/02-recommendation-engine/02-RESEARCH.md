# Phase 2: Recommendation Engine - Research

**Researched:** 2026-03-25
**Domain:** Pure Python scoring function — deterministic signal-to-verdict transformation
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Scoring Thresholds**
- Fixed numeric cutoffs: score 0–100, where >=70 = START, 45–69 = FLEX, <45 = SIT
- Fixed weights per signal type (not position-relative): matchup grade, usage trend, injury penalty, projected points, confidence
- Injury status is a hard veto: `Out` always = SIT regardless of score; `Doubtful` forces SIT; `Questionable` applies a score penalty
- Low-confidence threshold: players with fewer than 4 weeks of usage data receive a `low_confidence` flag (per RECD-08)

**Projected Points (RECD-06)**
- `projected_points` is a pass-through input — the engine accepts it as a typed signal, does not fetch or compute it
- If `projected_points` is `None` (off-season, new player, missing data), it is excluded from scoring — its weight redistributes to remaining signals
- Projected points directly affect the composite score (not just reasoning)
- Scoring format (PPR / half-PPR / standard) adjusts both projected points value AND signal weights (e.g., PPR increases target share weight and bumps projected points for pass-catchers)

**Reasoning Narrative Format (RECD-02)**
- Structured template strings — fixed per-signal templates, not free-form sentences
  - Example: `"Favorable matchup: #3 defense vs WR"`, `"Strong usage: 82% snap share (L4W)"`, `"Injury risk: Questionable (hamstring)"`
- Always 3–5 factors — if fewer signals are available (K, DST), pad with low-confidence or context notes to reach minimum 3
- Priority order — most impactful signal leads: hard veto reasons first (injury Out), then matchup, then usage, then projection, then confidence flag
- Lead with a summary reason — first factor states the primary reason for the verdict: `"Strong START: elite matchup + high usage"`

**K and DST Signal Sets (POS-02, POS-03)**
- K (Kicker): `matchup_rank` (opponent rank vs kickers from DVP) + `vegas_implied_team_total` as signals
  - `vegas_implied_team_total` is an optional pass-through input — treated as `None` in Phase 2 (Vegas data is Phase 4 scope, ENRI-01)
- DST: `opponent_offense_rank` (opponent rank vs DST from DVP) + `opponent_implied_points` (Vegas implied points opponent is expected to score)
  - `opponent_implied_points` is an optional pass-through input — treated as `None` in Phase 2
- No low-confidence flag for K/DST — these positions have no snap/target/carry usage data; RECD-08 only applies to skill positions (QB, RB, WR, TE)

### Claude's Discretion
- Exact numeric weight values for each signal (e.g., matchup = 40%, usage = 30%) — pick sensible defaults
- How weight redistribution works when optional signals are None
- Internal score normalization approach
- Test fixture design for representative per-position inputs

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| RECD-01 | User can see a clear START / SIT / FLEX verdict for any player for the current week | Verdict enum + threshold constants; scoring function return type |
| RECD-02 | Each recommendation includes a structured reasoning narrative (3-5 plain-English factors) | Template-string approach; priority ordering; padding rules for K/DST |
| RECD-03 | User can see the matchup grade (opponent rank vs. position, based on DVP) | Matchup model already stores `opponent_rank` (1–32); feed directly as signal |
| RECD-06 | User can see projected fantasy points for the current week | Pass-through input field in PlayerSignals; weight redistribution when None |
| RECD-07 | User can select scoring format (PPR / half-PPR / standard) and have recommendation update accordingly | ScoringFormat enum; weight modifier map; engine accepts format param |
| RECD-08 | Low-confidence recommendations (fewer than 4 games of data) are visibly flagged | Count non-None week slots in usage data; flag if < 4 |
| POS-01 | Recommendations available for QB, RB, WR, TE (full signal set) | SkillSignals dataclass; all four positions use snap_pct + position-appropriate usage share |
| POS-02 | Recommendations available for K (matchup-based signals only) | KickerSignals dataclass; matchup_rank only (vegas_implied_team_total = None in Phase 2) |
| POS-03 | Recommendations available for DST (opponent offense rank) | DSTSignals dataclass; opponent_offense_rank only (opponent_implied_points = None in Phase 2) |
</phase_requirements>

---

## Summary

Phase 2 builds a single pure Python module (`src/fantasy/engine.py`) that accepts typed signal inputs and returns a deterministic `Recommendation` dataclass. There is no I/O, no database access, and no external calls — only math and logic on the values passed in. This is a straightforward weighted-score implementation; the only genuine complexity is the three-way signal surface (skill positions vs. K vs. DST), weight redistribution when optional signals are absent, and the template-string reasoning narrative.

The existing codebase (Phase 1) provides all the data that feeds this engine: `Player.injury_status`, `Player.week1_snap_pct` through `Player.week4_snap_pct`, `Player.week1_target_share` through `Player.week4_target_share`, `Player.week1_carry_share` through `Player.week4_carry_share`, and `Matchup.opponent_rank`. The engine does not touch these tables directly; it only consumes the derived float values that API routes (Phase 3) will extract and pass in.

The test pattern established in Phase 1 (pytest, in-memory SQLite, plain dataclass fixtures) is the right model. Engine tests are simpler — they need no DB at all, only constructed `PlayerSignals` instances. The test suite needs one representative fixture per position plus isolated single-signal tests for each scoring axis.

**Primary recommendation:** Implement as a single `src/fantasy/engine.py` module exposing one public function `score_player(signals, scoring_format) -> Recommendation`, backed by three private signal dataclasses and one `Recommendation` dataclass that becomes the Phase 3 API contract.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python dataclasses | stdlib | `PlayerSignals`, `Recommendation` typed containers | Zero dependencies; already used project-wide; mypy-compatible |
| Python `enum` | stdlib | `Verdict` (START/SIT/FLEX), `ScoringFormat` (PPR/HALF_PPR/STANDARD), `InjuryStatus` | Type-safe constants; exhaustive match possible |
| pytest | >=9.0.2 (pinned in pyproject.toml) | Test suite | Already installed and configured |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `dataclasses.field` + `__post_init__` | stdlib | Validation of signal ranges (0.0–1.0 for share values) | Use in `PlayerSignals.__post_init__` |
| `typing.Literal` | stdlib (Python 3.8+) | Narrow string types before enum is used at call site | Optional — prefer enum |
| `typing.TypedDict` | stdlib | Alternative to dataclass for JSON-serializable output | Prefer dataclass; TypedDict if Phase 3 needs direct dict serialization |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Plain dataclasses | Pydantic models | Pydantic adds validation and JSON serialization but adds a dependency; overkill for a pure computation layer with no I/O |
| Flat `PlayerSignals` with position field | Union type / separate dataclasses per position | Separate dataclasses are cleaner for K/DST (no unused None fields) but require overloaded function signature; flat + position enum is simpler |
| Hardcoded weight dicts | Config file / env vars | Config adds complexity; weights are not user-adjustable; constants in module are more readable and testable |

**Installation:** No new dependencies required. Engine uses only Python stdlib.

---

## Architecture Patterns

### Recommended Project Structure

```
src/fantasy/
├── engine.py          # Public: score_player(); Private: _score_skill(), _score_kicker(), _score_dst()
├── db/
│   ├── models.py      # Phase 1: Player, Matchup ORM
│   └── ...
├── fetch/             # Phase 1: Sleeper, nflverse
└── normalize.py       # Phase 1: Player/Matchup dict normalization

tests/
├── test_engine.py     # New: engine unit tests (no DB needed)
├── conftest.py        # Existing: db fixtures (not needed for engine tests)
└── ...
```

### Pattern 1: Input Dataclasses (Three Signal Surfaces)

**What:** Three separate frozen dataclasses encode the distinct signal sets. A shared `score_player` dispatcher routes to the correct scorer based on position.

**When to use:** Always — position determines which signals exist; using one flat dataclass produces many meaningless `None` fields for K/DST.

```python
from dataclasses import dataclass
from enum import Enum
from typing import Optional

class ScoringFormat(Enum):
    PPR = "ppr"
    HALF_PPR = "half_ppr"
    STANDARD = "standard"

class Verdict(Enum):
    START = "START"
    SIT = "SIT"
    FLEX = "FLEX"

@dataclass(frozen=True)
class SkillSignals:
    """Signals for QB, RB, WR, TE."""
    position: str                          # "QB" | "RB" | "WR" | "TE"
    matchup_rank: Optional[int]            # 1-32; 1 = easiest (most pts allowed)
    injury_status: Optional[str]           # "Out" | "Doubtful" | "Questionable" | None
    snap_pct_l4w: list[Optional[float]]    # [week1, week2, week3, week4]; None = no data
    usage_share_l4w: list[Optional[float]] # target_share (WR/TE) or carry_share (RB) or None (QB)
    projected_points: Optional[float]      # pass-through; None = excluded from score

@dataclass(frozen=True)
class KickerSignals:
    """Signals for K."""
    matchup_rank: Optional[int]
    vegas_implied_team_total: Optional[float]  # None in Phase 2

@dataclass(frozen=True)
class DSTSignals:
    """Signals for DST."""
    opponent_offense_rank: Optional[int]       # 1-32; 1 = worst offense = easiest matchup
    opponent_implied_points: Optional[float]   # None in Phase 2

@dataclass
class Recommendation:
    """Engine output — the Phase 3 API contract. Do not change shape post-Phase 2."""
    verdict: Verdict
    score: float                    # 0.0–100.0
    reasons: list[str]              # 3–5 template strings; first is summary
    low_confidence: bool            # True if < 4 weeks of usage data (skill only)
    scoring_format: ScoringFormat
```

### Pattern 2: Weighted Score Computation with None-Aware Redistribution

**What:** Each signal contributes a normalized sub-score (0–100) multiplied by its weight. When a signal is `None`, its weight is redistributed proportionally across present signals so the total weight always sums to 1.0.

**When to use:** Skill position scoring; also Kicker/DST (simpler — fewer signals).

```python
# Discretionary weight defaults (Claude's discretion — tune during implementation)
SKILL_WEIGHTS = {
    "matchup":    0.30,
    "usage":      0.30,
    "projected":  0.25,
    "confidence": 0.15,
}

# PPR format boosts target share weight and projected points for pass-catchers
FORMAT_MODIFIERS = {
    ScoringFormat.PPR:       {"usage_delta": +0.05, "projected_delta": +0.05},
    ScoringFormat.HALF_PPR:  {"usage_delta": +0.025, "projected_delta": +0.025},
    ScoringFormat.STANDARD:  {"usage_delta": 0.0,   "projected_delta": 0.0},
}

def _redistribute(weights: dict, absent_keys: set) -> dict:
    """Remove absent keys, redistribute their weight to remaining keys proportionally."""
    present = {k: v for k, v in weights.items() if k not in absent_keys}
    total = sum(present.values())
    return {k: v / total for k, v in present.items()} if total > 0 else present
```

### Pattern 3: Injury Hard-Veto Before Score Computation

**What:** Check injury_status before computing any numeric score. Out and Doubtful bypass scoring entirely and immediately return a SIT verdict with a veto reason as the first factor.

**When to use:** Always — this prevents a perfectly favorable matchup from overriding a player who is declared Out.

```python
INJURY_VETO = {"Out", "Doubtful"}
INJURY_PENALTY_STATUS = {"Questionable"}
INJURY_PENALTY_POINTS = 15  # deducted from composite score

def _apply_injury_veto(injury_status: Optional[str]) -> Optional[str]:
    """Returns a veto reason string if status forces SIT, else None."""
    if injury_status in INJURY_VETO:
        return f"Hard SIT: {injury_status} — player ruled out"
    return None
```

### Pattern 4: Template String Reason Builder

**What:** Each signal produces a formatted string from a fixed template. Strings are sorted by priority (veto first, then matchup, usage, projection, confidence). Padded to minimum 3, capped at 5.

```python
def _matchup_reason(rank: int) -> str:
    suffix = "easiest" if rank <= 8 else ("average" if rank <= 20 else "toughest")
    return f"Matchup: #{rank} defense vs position ({suffix})"

def _usage_reason(avg_share: float, position: str, weeks: int) -> str:
    pct = round(avg_share * 100)
    label = "snap share" if position == "QB" else ("target share" if position in ("WR", "TE") else "carry share")
    return f"{'Strong' if avg_share >= 0.20 else 'Low'} usage: {pct}% {label} (L{weeks}W)"

def _projected_reason(pts: float) -> str:
    return f"Projected: {pts:.1f} fantasy points"

def _low_confidence_reason(weeks: int) -> str:
    return f"Low confidence: only {weeks} week(s) of data available"

def _summary_reason(verdict: Verdict, primary_signal: str) -> str:
    return f"{'Strong' if verdict == Verdict.START else ''} {verdict.value}: {primary_signal}"
```

### Pattern 5: Low-Confidence Detection (RECD-08)

**What:** Count non-None entries in `snap_pct_l4w`. If fewer than 4, set `low_confidence=True` on the output.

**When to use:** Skill positions only (QB, RB, WR, TE). K and DST always have `low_confidence=False`.

```python
def _count_data_weeks(weekly_values: list[Optional[float]]) -> int:
    return sum(1 for v in weekly_values if v is not None)
```

### Anti-Patterns to Avoid

- **Computing matchup rank inside the engine:** The engine only receives `matchup_rank` as an integer; DVP computation happened in Phase 1. Do not re-derive or fetch from DB.
- **Using float string formatting in template strings at render time:** Format to string at scoring time, store in `reasons` list. Phase 3 renders `reasons` verbatim without re-processing.
- **Mutable default arguments in dataclasses:** Use `dataclasses.field(default_factory=list)` not `= []`.
- **Importing from `src.fantasy.db` inside engine.py:** Engine must have zero DB imports. The test for this is: `import src.fantasy.engine` should not trigger any SQLAlchemy import.
- **Exceeding 5 reasons or returning fewer than 3:** Enforce bounds explicitly — truncate or pad in the reason builder, never rely on call-site correctness.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Enum exhaustiveness | Custom string constants with if/elif chains | Python `enum.Enum` with `match`/`case` or `if e is Verdict.START` | Enums catch typos at definition time; match is exhaustive |
| Dataclass validation | Manual `__init__` with asserts | `__post_init__` in `@dataclass` | Cleaner, works with frozen=True |
| Weight redistribution | Re-implementing fraction logic | Simple dict comprehension (shown in Pattern 2 above) | Four lines; no library needed |
| JSON serialization of Recommendation | Custom serializer | `dataclasses.asdict()` + `{v.value for v in Verdict}` | Built-in; Phase 3 can call `asdict()` and replace enum values |

**Key insight:** This phase is intentionally a no-dependency pure computation module. The complexity budget should go into correctness of the scoring math and reasoning narrative, not infrastructure.

---

## Common Pitfalls

### Pitfall 1: Weight Redistribution Produces Score > 100

**What goes wrong:** When signals are absent and weights are redistributed, the normalized sub-scores may be computed on different scales (e.g., matchup rank 1–32 converted to 0–100) and the composite can drift above 100 or below 0.
**Why it happens:** Normalization of individual signals to [0, 100] range + redistribution does not guarantee composite stays in range if sub-score formulas are inconsistent.
**How to avoid:** `min(100.0, max(0.0, composite))` clamp after all weights applied. Verify with a test: `score_player(best_possible_inputs) <= 100`.
**Warning signs:** Tests with all-favorable inputs returning score > 100.

### Pitfall 2: PPR Format Modifier Applied to QB / RB Carry Share

**What goes wrong:** Format modifiers are designed for pass-catchers (WR/TE). Applying the same `usage_delta` to QB snap_pct or RB carry_share inflates scores incorrectly.
**Why it happens:** A single `FORMAT_MODIFIERS` dict applied uniformly regardless of position.
**How to avoid:** Check position before applying usage weight delta. QB and RB carry-share users get no usage_delta in PPR. Only WR and TE target-share users get the full PPR boost.
**Warning signs:** QB PPR score > QB standard score — there should be no difference for QBs.

### Pitfall 3: K/DST Reasons Array Has Fewer Than 3 Entries

**What goes wrong:** K only has `matchup_rank` (with `vegas_implied_team_total` = None in Phase 2). DST has `opponent_offense_rank` (with `opponent_implied_points` = None). That's only one active signal each — the reasons array would have 1–2 entries, violating the 3-factor minimum.
**Why it happens:** Reason builder only generates strings for present signals.
**How to avoid:** Explicitly pad to 3 using generic context notes: `"Vegas total unavailable (Phase 4)"`, `"Limited signal set for K — matchup is primary factor"`.
**Warning signs:** `len(recommendation.reasons) < 3` in any test case.

### Pitfall 4: `low_confidence` Triggered by K/DST

**What goes wrong:** K/DST don't have snap/usage data. If `low_confidence` detection checks `snap_pct_l4w` for these positions, they'd always be flagged.
**Why it happens:** Reusing the same `_count_data_weeks` logic on K/DST signal objects that have no such field.
**How to avoid:** `low_confidence` is always `False` for `KickerSignals` and `DSTSignals`. Only `SkillSignals` carries usage arrays. The dispatcher sets `low_confidence` before calling `_score_kicker` or `_score_dst`.
**Warning signs:** DST recommendation showing `low_confidence: True`.

### Pitfall 5: Frozen Dataclass with Mutable `list` Field

**What goes wrong:** `@dataclass(frozen=True)` raises `TypeError` if a mutable default is used.
**Why it happens:** `snap_pct_l4w: list[Optional[float]] = []` in a frozen dataclass.
**How to avoid:** `snap_pct_l4w: list[Optional[float]] = field(default_factory=list)` or require explicit construction without defaults.
**Warning signs:** `TypeError: mutable default <class 'list'>` at import time.

---

## Code Examples

### Full Engine Skeleton

```python
# src/fantasy/engine.py
# Source: project decisions in 02-CONTEXT.md

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Union

# --- Enums ---

class ScoringFormat(Enum):
    PPR = "ppr"
    HALF_PPR = "half_ppr"
    STANDARD = "standard"

class Verdict(Enum):
    START = "START"
    SIT = "SIT"
    FLEX = "FLEX"

# --- Signal dataclasses ---

@dataclass(frozen=True)
class SkillSignals:
    position: str
    matchup_rank: Optional[int]
    injury_status: Optional[str]
    snap_pct_l4w: list[Optional[float]]
    usage_share_l4w: list[Optional[float]]
    projected_points: Optional[float]

@dataclass(frozen=True)
class KickerSignals:
    matchup_rank: Optional[int]
    vegas_implied_team_total: Optional[float] = None

@dataclass(frozen=True)
class DSTSignals:
    opponent_offense_rank: Optional[int]
    opponent_implied_points: Optional[float] = None

PlayerSignals = Union[SkillSignals, KickerSignals, DSTSignals]

# --- Output ---

@dataclass
class Recommendation:
    verdict: Verdict
    score: float
    reasons: list[str]
    low_confidence: bool
    scoring_format: ScoringFormat

# --- Constants ---

START_THRESHOLD = 70.0
SIT_THRESHOLD   = 45.0

INJURY_VETO    = {"Out", "Doubtful"}
INJURY_PENALTY = {"Questionable"}
INJURY_PENALTY_PTS = 15.0

# --- Public API ---

def score_player(
    signals: PlayerSignals,
    scoring_format: ScoringFormat = ScoringFormat.PPR,
) -> Recommendation:
    if isinstance(signals, SkillSignals):
        return _score_skill(signals, scoring_format)
    elif isinstance(signals, KickerSignals):
        return _score_kicker(signals, scoring_format)
    elif isinstance(signals, DSTSignals):
        return _score_dst(signals, scoring_format)
    raise TypeError(f"Unknown signal type: {type(signals)}")
```

### Weight Redistribution Helper

```python
def _redistribute(weights: dict[str, float], absent: set[str]) -> dict[str, float]:
    present = {k: v for k, v in weights.items() if k not in absent}
    total = sum(present.values())
    if total == 0:
        return present
    return {k: v / total for k, v in present.items()}
```

### Matchup Rank to Sub-score Conversion

```python
def _matchup_sub_score(rank: Optional[int]) -> Optional[float]:
    """Rank 1 (easiest) -> 100, Rank 32 (toughest) -> 0."""
    if rank is None:
        return None
    return round(100.0 * (32 - rank) / 31, 2)
```

### Usage Average Helper

```python
def _avg_usage(weekly: list[Optional[float]]) -> Optional[float]:
    present = [v for v in weekly if v is not None]
    return sum(present) / len(present) if present else None
```

### Test Fixture Pattern (per position)

```python
# tests/test_engine.py
import pytest
from src.fantasy.engine import (
    score_player, SkillSignals, KickerSignals, DSTSignals,
    ScoringFormat, Verdict
)

@pytest.fixture
def wr_start_signals():
    return SkillSignals(
        position="WR",
        matchup_rank=2,             # top-3 = very favorable
        injury_status=None,
        snap_pct_l4w=[0.92, 0.88, 0.90, 0.91],
        usage_share_l4w=[0.28, 0.30, 0.25, 0.27],
        projected_points=18.5,
    )

@pytest.fixture
def rb_out_signals():
    return SkillSignals(
        position="RB",
        matchup_rank=5,
        injury_status="Out",
        snap_pct_l4w=[0.75, 0.80, 0.78, 0.82],
        usage_share_l4w=[0.35, 0.32, 0.38, 0.36],
        projected_points=12.0,
    )

def test_out_always_sit(rb_out_signals):
    rec = score_player(rb_out_signals, ScoringFormat.PPR)
    assert rec.verdict == Verdict.SIT
    assert rec.reasons[0].startswith("Hard SIT")

def test_favorable_wr_starts(wr_start_signals):
    rec = score_player(wr_start_signals, ScoringFormat.PPR)
    assert rec.verdict == Verdict.START
    assert 3 <= len(rec.reasons) <= 5

def test_reasons_count_never_below_3(kicker_signals):
    rec = score_player(kicker_signals, ScoringFormat.STANDARD)
    assert len(rec.reasons) >= 3
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Free-form LLM-generated narrative | Structured template strings (decided pre-build) | Pre-build decision | Deterministic, testable, no LLM dependency |
| Per-position separate scoring functions only | Shared dispatcher `score_player()` routing to position-specific scorers | Phase 2 design | Single public API surface for Phase 3 |
| Mutable ORM objects passed to engine | Frozen dataclasses as engine inputs | Phase 2 design | Immutable inputs prevent state bugs; pure function guarantee |

**Deprecated/outdated:**
- Passing `Player` ORM objects directly to the engine: Phase 3 routes extract scalar values and construct `PlayerSignals`. The engine must never see SQLAlchemy objects.

---

## Open Questions

1. **Projected points scale for sub-score conversion**
   - What we know: `projected_points` is a float (e.g., 8.0 for a poor game, 25.0 for an elite game); typical fantasy range is ~5–35 pts
   - What's unclear: What ceiling to use for the 0–100 normalization (divide by 30? 35?)
   - Recommendation: Use 30.0 as ceiling (`min(100, projected_points / 30.0 * 100)`); add a constant `PROJECTED_POINTS_CEILING = 30.0` so it can be adjusted without touching formulas.

2. **Usage signal for QB (no carry_share, no target_share)**
   - What we know: QB has snap_pct_l4w but no meaningful usage_share (QBs don't have a "share" metric)
   - What's unclear: Whether to use snap_pct as the sole usage signal for QB, or disable the usage dimension entirely for QB
   - Recommendation: Use `snap_pct` as the usage signal for QB (it captures starter vs. backup distinction). Document this clearly in engine.py.

3. **Verdict tie-break at exact threshold boundaries**
   - What we know: score exactly 70 = START (>=70), score exactly 45 = FLEX (45–69)
   - What's unclear: This is actually clear from CONTEXT.md thresholds — no tie-break needed
   - Recommendation: Implement as `>= 70 -> START`, `>= 45 -> FLEX`, `< 45 -> SIT`. No issue.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest >=9.0.2 |
| Config file | `pyproject.toml` [tool.pytest.ini_options] — testpaths=["tests"], addopts="-x -q" |
| Quick run command | `uv run pytest tests/test_engine.py -x -q` |
| Full suite command | `uv run pytest -x -q` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RECD-01 | `score_player()` returns `Verdict.START/SIT/FLEX` | unit | `uv run pytest tests/test_engine.py::test_verdict_enum -x` | Wave 0 |
| RECD-01 | Score >=70 yields START, 45-69 yields FLEX, <45 yields SIT | unit | `uv run pytest tests/test_engine.py::test_threshold_boundaries -x` | Wave 0 |
| RECD-02 | `reasons` list has 3–5 entries for every position | unit | `uv run pytest tests/test_engine.py::test_reasons_count -x` | Wave 0 |
| RECD-02 | First reason is the summary string | unit | `uv run pytest tests/test_engine.py::test_reasons_order -x` | Wave 0 |
| RECD-03 | Matchup rank contributes to composite score | unit | `uv run pytest tests/test_engine.py::test_matchup_signal_effect -x` | Wave 0 |
| RECD-06 | projected_points=None excludes signal (weight redistributed) | unit | `uv run pytest tests/test_engine.py::test_projected_points_none -x` | Wave 0 |
| RECD-07 | PPR format increases score vs. standard for WR/TE | unit | `uv run pytest tests/test_engine.py::test_ppr_boosts_pass_catcher -x` | Wave 0 |
| RECD-07 | PPR format has no effect on QB score | unit | `uv run pytest tests/test_engine.py::test_ppr_no_effect_qb -x` | Wave 0 |
| RECD-08 | Fewer than 4 non-None week entries sets low_confidence=True | unit | `uv run pytest tests/test_engine.py::test_low_confidence_flag -x` | Wave 0 |
| RECD-08 | K and DST always have low_confidence=False | unit | `uv run pytest tests/test_engine.py::test_k_dst_no_low_confidence -x` | Wave 0 |
| POS-01 | QB/RB/WR/TE each produce valid Recommendation | unit | `uv run pytest tests/test_engine.py::test_all_skill_positions -x` | Wave 0 |
| POS-02 | KickerSignals produces valid Recommendation with >=3 reasons | unit | `uv run pytest tests/test_engine.py::test_kicker_position -x` | Wave 0 |
| POS-03 | DSTSignals produces valid Recommendation with >=3 reasons | unit | `uv run pytest tests/test_engine.py::test_dst_position -x` | Wave 0 |
| RECD-01 | injury_status="Out" always yields SIT regardless of other signals | unit | `uv run pytest tests/test_engine.py::test_out_always_sit -x` | Wave 0 |
| RECD-01 | injury_status="Doubtful" always yields SIT | unit | `uv run pytest tests/test_engine.py::test_doubtful_always_sit -x` | Wave 0 |
| RECD-01 | score always in [0.0, 100.0] range | unit | `uv run pytest tests/test_engine.py::test_score_clamped -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_engine.py -x -q`
- **Per wave merge:** `uv run pytest -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_engine.py` — all engine unit tests (covers all phase requirements); does not exist yet
- [ ] `src/fantasy/engine.py` — the engine module itself; does not exist yet

*(conftest.py and pytest config exist from Phase 1 — no new framework setup needed)*

---

## Sources

### Primary (HIGH confidence)

- Direct code inspection: `src/fantasy/db/models.py` — Player and Matchup column names, types, and constraints verified
- Direct code inspection: `src/fantasy/normalize.py` — week1–week4 convention and signal derivation confirmed
- Direct code inspection: `tests/conftest.py`, `tests/test_normalize.py` — pytest fixture patterns and test style
- Direct code inspection: `pyproject.toml` — pytest >=9.0.2 confirmed installed; no new deps needed
- `.planning/phases/02-recommendation-engine/02-CONTEXT.md` — all scoring decisions, thresholds, and signal contracts

### Secondary (MEDIUM confidence)

- Python stdlib docs (dataclasses, enum) — stable APIs, no version concerns for Python 3.13

### Tertiary (LOW confidence)

- None — all findings supported by direct code inspection or authoritative stdlib docs

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; pure stdlib; pyproject.toml inspected directly
- Architecture: HIGH — signal contracts derived directly from existing ORM models and CONTEXT.md locked decisions
- Pitfalls: HIGH — derived from direct analysis of implementation constraints (frozen dataclasses, weight math, K/DST padding rules)

**Research date:** 2026-03-25
**Valid until:** 2026-06-25 (stable — pure Python stdlib, no external API dependencies)
