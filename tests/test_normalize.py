"""Tests for the normalization layer — Sleeper + nflverse data → Player/Matchup dicts."""
import pytest
import polars as pl
from datetime import datetime, timezone

from src.fantasy.normalize import normalize_players, normalize_matchups


@pytest.fixture
def crosswalk_df():
    """Polars crosswalk DataFrame with 3 players having gsis_id and sleeper_id."""
    return pl.DataFrame({
        "gsis_id": ["00-0001111", "00-0002222", "00-0003333"],
        "sleeper_id": ["123", "456", "789"],
    })


@pytest.fixture
def stats_df_4weeks():
    """Polars stats DataFrame with target_share and carries for 3 players over 4 weeks."""
    rows = []
    # player gsis_id -> target_share/carries per week
    player_data = [
        ("00-0001111", "KC", 0.30, 0.0),   # QB — target_share high, no carries
        ("00-0002222", "KC", 0.15, 5.0),   # RB — some target_share and carries
        ("00-0003333", "SF", 0.20, 0.0),   # WR — target_share, no carries
    ]
    for week in [14, 15, 16, 17]:
        for pid, team, ts, carries in player_data:
            rows.append({
                "player_id": pid,
                "recent_team": team,
                "week": week,
                "target_share": ts,
                "carries": carries,
                "targets": ts * 10,
                "receptions": ts * 8,
                "rushing_yards": carries * 4.0,
                "receiving_yards": ts * 80.0,
                "passing_yards": 0.0,
            })
    return pl.DataFrame(rows)


@pytest.fixture
def snaps_df_4weeks():
    """Polars snap counts DataFrame with offense_pct for 3 players over 4 weeks."""
    rows = []
    player_data = [
        ("00-0001111", "KC", 0.95),
        ("00-0002222", "KC", 0.70),
        ("00-0003333", "SF", 0.85),
    ]
    for week in [14, 15, 16, 17]:
        for pid, team, snap_pct in player_data:
            rows.append({
                "pfr_id": pid,   # snap counts use pfr_id mapped from player_id
                "player_id": pid,
                "team": team,
                "week": week,
                "offense_pct": snap_pct,
            })
    return pl.DataFrame(rows)


@pytest.fixture
def sleeper_players_fixture():
    """Sleeper players dict matching the crosswalk sleeper_ids, including a punter."""
    return {
        "123": {
            "full_name": "Patrick Mahomes",
            "first_name": "Patrick",
            "last_name": "Mahomes",
            "position": "QB",
            "team": "KC",
            "injury_status": None,
            "practice_participation": None,
            "status": "Active",
            "injury_start_date": None,
        },
        "456": {
            "full_name": "Travis Kelce",
            "first_name": "Travis",
            "last_name": "Kelce",
            "position": "TE",
            "team": "KC",
            "injury_status": None,
            "practice_participation": None,
            "status": "Active",
            "injury_start_date": None,
        },
        "789": {
            "full_name": "Deebo Samuel",
            "first_name": "Deebo",
            "last_name": "Samuel",
            "position": "WR",
            "team": "SF",
            "injury_status": None,
            "practice_participation": None,
            "status": "Active",
            "injury_start_date": None,
        },
        "999": {
            "full_name": "Sample Punter",
            "first_name": "Sample",
            "last_name": "Punter",
            "position": "P",  # punter — should be excluded
            "team": "BUF",
            "injury_status": None,
            "practice_participation": None,
            "status": "Active",
            "injury_start_date": None,
        },
    }


def test_normalize_players_joins_ids(
    sleeper_players_fixture, stats_df_4weeks, snaps_df_4weeks, crosswalk_df
):
    """Output dicts should contain both nflverse_id and sleeper_id."""
    result = normalize_players(
        sleeper_players=sleeper_players_fixture,
        stats_df=stats_df_4weeks,
        snaps_df=snaps_df_4weeks,
        crosswalk_df=crosswalk_df,
        current_week=18,
    )

    assert len(result) > 0
    for player_dict in result:
        assert "nflverse_id" in player_dict, "nflverse_id must be present"
        assert "sleeper_id" in player_dict, "sleeper_id must be present"
        # Must not be None
        assert player_dict["nflverse_id"] is not None
        assert player_dict["sleeper_id"] is not None


