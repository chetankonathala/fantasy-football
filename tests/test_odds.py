"""Tests for The Odds API fetch module (TDD RED phase)."""
from unittest.mock import patch, MagicMock

import src.fantasy.fetch.odds as odds_module
from src.fantasy.fetch.odds import fetch_game_lines, _normalize_team


# ---------------------------------------------------------------------------
# Helper: build a minimal Odds API event response
# ---------------------------------------------------------------------------

def _make_odds_event(
    home_team="Kansas City Chiefs",
    away_team="Buffalo Bills",
    commence_time="2025-11-16T18:00:00Z",
    game_total=47.5,
    home_spread=-3.5,
):
    return {
        "id": "abc123",
        "home_team": home_team,
        "away_team": away_team,
        "commence_time": commence_time,
        "bookmakers": [
            {
                "key": "draftkings",
                "markets": [
                    {
                        "key": "totals",
                        "outcomes": [
                            {"name": "Over", "point": game_total},
                            {"name": "Under", "point": game_total},
                        ],
                    },
                    {
                        "key": "spreads",
                        "outcomes": [
                            {"name": home_team, "point": home_spread},
                            {"name": away_team, "point": -home_spread},
                        ],
                    },
                ],
            }
        ],
    }


def _mock_resp(data):
    r = MagicMock()
    r.json.return_value = data
    r.raise_for_status.return_value = None
    return r


# ---------------------------------------------------------------------------
# Test 1: fetch_game_lines returns list of dicts with required keys
# ---------------------------------------------------------------------------

def test_fetch_game_lines_returns_required_keys(monkeypatch):
    """Test 1: fetch_game_lines returns list of dicts with all expected keys."""
    monkeypatch.setenv("ODDS_API_KEY", "test-key")

    mock_now = MagicMock()
    mock_now.weekday.return_value = 2  # Wednesday

    with patch("src.fantasy.fetch.odds.requests.get", return_value=_mock_resp([_make_odds_event()])), \
         patch("src.fantasy.fetch.odds.datetime") as mock_dt:
        mock_dt.now.return_value = mock_now
        mock_dt.now.return_value.weekday.return_value = 2
        # allow timezone.utc passthrough
        from datetime import timezone
        mock_dt.now.side_effect = lambda tz=None: mock_now

        result = fetch_game_lines(week=12)

    assert isinstance(result, list)
    assert len(result) == 1
    expected_keys = {
        "week", "home_team", "away_team", "game_total", "home_spread",
        "home_implied_total", "away_implied_total",
    }
    assert expected_keys.issubset(set(result[0].keys()))


# ---------------------------------------------------------------------------
# Test 2: Implied totals computed correctly
# ---------------------------------------------------------------------------

def test_fetch_game_lines_implied_total_math(monkeypatch):
    """Test 2: For game_total=47.5, home_spread=-3.5: home_implied=25.5, away_implied=22.0."""
    monkeypatch.setenv("ODDS_API_KEY", "test-key")

    mock_now = MagicMock()
    mock_now.weekday.return_value = 2

    with patch("src.fantasy.fetch.odds.requests.get",
               return_value=_mock_resp([_make_odds_event(game_total=47.5, home_spread=-3.5)])), \
         patch("src.fantasy.fetch.odds.datetime") as mock_dt:
        mock_dt.now.side_effect = lambda tz=None: mock_now

        result = fetch_game_lines(week=12)

    assert len(result) == 1
    assert result[0]["home_implied_total"] == 25.5
    assert result[0]["away_implied_total"] == 22.0


# ---------------------------------------------------------------------------
# Test 3: fetch_game_lines returns empty list when API returns no events
# ---------------------------------------------------------------------------

def test_fetch_game_lines_empty_when_no_events(monkeypatch):
    """Test 3: fetch_game_lines returns empty list when API returns no events."""
    monkeypatch.setenv("ODDS_API_KEY", "test-key")

    mock_now = MagicMock()
    mock_now.weekday.return_value = 2

    with patch("src.fantasy.fetch.odds.requests.get", return_value=_mock_resp([])), \
         patch("src.fantasy.fetch.odds.datetime") as mock_dt:
        mock_dt.now.side_effect = lambda tz=None: mock_now

        result = fetch_game_lines(week=12)

    assert result == []


# ---------------------------------------------------------------------------
# Additional: no API key returns empty list
# ---------------------------------------------------------------------------

def test_fetch_game_lines_no_api_key(monkeypatch):
    """fetch_game_lines returns empty list when ODDS_API_KEY is not set."""
    monkeypatch.delenv("ODDS_API_KEY", raising=False)
    result = fetch_game_lines(week=17)
    assert result == []


# ---------------------------------------------------------------------------
# Additional: day-of-week guard skips non-Wed-Sat days
# ---------------------------------------------------------------------------

def test_fetch_game_lines_skips_outside_window(monkeypatch):
    """fetch_game_lines returns empty list on Sunday (weekday=6)."""
    monkeypatch.setenv("ODDS_API_KEY", "test-key")

    mock_now = MagicMock()
    mock_now.weekday.return_value = 6  # Sunday

    with patch("src.fantasy.fetch.odds.datetime") as mock_dt:
        mock_dt.now.side_effect = lambda tz=None: mock_now
        result = fetch_game_lines(week=17)

    assert result == []


# ---------------------------------------------------------------------------
# Additional: _normalize_team maps known names to abbreviations
# ---------------------------------------------------------------------------

def test_normalize_team_known_names():
    """_normalize_team correctly maps known team names to abbreviations."""
    assert _normalize_team("Kansas City Chiefs") == "KC"
    assert _normalize_team("Buffalo Bills") == "BUF"
    assert _normalize_team("Las Vegas Raiders") == "LV"
    assert _normalize_team("Los Angeles Rams") == "LAR"
    assert _normalize_team("Los Angeles Chargers") == "LAC"
