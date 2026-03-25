"""Engine unit tests — Wave 1 (GREEN phase).

All 16 test functions are present. test_verdict_enum passes immediately
(checks enum members only). All remaining 15 tests now assert real behavior
against the complete implementation in Plan 02.

Import: from src.fantasy.engine import score_player, SkillSignals, ...
"""

import pytest

from src.fantasy.engine import (
    DSTSignals,
    KickerSignals,
    Recommendation,
    ScoringFormat,
    SkillSignals,
    Verdict,
    score_player,
)


# ---------------------------------------------------------------------------
# Fixtures (no DB required — pure signal dataclass construction)
# ---------------------------------------------------------------------------


@pytest.fixture
def wr_start_signals():
    return SkillSignals(
        position="WR",
        matchup_rank=2,
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


@pytest.fixture
def rb_doubtful_signals():
    return SkillSignals(
        position="RB",
        matchup_rank=5,
        injury_status="Doubtful",
        snap_pct_l4w=[0.75, 0.80, 0.78, 0.82],
        usage_share_l4w=[0.35, 0.32, 0.38, 0.36],
        projected_points=12.0,
    )


@pytest.fixture
def qb_healthy_signals():
    return SkillSignals(
        position="QB",
        matchup_rank=10,
        injury_status=None,
        snap_pct_l4w=[0.98, 0.95, 1.0, 0.97],
        usage_share_l4w=[None, None, None, None],  # QB has no usage share
        projected_points=20.0,
    )


@pytest.fixture
def te_healthy_signals():
    return SkillSignals(
        position="TE",
        matchup_rank=8,
        injury_status=None,
        snap_pct_l4w=[0.80, 0.78, 0.82, 0.75],
        usage_share_l4w=[0.22, 0.20, 0.24, 0.18],
        projected_points=12.0,
    )


@pytest.fixture
def low_confidence_signals():
    return SkillSignals(
        position="WR",
        matchup_rank=15,
        injury_status=None,
        snap_pct_l4w=[0.60, 0.55, None, None],  # only 2 weeks of data
        usage_share_l4w=[0.10, 0.12, None, None],
        projected_points=8.0,
    )


@pytest.fixture
def kicker_signals():
    return KickerSignals(matchup_rank=5, vegas_implied_team_total=None)


@pytest.fixture
def dst_signals():
    return DSTSignals(opponent_offense_rank=3, opponent_implied_points=None)


@pytest.fixture
def worst_case_signals():
    return SkillSignals(
        position="WR",
        matchup_rank=32,
        injury_status="Questionable",
        snap_pct_l4w=[0.10, 0.08, 0.05, 0.12],
        usage_share_l4w=[0.02, 0.03, 0.01, 0.02],
        projected_points=2.0,
    )


@pytest.fixture
def best_case_signals():
    return SkillSignals(
        position="WR",
        matchup_rank=1,
        injury_status=None,
        snap_pct_l4w=[1.0, 1.0, 1.0, 1.0],
        usage_share_l4w=[0.40, 0.38, 0.42, 0.39],
        projected_points=30.0,
    )


# ---------------------------------------------------------------------------
# Test 1: Verdict enum members (PASSES in Wave 0 — enum check only)
# ---------------------------------------------------------------------------


def test_verdict_enum():
    """Verdict enum has exactly START, SIT, FLEX — no more, no less."""
    assert set(Verdict) == {Verdict.START, Verdict.SIT, Verdict.FLEX}


# ---------------------------------------------------------------------------
# Tests 2-16: GREEN phase — real assertions against full implementation.
# ---------------------------------------------------------------------------


def test_threshold_boundaries():
    """Score thresholds: >=70 = START, 45-69 = FLEX, <45 = SIT."""
    signals = SkillSignals(
        position="WR",
        matchup_rank=1,
        injury_status=None,
        snap_pct_l4w=[1.0, 1.0, 1.0, 1.0],
        usage_share_l4w=[0.40, 0.40, 0.40, 0.40],
        projected_points=30.0,
    )
    rec = score_player(signals, ScoringFormat.PPR)
    assert rec.verdict == Verdict.START
    assert rec.score >= 70.0


def test_out_always_sit(rb_out_signals):
    """injury_status='Out' always yields Verdict.SIT regardless of other signals."""
    rec = score_player(rb_out_signals, ScoringFormat.PPR)
    assert rec.verdict == Verdict.SIT
    assert rec.reasons[0].startswith("Hard SIT")


def test_doubtful_always_sit(rb_doubtful_signals):
    """injury_status='Doubtful' always yields Verdict.SIT."""
    rec = score_player(rb_doubtful_signals, ScoringFormat.PPR)
    assert rec.verdict == Verdict.SIT


def test_score_clamped(best_case_signals, worst_case_signals):
    """score is always in [0.0, 100.0] range — test with best-case and worst-case inputs."""
    rec_best = score_player(best_case_signals, ScoringFormat.PPR)
    rec_worst = score_player(worst_case_signals, ScoringFormat.PPR)
    assert 0.0 <= rec_best.score <= 100.0
    assert 0.0 <= rec_worst.score <= 100.0


def test_reasons_count(wr_start_signals, kicker_signals, dst_signals):
    """Every position produces 3-5 reasons."""
    rec_wr = score_player(wr_start_signals, ScoringFormat.PPR)
    rec_k = score_player(kicker_signals, ScoringFormat.STANDARD)
    rec_dst = score_player(dst_signals, ScoringFormat.STANDARD)
    assert 3 <= len(rec_wr.reasons) <= 5
    assert 3 <= len(rec_k.reasons) <= 5
    assert 3 <= len(rec_dst.reasons) <= 5


def test_reasons_order(wr_start_signals):
    """First reason is a summary string that contains the verdict value."""
    rec = score_player(wr_start_signals, ScoringFormat.PPR)
    assert rec.verdict.value in rec.reasons[0]


def test_matchup_signal_effect():
    """Better matchup_rank produces higher score than worse rank (all else equal)."""
    easy_matchup = SkillSignals(
        position="WR",
        matchup_rank=1,
        injury_status=None,
        snap_pct_l4w=[0.85, 0.85, 0.85, 0.85],
        usage_share_l4w=[0.25, 0.25, 0.25, 0.25],
        projected_points=15.0,
    )
    tough_matchup = SkillSignals(
        position="WR",
        matchup_rank=32,
        injury_status=None,
        snap_pct_l4w=[0.85, 0.85, 0.85, 0.85],
        usage_share_l4w=[0.25, 0.25, 0.25, 0.25],
        projected_points=15.0,
    )
    rec_easy = score_player(easy_matchup, ScoringFormat.PPR)
    rec_tough = score_player(tough_matchup, ScoringFormat.PPR)
    assert rec_easy.score > rec_tough.score


def test_projected_points_none():
    """projected_points=None still produces a valid Recommendation (weight redistributed)."""
    signals = SkillSignals(
        position="WR",
        matchup_rank=10,
        injury_status=None,
        snap_pct_l4w=[0.80, 0.78, 0.82, 0.75],
        usage_share_l4w=[0.22, 0.20, 0.24, 0.18],
        projected_points=None,
    )
    rec = score_player(signals, ScoringFormat.PPR)
    assert isinstance(rec, Recommendation)
    assert 0.0 <= rec.score <= 100.0
    assert 3 <= len(rec.reasons) <= 5


def test_ppr_boosts_pass_catcher(wr_start_signals):
    """PPR score > STANDARD score for WR with target_share data."""
    rec_ppr = score_player(wr_start_signals, ScoringFormat.PPR)
    rec_std = score_player(wr_start_signals, ScoringFormat.STANDARD)
    assert rec_ppr.score > rec_std.score


def test_ppr_no_effect_qb(qb_healthy_signals):
    """PPR format has no effect on QB score (QB has no target/carry share)."""
    rec_ppr = score_player(qb_healthy_signals, ScoringFormat.PPR)
    rec_std = score_player(qb_healthy_signals, ScoringFormat.STANDARD)
    assert rec_ppr.score == pytest.approx(rec_std.score)


def test_low_confidence_flag(low_confidence_signals):
    """SkillSignals with only 2 non-None weeks yields low_confidence=True."""
    rec = score_player(low_confidence_signals, ScoringFormat.PPR)
    assert rec.low_confidence is True


def test_k_dst_no_low_confidence(kicker_signals, dst_signals):
    """KickerSignals and DSTSignals always have low_confidence=False."""
    rec_k = score_player(kicker_signals, ScoringFormat.STANDARD)
    rec_dst = score_player(dst_signals, ScoringFormat.STANDARD)
    assert rec_k.low_confidence is False
    assert rec_dst.low_confidence is False


@pytest.mark.parametrize(
    "position,snap_pct,usage_share,projected",
    [
        ("QB", [0.98, 0.95, 1.0, 0.97], [None, None, None, None], 20.0),
        ("RB", [0.75, 0.80, 0.78, 0.82], [0.35, 0.32, 0.38, 0.36], 12.0),
        ("WR", [0.92, 0.88, 0.90, 0.91], [0.28, 0.30, 0.25, 0.27], 18.5),
        ("TE", [0.80, 0.78, 0.82, 0.75], [0.22, 0.20, 0.24, 0.18], 12.0),
    ],
)
def test_all_skill_positions(position, snap_pct, usage_share, projected):
    """QB, RB, WR, TE each produce a valid Recommendation."""
    signals = SkillSignals(
        position=position,
        matchup_rank=10,
        injury_status=None,
        snap_pct_l4w=snap_pct,
        usage_share_l4w=usage_share,
        projected_points=projected,
    )
    rec = score_player(signals, ScoringFormat.PPR)
    assert isinstance(rec, Recommendation)
    assert rec.verdict in {Verdict.START, Verdict.SIT, Verdict.FLEX}
    assert 3 <= len(rec.reasons) <= 5


def test_kicker_position(kicker_signals):
    """KickerSignals with matchup_rank produces valid Recommendation with >=3 reasons."""
    rec = score_player(kicker_signals, ScoringFormat.STANDARD)
    assert isinstance(rec, Recommendation)
    assert rec.verdict in {Verdict.START, Verdict.SIT, Verdict.FLEX}
    assert len(rec.reasons) >= 3
    assert rec.low_confidence is False


def test_dst_position(dst_signals):
    """DSTSignals with opponent_offense_rank produces valid Recommendation with >=3 reasons."""
    rec = score_player(dst_signals, ScoringFormat.STANDARD)
    assert isinstance(rec, Recommendation)
    assert rec.verdict in {Verdict.START, Verdict.SIT, Verdict.FLEX}
    assert len(rec.reasons) >= 3
    assert rec.low_confidence is False
