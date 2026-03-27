"""Tests for Sleeper API fetch and injury field extraction."""
import pytest
from unittest.mock import patch

from src.fantasy.fetch.sleeper import extract_player_data, fetch_sleeper_players
from src.fantasy.db.models import Player
from src.fantasy.db.upsert import upsert_players


def test_extract_player_healthy():
    """Player with injury_status=None should produce injury_status=''."""
    player = {
        "full_name": "Patrick Mahomes",
        "first_name": "Patrick",
        "last_name": "Mahomes",
        "position": "QB",
        "team": "KC",
        "injury_status": None,
        "practice_participation": None,
        "status": "Active",
        "injury_start_date": None,
    }
    result = extract_player_data("123", player)
    assert result["injury_status"] == ""


def test_extract_player_injured():
    """Player with injury_status='Questionable' should preserve the value."""
    player = {
        "full_name": "Travis Kelce",
        "first_name": "Travis",
        "last_name": "Kelce",
        "position": "TE",
        "team": "KC",
        "injury_status": "Questionable",
        "practice_participation": "Limited",
        "status": "Active",
        "injury_start_date": "2025-11-15",
    }
    result = extract_player_data("456", player)
    assert result["injury_status"] == "Questionable"


def test_extract_player_fields():
    """Returned dict should contain all expected keys matching Player model columns."""
    player = {
        "full_name": "Travis Kelce",
        "first_name": "Travis",
        "last_name": "Kelce",
        "position": "TE",
        "team": "KC",
        "injury_status": "Questionable",
        "practice_participation": "Limited",
        "status": "Active",
        "injury_start_date": "2025-11-15",
    }
    result = extract_player_data("456", player)
    expected_keys = {
        "sleeper_id",
        "full_name",
        "first_name",
        "last_name",
        "position",
        "team",
        "injury_status",
        "practice_participation",
        "status",
        "injury_start_date",
    }
    assert expected_keys.issubset(result.keys())
    assert result["sleeper_id"] == "456"


def test_player_upsert(db_session):
    """Extract player data, upsert to DB, query back and verify fields match."""
    player = {
        "full_name": "Patrick Mahomes",
        "first_name": "Patrick",
        "last_name": "Mahomes",
        "position": "QB",
        "team": "KC",
        "injury_status": None,
        "practice_participation": None,
        "status": "Active",
        "injury_start_date": None,
    }
    data = extract_player_data("123", player)
    # Add required nflverse_id for upsert
    data["nflverse_id"] = "00-0000001"
    from datetime import datetime, timezone
    data["updated_at"] = datetime.now(timezone.utc)

    count = upsert_players(db_session, [data])
    assert count > 0

    from sqlalchemy import select
    row = db_session.execute(select(Player).where(Player.nflverse_id == "00-0000001")).scalar_one()
    assert row.full_name == "Patrick Mahomes"
    assert row.injury_status == ""
    assert row.sleeper_id == "123"
    assert row.position == "QB"
    assert row.team == "KC"


def test_fetch_projected_points_fallback():
    """When requests.get raises HTTPError, fetch_projected_points returns empty dict."""
    import requests
    from src.fantasy.fetch.sleeper import fetch_projected_points

    with patch("requests.get") as mock_get:
        mock_get.side_effect = requests.exceptions.HTTPError("500 Server Error")
        result = fetch_projected_points(2025, 1)
    assert result == {}