def test_normalize_players_week_stats(
    sleeper_players_fixture, stats_df_4weeks, snaps_df_4weeks, crosswalk_df
):
    """week1_snap_pct should correspond to the most recent week (current_week - 1)."""
    result = normalize_players(
        sleeper_players=sleeper_players_fixture,
        stats_df=stats_df_4weeks,
        snaps_df=snaps_df_4weeks,
        crosswalk_df=crosswalk_df,
        current_week=18,
    )

    # Find Mahomes (sleeper_id=123, gsis_id=00-0001111)
    mahomes = next((p for p in result if p["sleeper_id"] == "123"), None)
    assert mahomes is not None

    # current_week=18, so:
    # week1 = week 17 (most recent), week2 = 16, week3 = 15, week4 = 14
    assert mahomes.get("week1_snap_pct") is not None
    assert mahomes.get("week4_snap_pct") is not None

    # All 4 weeks in mock data have snap_pct=0.95 for Mahomes
    assert abs(mahomes["week1_snap_pct"] - 0.95) < 0.01
    assert abs(mahomes["week4_snap_pct"] - 0.95) < 0.01


def test_normalize_players_filters_positions(
    sleeper_players_fixture, stats_df_4weeks, snaps_df_4weeks, crosswalk_df
):
    """Punter (position='P') should be excluded from output."""
    result = normalize_players(
        sleeper_players=sleeper_players_fixture,
        stats_df=stats_df_4weeks,
        snaps_df=snaps_df_4weeks,
        crosswalk_df=crosswalk_df,
        current_week=18,
    )

    positions = {p["position"] for p in result}
    assert "P" not in positions

    # No sleeper_id=999 (the punter) should appear
    punter = next((p for p in result if p.get("sleeper_id") == "999"), None)
    assert punter is None


def test_normalize_players_missing_stats(
    sleeper_players_fixture, crosswalk_df
):
    """Player in crosswalk but missing from stats — week fields should be None."""
    # Use empty stats/snaps DataFrames
    empty_stats = pl.DataFrame({
        "player_id": pl.Series([], dtype=pl.Utf8),
        "recent_team": pl.Series([], dtype=pl.Utf8),
        "week": pl.Series([], dtype=pl.Int64),
        "target_share": pl.Series([], dtype=pl.Float64),
        "carries": pl.Series([], dtype=pl.Float64),
        "targets": pl.Series([], dtype=pl.Float64),
        "receptions": pl.Series([], dtype=pl.Float64),
        "rushing_yards": pl.Series([], dtype=pl.Float64),
        "receiving_yards": pl.Series([], dtype=pl.Float64),
        "passing_yards": pl.Series([], dtype=pl.Float64),
    })
    empty_snaps = pl.DataFrame({
        "player_id": pl.Series([], dtype=pl.Utf8),
        "team": pl.Series([], dtype=pl.Utf8),
        "week": pl.Series([], dtype=pl.Int64),
        "offense_pct": pl.Series([], dtype=pl.Float64),
    })

    result = normalize_players(
        sleeper_players=sleeper_players_fixture,
        stats_df=empty_stats,
        snaps_df=empty_snaps,
        crosswalk_df=crosswalk_df,
        current_week=18,
    )

    for player_dict in result:
        assert player_dict.get("week1_snap_pct") is None
        assert player_dict.get("week1_target_share") is None
        assert player_dict.get("week1_carry_share") is None


def test_normalize_matchups_valid():
    """Valid DVP dicts should all be returned unchanged."""
    dvp_results = [
        {"week": 18, "team": "KC", "position": "QB", "dvp_score": 25.5, "opponent_rank": 1},
        {"week": 18, "team": "SF", "position": "RB", "dvp_score": 18.2, "opponent_rank": 2},
        {"week": 18, "team": "BUF", "position": "WR", "dvp_score": 22.0, "opponent_rank": 3},
    ]
    result = normalize_matchups(dvp_results)
    assert len(result) == 3
    assert result[0]["team"] == "KC"
    assert result[1]["position"] == "RB"
