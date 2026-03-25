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

FORMAT_MODIFIERS = {
    ScoringFormat.PPR: {"usage_delta": 0.05, "projected_delta": 0.05},
    ScoringFormat.HALF_PPR: {"usage_delta": 0.025, "projected_delta": 0.025},
    ScoringFormat.STANDARD: {"usage_delta": 0.0, "projected_delta": 0.0},
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
# Private helpers
# ---------------------------------------------------------------------------


def _redistribute(weights: dict[str, float], absent: set[str]) -> dict[str, float]:
    """Remove absent keys from weights and redistribute their weight proportionally.

    Returns a new dict with weights summing to 1.0 (or empty dict if all absent).
    """
    remaining = {k: v for k, v in weights.items() if k not in absent}
    if not remaining:
        return {}
    total = sum(remaining.values())
    if total == 0.0:
        return remaining
    factor = 1.0 / total
    return {k: v * factor for k, v in remaining.items()}


def _matchup_sub_score(rank: Optional[int]) -> Optional[float]:
    """Convert matchup rank (1=easiest, 32=toughest) to a 0-100 sub-score.

    rank 1 -> 100.0, rank 32 -> 0.0
    """
    if rank is None:
        return None
    return round(100.0 * (32 - rank) / 31, 2)


def _avg_usage(weekly: list[Optional[float]]) -> Optional[float]:
    """Average of non-None values; returns None if all entries are None."""
    values = [v for v in weekly if v is not None]
    if not values:
        return None
    return sum(values) / len(values)


def _count_data_weeks(weekly: list[Optional[float]]) -> int:
    """Count non-None entries in a weekly list."""
    return sum(1 for v in weekly if v is not None)


def _apply_injury_veto(injury_status: Optional[str]) -> Optional[str]:
    """Return a veto reason string if injury_status triggers a hard SIT, else None."""
    if injury_status in INJURY_VETO:
        return f"Hard SIT: {injury_status} — player ruled out"
    return None


def _verdict_from_score(score: float) -> Verdict:
    """Determine verdict from composite score using fixed thresholds."""
    if score >= START_THRESHOLD:
        return Verdict.START
    elif score >= SIT_THRESHOLD:
        return Verdict.FLEX
    else:
        return Verdict.SIT


# ---------------------------------------------------------------------------
# Reason builder helpers
# ---------------------------------------------------------------------------


def _summary_reason(verdict: Verdict, primary_signal: str) -> str:
    """Build a summary reason string with the verdict and primary signal."""
    if verdict == Verdict.START:
        return f"Strong {verdict.value}: {primary_signal}"
    return f"{verdict.value}: {primary_signal}"


def _matchup_reason(rank: int, position: str) -> str:
    """Build a matchup reason string based on rank."""
    if rank <= 10:
        return f"Favorable matchup: #{rank} defense vs {position}"
    elif rank <= 20:
        return f"Neutral matchup: #{rank} defense vs {position}"
    else:
        return f"Tough matchup: #{rank} defense vs {position}"


def _usage_reason(avg_share: float, position: str, weeks: int) -> str:
    """Build a usage reason string for a skill position."""
    if position == "QB":
        label = "snap share"
    elif position in ("WR", "TE"):
        label = "target share"
    else:  # RB
        label = "carry share"
    pct = round(avg_share * 100)
    if avg_share >= 0.20:
        return f"Strong usage: {pct}% {label} (L{weeks}W)"
    else:
        return f"Low usage: {pct}% {label} (L{weeks}W)"


def _projected_reason(pts: float) -> str:
    """Build a projected points reason string."""
    return f"Projected: {pts:.1f} fantasy points"


def _low_confidence_reason(weeks: int) -> str:
    """Build a low-confidence reason string."""
    return f"Low confidence: only {weeks} week(s) of data available"


def _pad_reasons(reasons: list[str], min_count: int = 3, max_count: int = 5) -> list[str]:
    """Pad reasons to at least min_count and truncate to max_count."""
    padding = [
        "Limited signal set — matchup is primary factor",
        "No additional risk factors identified",
    ]
    result = list(reasons)
    pad_idx = 0
    while len(result) < min_count and pad_idx < len(padding):
        result.append(padding[pad_idx])
        pad_idx += 1
    return result[:max_count]


# ---------------------------------------------------------------------------
# Private position scorers
# ---------------------------------------------------------------------------


def _score_skill(signals: SkillSignals, fmt: ScoringFormat) -> Recommendation:
    """Score a skill position player (QB, RB, WR, TE)."""
    # Step 1: Check injury veto
    veto_reason = _apply_injury_veto(signals.injury_status)
    if veto_reason is not None:
        reasons = _pad_reasons([veto_reason])
        return Recommendation(
            verdict=Verdict.SIT,
            score=0.0,
            reasons=reasons,
            low_confidence=False,
            scoring_format=fmt,
        )

    # Step 2: Compute sub-scores
    matchup_sub = _matchup_sub_score(signals.matchup_rank)

    snap_avg = _avg_usage(signals.snap_pct_l4w)
    usage_share_avg = _avg_usage(signals.usage_share_l4w)

    # Compute usage_sub based on position
    if signals.position in ("WR", "TE"):
        if snap_avg is not None and usage_share_avg is not None:
            usage_sub: Optional[float] = (snap_avg * 0.4 + usage_share_avg * 0.6) * 100
        elif snap_avg is not None:
            usage_sub = snap_avg * 100
        elif usage_share_avg is not None:
            usage_sub = usage_share_avg * 100
        else:
            usage_sub = None
    elif signals.position == "RB":
        if snap_avg is not None and usage_share_avg is not None:
            usage_sub = (snap_avg * 0.4 + usage_share_avg * 0.6) * 100
        elif snap_avg is not None:
            usage_sub = snap_avg * 100
        elif usage_share_avg is not None:
            usage_sub = usage_share_avg * 100
        else:
            usage_sub = None
    else:  # QB
        usage_sub = snap_avg * 100 if snap_avg is not None else None

    projected_sub: Optional[float] = None
    if signals.projected_points is not None:
        projected_sub = min(100.0, (signals.projected_points / PROJECTED_POINTS_CEILING) * 100)

    confidence_sub = _count_data_weeks(signals.snap_pct_l4w) / 4.0 * 100

    # Step 3: Determine absent signals and redistribute base weights
    absent: set[str] = set()
    if matchup_sub is None:
        absent.add("matchup")
    if usage_sub is None:
        absent.add("usage")
    if projected_sub is None:
        absent.add("projected")

    weights = _redistribute(dict(SKILL_WEIGHTS), absent)

    # Step 4: Apply PPR format modifier for WR/TE — additive boost (no renormalization)
    # The deltas increase total weight above 1.0, giving extra credit to pass-catcher signals.
    if signals.position in ("WR", "TE") and weights:
        mods = FORMAT_MODIFIERS[fmt]
        if "usage" in weights:
            weights["usage"] = weights["usage"] + mods["usage_delta"]
        if "projected" in weights:
            weights["projected"] = weights["projected"] + mods["projected_delta"]

    # Step 5: Compute composite score
    sub_scores = {
        "matchup": matchup_sub,
        "usage": usage_sub,
        "projected": projected_sub,
        "confidence": confidence_sub,
    }
    composite = 0.0
    for key, weight in weights.items():
        sub = sub_scores[key]
        if sub is not None:
            composite += weight * sub

    # Step 6: Apply Questionable injury penalty
    if signals.injury_status == "Questionable":
        composite -= INJURY_PENALTY_PTS

    # Step 7: Clamp
    composite = min(100.0, max(0.0, composite))

    # Step 8: Determine verdict
    verdict = _verdict_from_score(composite)

    # Step 9: Determine low_confidence
    data_weeks = _count_data_weeks(signals.snap_pct_l4w)
    low_confidence = data_weeks < 4

    # Step 10: Build reasons
    # Determine primary signal description for summary
    weighted_contributions = {}
    for key, weight in weights.items():
        sub = sub_scores[key]
        if sub is not None:
            weighted_contributions[key] = weight * sub

    primary_signal_key = max(weighted_contributions, key=lambda k: weighted_contributions[k]) if weighted_contributions else "matchup"

    primary_descriptions = {
        "matchup": "elite matchup" if (matchup_sub is not None and matchup_sub >= 70) else "favorable matchup" if (matchup_sub is not None and matchup_sub >= 40) else "matchup grade",
        "usage": "high usage" if (usage_sub is not None and usage_sub >= 60) else "usage trend",
        "projected": "strong projection" if (projected_sub is not None and projected_sub >= 60) else "projection",
        "confidence": "consistent availability",
    }
    primary_description = primary_descriptions.get(primary_signal_key, "composite signals")

    reasons: list[str] = [_summary_reason(verdict, primary_description)]

    if matchup_sub is not None and signals.matchup_rank is not None:
        reasons.append(_matchup_reason(signals.matchup_rank, signals.position))

    # Usage reason: determine appropriate avg and label
    if usage_sub is not None:
        if signals.position == "QB":
            usage_avg_for_reason = snap_avg if snap_avg is not None else 0.0
            snap_weeks = _count_data_weeks(signals.snap_pct_l4w)
            reasons.append(_usage_reason(usage_avg_for_reason, signals.position, snap_weeks))
        else:
            # Use usage_share_avg if available, else snap_avg
            if usage_share_avg is not None:
                usage_avg_for_reason = usage_share_avg
            else:
                usage_avg_for_reason = snap_avg if snap_avg is not None else 0.0
            usage_weeks = _count_data_weeks(signals.usage_share_l4w) if usage_share_avg is not None else _count_data_weeks(signals.snap_pct_l4w)
            reasons.append(_usage_reason(usage_avg_for_reason, signals.position, usage_weeks))

    if projected_sub is not None and signals.projected_points is not None:
        reasons.append(_projected_reason(signals.projected_points))

    if low_confidence:
        reasons.append(_low_confidence_reason(data_weeks))

    reasons = _pad_reasons(reasons)

    return Recommendation(
        verdict=verdict,
        score=composite,
        reasons=reasons,
        low_confidence=low_confidence,
        scoring_format=fmt,
    )


def _score_kicker(signals: KickerSignals, fmt: ScoringFormat) -> Recommendation:
    """Score a kicker."""
    # Step 1: matchup sub-score (default 50.0 if None)
    matchup_sub = _matchup_sub_score(signals.matchup_rank) if signals.matchup_rank is not None else 50.0

    # Step 2: vegas sub-score
    vegas_sub: Optional[float] = None
    if signals.vegas_implied_team_total is not None:
        vegas_sub = min(100.0, signals.vegas_implied_team_total / 30.0 * 100)

    # Step 3: Composite
    if vegas_sub is None:
        composite = matchup_sub
    else:
        composite = 0.6 * matchup_sub + 0.4 * vegas_sub

    # Step 4: Clamp
    composite = min(100.0, max(0.0, composite))

    # Step 5: Verdict
    verdict = _verdict_from_score(composite)

    # Step 6: Build reasons
    primary_desc = "elite matchup" if matchup_sub >= 70 else "favorable matchup" if matchup_sub >= 40 else "matchup grade"
    reasons: list[str] = [_summary_reason(verdict, primary_desc)]

    if signals.matchup_rank is not None:
        reasons.append(_matchup_reason(signals.matchup_rank, "K"))
    else:
        reasons.append("Vegas total unavailable — matchup is sole factor")

    if vegas_sub is None:
        reasons.append("Vegas total unavailable — matchup is sole factor")

    reasons.append("K scoring is matchup-dependent")
    reasons = _pad_reasons(reasons)

    return Recommendation(
        verdict=verdict,
        score=composite,
        reasons=reasons,
        low_confidence=False,
        scoring_format=fmt,
    )


def _score_dst(signals: DSTSignals, fmt: ScoringFormat) -> Recommendation:
    """Score a DST."""
    # Step 1: opponent sub-score (default 50.0 if None)
    opponent_sub = _matchup_sub_score(signals.opponent_offense_rank) if signals.opponent_offense_rank is not None else 50.0

    # Step 2: implied points sub-score (lower implied points = easier for DST)
    implied_sub: Optional[float] = None
    if signals.opponent_implied_points is not None:
        # Lower opponent implied points = better for DST; invert the scale
        implied_sub = min(100.0, max(0.0, 100.0 - (signals.opponent_implied_points / 30.0 * 100)))

    # Step 3: Composite
    if implied_sub is None:
        composite = opponent_sub
    else:
        composite = 0.6 * opponent_sub + 0.4 * implied_sub

    # Step 4: Clamp
    composite = min(100.0, max(0.0, composite))

    # Step 5: Verdict
    verdict = _verdict_from_score(composite)

    # Step 6: Build reasons
    primary_desc = "elite matchup" if opponent_sub >= 70 else "favorable matchup" if opponent_sub >= 40 else "matchup grade"
    reasons: list[str] = [_summary_reason(verdict, primary_desc)]

    if signals.opponent_offense_rank is not None:
        reasons.append(_matchup_reason(signals.opponent_offense_rank, "DST"))
    else:
        reasons.append("Opponent implied points unavailable — opponent rank is sole factor")

    if implied_sub is None:
        reasons.append("Opponent implied points unavailable — opponent rank is sole factor")

    reasons.append("DST scoring is opponent-dependent")
    reasons = _pad_reasons(reasons)

    return Recommendation(
        verdict=verdict,
        score=composite,
        reasons=reasons,
        low_confidence=False,
        scoring_format=fmt,
    )
