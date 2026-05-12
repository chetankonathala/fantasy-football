"""Value Based Drafting (VBD) — replacement-level fantasy value computation.

For a 12-team league with standard roster (1QB / 2RB / 2WR / 1TE / 1FLEX / DST / K):
  - QB: replacement = roster size of starters across league (≈12)
  - RB: 2 starters per team = 24, plus a portion of flex slots → ~30
  - WR: 2 starters per team = 24, plus the remainder of flex slots → ~36
  - TE: 1 starter per team = 12, with limited TE-flex usage → ~14

VBD = redraft_value − replacement_redraft_value, clamped at 0.

Tier breaks: detect significant gaps in VBD within position by computing
consecutive deltas and flagging breakpoints where delta > k * median delta.
"""
from __future__ import annotations

from dataclasses import dataclass

# Replacement-level cutoff (1-indexed position rank). Tuned for 12-team PPR.
REPLACEMENT_CUTOFFS: dict[str, int] = {
    "QB": 12,
    "RB": 30,
    "WR": 36,
    "TE": 14,
}


@dataclass
class VBDPlayer:
    name: str
    position: str
    redraft_value: int
    redraft_position_rank: int | None


def compute_vbd(players: list[VBDPlayer]) -> dict[str, dict]:
    """Compute VBD per player and tier breaks per position.

    Returns dict keyed by player name with keys:
      vbd, tier (1..N), is_tier_break (bool), replacement_value
    """
    by_position: dict[str, list[VBDPlayer]] = {}
    for p in players:
        by_position.setdefault(p.position, []).append(p)

    out: dict[str, dict] = {}

    for pos, group in by_position.items():
        # Sort by redraft_value desc, fall back to position rank
        group.sort(
            key=lambda x: (-(x.redraft_value or 0), x.redraft_position_rank or 999)
        )

        cutoff = REPLACEMENT_CUTOFFS.get(pos, 24)
        replacement_val = 0
        if len(group) >= cutoff:
            replacement_val = group[cutoff - 1].redraft_value or 0

        # Tier-break detection: gaps in VBD relative to median gap
        vbds = [max(0, (p.redraft_value or 0) - replacement_val) for p in group]
        gaps = [vbds[i] - vbds[i + 1] for i in range(len(vbds) - 1)]

        # Median gap among the top-N where N≈cutoff (tier structure matters at the top)
        relevant_gaps = gaps[: max(cutoff, 8)]
        sorted_gaps = sorted(relevant_gaps, reverse=True)
        # k=2 means breakpoints are gaps ≥ 2× the median of top-cutoff gaps
        median_gap = sorted_gaps[len(sorted_gaps) // 2] if sorted_gaps else 0
        threshold = max(median_gap * 2, 200)  # 200 abs floor so ties don't trigger

        tier = 1
        for i, p in enumerate(group):
            vbd = max(0, (p.redraft_value or 0) - replacement_val)
            is_break = i > 0 and i - 1 < len(gaps) and gaps[i - 1] >= threshold
            if is_break:
                tier += 1
            out[p.name] = {
                "vbd": vbd,
                "tier": tier,
                "is_tier_break": is_break,
                "replacement_value": replacement_val,
                "position_rank_within_format": i + 1,
            }

    return out


def positional_scarcity(players: list[VBDPlayer]) -> dict[str, float]:
    """Score how concentrated positional value is at the top.

    Returns {position: 0-100 scarcity score}. Higher = more cliff-like
    (small group of stars, sharp drop), lower = flatter / fungible.
    """
    by_position: dict[str, list[VBDPlayer]] = {}
    for p in players:
        by_position.setdefault(p.position, []).append(p)

    out: dict[str, float] = {}
    for pos, group in by_position.items():
        if not group:
            continue
        group.sort(key=lambda x: -(x.redraft_value or 0))
        cutoff = REPLACEMENT_CUTOFFS.get(pos, 24)
        top = group[: min(len(group), cutoff)]
        if len(top) < 4:
            out[pos] = 50.0
            continue
        top_3_avg = sum(p.redraft_value for p in top[:3]) / 3
        rest_avg = sum(p.redraft_value for p in top[3:]) / max(1, len(top) - 3)
        if rest_avg <= 0:
            out[pos] = 100.0
            continue
        ratio = top_3_avg / rest_avg
        # Clamp ratio 1.0–4.0 → score 0–100
        score = max(0.0, min(100.0, (ratio - 1.0) / 3.0 * 100.0))
        out[pos] = score

    return out
