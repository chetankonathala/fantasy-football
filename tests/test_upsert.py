"""Tests for SQLite upsert helpers (TDD RED phase)."""
import pytest
from datetime import datetime, timezone

from src.fantasy.db.models import Player, Matchup
from src.fantasy.db.upsert import upsert_players, upsert_matchups


def _now():
    return datetime.now(timezone.utc)


def test_upsert_players_insert(db_session):
    """Test 1: upsert_players inserts a new player when nflverse_id does not exist."""
    player_data = [
        {
            "nflverse_id": "00-0099001",
            "full_name": "Patrick Mahomes",
            "position": "QB",
            "team": "KC",
            "updated_at": _now(),
        }
    ]
    upsert_players(db_session, player_data)

    players = db_session.query(Player).filter_by(nflverse_id="00-0099001").all()
    assert len(players) == 1
    assert players[0].full_name == "Patrick Mahomes"
    assert players[0].team == "KC"


def test_upsert_players_update_injury_status(db_session):
    """Test 2: upsert_players updates injury_status when nflverse_id already exists (no duplicate)."""
    player_data = [
        {
            "nflverse_id": "00-0099002",
            "full_name": "Travis Kelce",
            "position": "TE",
            "team": "KC",
            "injury_status": None,
            "updated_at": _now(),
        }
    ]
    upsert_players(db_session, player_data)

    # Update with injury status
    updated_data = [
        {
            "nflverse_id": "00-0099002",
            "full_name": "Travis Kelce",
            "position": "TE",
            "team": "KC",
            "injury_status": "Questionable",
            "updated_at": _now(),
        }
    ]
    upsert_players(db_session, updated_data)

    players = db_session.query(Player).filter_by(nflverse_id="00-0099002").all()
    assert len(players) == 1, "Should not create duplicate row"
    assert players[0].injury_status == "Questionable"


def test_upsert_players_updates_all_mutable_fields(db_session):
    """Test 3: upsert_players updates all mutable fields on conflict."""
    initial = [
        {
            "nflverse_id": "00-0099003",
            "full_name": "Justin Jefferson",
            "position": "WR",
            "team": "MIN",
            "injury_status": None,
            "practice_participation": None,
            "week1_snap_pct": 0.75,
            "week1_target_share": 0.25,
            "week1_carry_share": 0.0,
            "updated_at": _now(),
        }
    ]
    upsert_players(db_session, initial)

    updated = [
        {
            "nflverse_id": "00-0099003",
            "full_name": "Justin Jefferson",
            "position": "WR",
            "team": "MIN",
            "injury_status": "Doubtful",
            "practice_participation": "Limited",
            "week1_snap_pct": 0.50,
            "week1_target_share": 0.30,
            "week1_carry_share": 0.05,
            "updated_at": _now(),
        }
    ]
    upsert_players(db_session, updated)

    player = db_session.query(Player).filter_by(nflverse_id="00-0099003").one()
    assert player.injury_status == "Doubtful"
    assert player.practice_participation == "Limited"
    assert player.week1_snap_pct == 0.50
    assert player.week1_target_share == 0.30
    assert player.week1_carry_share == 0.05


def test_upsert_matchups_insert(db_session):
    """Test 4: upsert_matchups inserts a new matchup when (week, team, position) does not exist."""
    matchup_data = [
        {
            "week": 1,
            "team": "KC",
            "position": "QB",
            "opponent_rank": 5,
            "dvp_score": 22.3,
        }
    ]
    upsert_matchups(db_session, matchup_data)

    matchups = db_session.query(Matchup).filter_by(week=1, team="KC", position="QB").all()
    assert len(matchups) == 1
    assert matchups[0].dvp_score == 22.3
    assert matchups[0].opponent_rank == 5


def test_upsert_matchups_update_on_conflict(db_session):
    """Test 5: upsert_matchups updates dvp_score and opponent_rank when (week, team, position) already exists."""
    initial = [{"week": 2, "team": "SF", "position": "RB", "opponent_rank": 10, "dvp_score": 18.5}]
    upsert_matchups(db_session, initial)

    updated = [{"week": 2, "team": "SF", "position": "RB", "opponent_rank": 3, "dvp_score": 29.1}]
    upsert_matchups(db_session, updated)

    matchups = db_session.query(Matchup).filter_by(week=2, team="SF", position="RB").all()
    assert len(matchups) == 1, "Should not create duplicate row"
    assert matchups[0].dvp_score == 29.1
    assert matchups[0].opponent_rank == 3


def test_upsert_players_empty_list_no_raise(db_session):
    """Test 6: upsert_players with empty list does not raise and returns 0."""
    result = upsert_players(db_session, [])
    assert result == 0
