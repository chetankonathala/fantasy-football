"""Recommendation engine: pure function converting typed player signals to START/SIT/FLEX verdicts.

This module has ZERO imports from src.fantasy.db or SQLAlchemy.
Only stdlib: dataclasses, enum, typing.

Phase 2 (Plan 01): Types, enums, dataclasses, constants, and stub functions.
Phase 2 (Plan 02): Full scoring implementation (_score_skill, _score_kicker, _score_dst).
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Union


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ScoringFormat(Enum):
    PPR = "ppr"
    HALF_PPR = "half_ppr"
    STANDARD = "standard"


class Verdict(Enum):
    START = "START"
    SIT = "SIT"
    FLEX = "FLEX"


# ---------------------------------------------------------------------------
# Signal dataclasses (frozen=True — immutable inputs guarantee pure function)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SkillSignals:
    """Signals for QB, RB, WR, TE.

    - snap_pct_l4w: week1 = most recent, week4 = oldest; None = no data for that week
    - usage_share_l4w: target_share for WR/TE, carry_share for RB, None values for QB
      (QB uses snap_pct as its sole usage proxy — no meaningful "share" metric)
    - matchup_rank: 1 = most pts allowed = easiest matchup (CONTEXT.md convention)
    """

    position: str                           # "QB" | "RB" | "WR" | "TE"
    matchup_rank: Optional[int]             # 1-32; 1 = easiest (most pts allowed)
    injury_status: Optional[str]            # "Out" | "Doubtful" | "Questionable" | None
    snap_pct_l4w: list[Optional[float]]     # [week1, week2, week3, week4]; None = no data
    usage_share_l4w: list[Optional[float]]  # target/carry share or None (QB has all None)
    projected_points: Optional[float]       # pass-through; None = excluded from score


@dataclass(frozen=True)
class KickerSignals:
    """Signals for K (Kicker).

    - matchup_rank: opponent rank vs kickers from DVP; 1 = easiest
    - vegas_implied_team_total: optional pass-through; None in Phase 2 (Vegas data is Phase 4)
    """

    matchup_rank: Optional[int]
    vegas_implied_team_total: Optional[float] = None


@dataclass(frozen=True)
class DSTSignals:
    """Signals for DST.

    - opponent_offense_rank: 1 = worst offense = easiest matchup for DST
    - opponent_implied_points: optional pass-through; None in Phase 2 (Vegas data is Phase 4)
    """

    opponent_offense_rank: Optional[int]
    opponent_implied_points: Optional[float] = None


# Union type alias for the public dispatcher
PlayerSignals = Union[SkillSignals, KickerSignals, DSTSignals]


# ---------------------------------------------------------------------------
# Output dataclass — Phase 3 API contract (do NOT change shape post-Phase 2)
# ---------------------------------------------------------------------------


@dataclass
class Recommendation:
    """Engine output.

    - verdict: START / SIT / FLEX
    - score: composite score 0.0-100.0
    - reasons: 3-5 structured template strings; reasons[0] is always the summary
    - low_confidence: True if fewer than 4 non-None weeks of usage data (skill positions only)
    - scoring_format: the format used to compute this recommendation
    """

    verdict: Verdict
    score: float                     # 0.0-100.0
    reasons: list[str]               # 3-5 template strings; first is summary
    low_confidence: bool             # True only for SkillSignals with < 4 data weeks
    scoring_format: ScoringFormat


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

START_THRESHOLD = 70.0
SIT_THRESHOLD = 45.0

INJURY_VETO = {"Out", "Doubtful"}
INJURY_PENALTY_PTS = 15.0

PROJECTED_POINTS_CEILING = 30.0

SKILL_WEIGHTS = {
    "matchup": 0.30,
    "usage": 0.30,
    "projected": 0.25,
    "confidence": 0.15,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def score_player(
    signals: PlayerSignals,
    scoring_format: ScoringFormat = ScoringFormat.PPR,
) -> Recommendation:
    """Convert typed player signals into a deterministic START/SIT/FLEX recommendation.

    Routes to the correct position scorer based on signal type.
    """
    if isinstance(signals, SkillSignals):
        return _score_skill(signals, scoring_format)
    elif isinstance(signals, KickerSignals):
        return _score_kicker(signals, scoring_format)
    elif isinstance(signals, DSTSignals):
        return _score_dst(signals, scoring_format)
    raise TypeError(f"Unknown signal type: {type(signals)}")


# ---------------------------------------------------------------------------
# Private stubs (implemented in Plan 02)
# ---------------------------------------------------------------------------


def _score_skill(signals: SkillSignals, fmt: ScoringFormat) -> Recommendation:
    """Score a skill position player (QB, RB, WR, TE). Implementation in Plan 02."""
    raise NotImplementedError("Implementation in Plan 02")


def _score_kicker(signals: KickerSignals, fmt: ScoringFormat) -> Recommendation:
    """Score a kicker. Implementation in Plan 02."""
    raise NotImplementedError("Implementation in Plan 02")


def _score_dst(signals: DSTSignals, fmt: ScoringFormat) -> Recommendation:
    """Score a DST. Implementation in Plan 02."""
    raise NotImplementedError("Implementation in Plan 02")
