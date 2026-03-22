"""Tests for nflverse PBP schema validation, carry share, and DVP computation."""
import pytest
import polars as pl

from src.fantasy.fetch.nflverse import (
    validate_pbp_schema,
    compute_carry_share,
    compute_dvp,
    REQUIRED_PBP_COLUMNS,
)


def test_pbp_schema_valid(mock_pbp_df):
    """Full mock PBP DataFrame should pass schema validation."""
    valid, missing = validate_pbp_schema(mock_pbp_df)
    assert valid is True
    assert missing == []


def test_pbp_schema_missing_column(mock_pbp_df):
    """Dropping 'defteam' should cause schema validation to fail with that column listed."""
    df_no_defteam = mock_pbp_df.drop("defteam")
    valid, missing = validate_pbp_schema(df_no_defteam)
    assert valid is False
    assert "defteam" in missing


def test_compute_carry_share(mock_stats_df):
    """carry_share = player_carries / team_carries per week."""
    result = compute_carry_share(mock_stats_df)

    # Verify expected columns
    assert "player_id" in result.columns
    assert "week" in result.columns
    assert "carry_share" in result.columns

    # For week 14: KC players — player 00-0000002 has 8 carries, 00-0000001 has 0
    # team_carries for KC in week 14 = 8 + 0 = 8
    # 00-0000002 carry_share = 8/8 = 1.0
    # 00-0000001 carry_share = 0/8 = 0.0 (but filtered since carries > 0 for team_carries)
    # SF players — 00-0000004 has 12 carries, team_carries = 12
    # 00-0000004 carry_share = 12/12 = 1.0

    week14 = result.filter(pl.col("week") == 14)
    sf_carrier = week14.filter(pl.col("player_id") == "00-0000004")
    assert len(sf_carrier) == 1
    assert abs(sf_carrier["carry_share"][0] - 1.0) < 0.01


def test_compute_dvp_returns_correct_shape(mock_pbp_df):
    """compute_dvp should return a list of dicts with expected keys."""
    results = compute_dvp(mock_pbp_df, current_week=18, season=2025)

    assert isinstance(results, list)
    assert len(results) > 0

    expected_keys = {"week", "team", "position", "dvp_score", "opponent_rank"}
    for row in results:
        assert expected_keys.issubset(row.keys()), f"Missing keys in: {row}"


def test_compute_dvp_ranks_correctly(mock_pbp_df):
    """Rank 1 should go to the defense that allowed the most fantasy points."""
    results = compute_dvp(mock_pbp_df, current_week=18, season=2025)

    # Find the team with rank 1 for each position — should be the highest dvp_score
    for pos in set(r["position"] for r in results):
        pos_rows = [r for r in results if r["position"] == pos]
        if len(pos_rows) > 1:
            rank1 = [r for r in pos_rows if r["opponent_rank"] == 1]
            if rank1:
                max_score = max(r["dvp_score"] for r in pos_rows)
                assert abs(rank1[0]["dvp_score"] - max_score) < 0.01, (
                    f"Rank 1 for {pos} should have max dvp_score. "
                    f"Got {rank1[0]['dvp_score']}, max is {max_score}"
                )
