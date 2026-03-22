"""Tests for scripts/refresh.py — refresh orchestration, off-season guard, error handling."""
import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

# Add project root to sys.path so scripts.refresh import works
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.refresh import main  # noqa: E402


@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging handlers between tests to prevent state leakage."""
    yield
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    refresh_logger = logging.getLogger("refresh")
    refresh_logger.handlers.clear()


@patch("scripts.refresh.fetch_sleeper_players")
@patch("scripts.refresh.nfl")
def test_offseason_guard(mock_nfl, mock_fetch):
    """When week is 23 (off-season), main() returns season_active=False without calling fetch."""
    mock_nfl.get_current_week.return_value = 23

    result = main()

    assert result["season_active"] is False
    assert result["players_upserted"] == 0
    assert result["matchups_upserted"] == 0
    mock_fetch.assert_not_called()


@patch("scripts.refresh.upsert_matchups", return_value=96)
@patch("scripts.refresh.upsert_players", return_value=500)
@patch("scripts.refresh.get_session_factory")
@patch("scripts.refresh.get_engine")
@patch("scripts.refresh.normalize_matchups", return_value=[{"week": 10}])
@patch("scripts.refresh.normalize_players", return_value=[{"nflverse_id": "abc"}])
@patch("scripts.refresh.compute_dvp", return_value=[])
@patch("scripts.refresh.load_pbp")
@patch("scripts.refresh.load_ff_playerids")
@patch("scripts.refresh.load_snap_counts")
@patch("scripts.refresh.load_player_stats")
@patch("scripts.refresh.fetch_sleeper_players", return_value={"123": {"position": "QB"}})
@patch("scripts.refresh.nfl")
def test_inseason_runs(
    mock_nfl,
    mock_fetch,
    mock_stats,
    mock_snaps,
    mock_crosswalk,
    mock_pbp,
    mock_dvp,
    mock_norm_players,
    mock_norm_matchups,
    mock_engine,
    mock_session_factory,
    mock_upsert_players,
    mock_upsert_matchups,
):
    """When week is 10 (in-season), main() calls fetch and upsert functions."""
    mock_nfl.get_current_week.return_value = 10
    mock_nfl.get_current_season.return_value = 2025

    # Set up session context manager
    mock_session = MagicMock()
    mock_session_factory.return_value.__enter__ = MagicMock(return_value=mock_session)
    mock_session_factory.return_value.__exit__ = MagicMock(return_value=False)
    mock_session_factory.return_value.return_value.__enter__ = MagicMock(return_value=mock_session)
    mock_session_factory.return_value.return_value.__exit__ = MagicMock(return_value=False)

    # Make SessionFactory() work as context manager
    session_cm = MagicMock()
    session_cm.__enter__ = MagicMock(return_value=mock_session)
    session_cm.__exit__ = MagicMock(return_value=False)
    mock_session_factory.return_value.return_value = session_cm

    result = main()

    assert result["season_active"] is True
    mock_fetch.assert_called_once()
    mock_upsert_players.assert_called_once()
    mock_upsert_matchups.assert_called_once()


@patch("scripts.refresh.upsert_players")
@patch("scripts.refresh.fetch_sleeper_players")
@patch("scripts.refresh.nfl")
def test_fetch_failure_retains_data(mock_nfl, mock_fetch, mock_upsert):
    """When fetch_sleeper_players raises RequestException, upsert is NOT called."""
    mock_nfl.get_current_week.return_value = 10
    mock_nfl.get_current_season.return_value = 2025
    mock_fetch.side_effect = requests.RequestException("timeout")

    result = main()

    assert result["players_upserted"] == 0
    mock_upsert.assert_not_called()


@patch("scripts.refresh.upsert_matchups", return_value=96)
@patch("scripts.refresh.upsert_players", return_value=500)
@patch("scripts.refresh.get_session_factory")
@patch("scripts.refresh.get_engine")
@patch("scripts.refresh.normalize_matchups", return_value=[])
@patch("scripts.refresh.normalize_players", return_value=[])
@patch("scripts.refresh.compute_dvp", return_value=[])
@patch("scripts.refresh.load_pbp")
@patch("scripts.refresh.load_ff_playerids")
@patch("scripts.refresh.load_snap_counts")
@patch("scripts.refresh.load_player_stats")
@patch("scripts.refresh.fetch_sleeper_players", return_value={})
@patch("scripts.refresh.nfl")
def test_refresh_returns_stats(
    mock_nfl,
    mock_fetch,
    mock_stats,
    mock_snaps,
    mock_crosswalk,
    mock_pbp,
    mock_dvp,
    mock_norm_players,
    mock_norm_matchups,
    mock_engine,
    mock_session_factory,
    mock_upsert_players,
    mock_upsert_matchups,
):
    """Successful run returns dict with correct keys and counts."""
    mock_nfl.get_current_week.return_value = 10
    mock_nfl.get_current_season.return_value = 2025

    # Set up session context manager
    mock_session = MagicMock()
    session_cm = MagicMock()
    session_cm.__enter__ = MagicMock(return_value=mock_session)
    session_cm.__exit__ = MagicMock(return_value=False)
    mock_session_factory.return_value.return_value = session_cm

    result = main()

    assert "season_active" in result
    assert "players_upserted" in result
    assert "matchups_upserted" in result
    assert result["season_active"] is True
    assert result["players_upserted"] == 500
    assert result["matchups_upserted"] == 96


@patch("scripts.refresh.upsert_matchups", return_value=0)
@patch("scripts.refresh.upsert_players", return_value=0)
@patch("scripts.refresh.get_session_factory")
@patch("scripts.refresh.get_engine")
@patch("scripts.refresh.normalize_matchups", return_value=[])
@patch("scripts.refresh.normalize_players", return_value=[])
@patch("scripts.refresh.compute_dvp", return_value=[])
@patch("scripts.refresh.load_pbp")
@patch("scripts.refresh.load_ff_playerids")
@patch("scripts.refresh.load_snap_counts")
@patch("scripts.refresh.load_player_stats")
@patch("scripts.refresh.fetch_sleeper_players", return_value={})
@patch("scripts.refresh.nfl")
def test_logging_configured(
    mock_nfl,
    mock_fetch,
    mock_stats,
    mock_snaps,
    mock_crosswalk,
    mock_pbp,
    mock_dvp,
    mock_norm_players,
    mock_norm_matchups,
    mock_engine,
    mock_session_factory,
    mock_upsert_players,
    mock_upsert_matchups,
):
    """After main() call, refresh.log handler is a TimedRotatingFileHandler with backupCount=7."""
    mock_nfl.get_current_week.return_value = 10
    mock_nfl.get_current_season.return_value = 2025

    # Set up session context manager
    mock_session = MagicMock()
    session_cm = MagicMock()
    session_cm.__enter__ = MagicMock(return_value=mock_session)
    session_cm.__exit__ = MagicMock(return_value=False)
    mock_session_factory.return_value.return_value = session_cm

    main()

    # Check root logger handlers for TimedRotatingFileHandler
    root_logger = logging.getLogger()
    timed_handlers = [
        h for h in root_logger.handlers if isinstance(h, TimedRotatingFileHandler)
    ]
    assert len(timed_handlers) >= 1
    assert timed_handlers[0].backupCount == 7
