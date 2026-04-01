"""Tests for Open-Meteo weather fetch module (TDD RED phase)."""
from unittest.mock import patch, MagicMock

from src.fantasy.fetch.weather import (
    fetch_weather,
    DOME_TEAMS,
    WIND_THRESHOLD_MPH,
    PRECIP_THRESHOLD_PCT,
)


# ---------------------------------------------------------------------------
# Helper: build a minimal Open-Meteo hourly response
# ---------------------------------------------------------------------------

def _make_meteo_response(wind_mph=10.0, precip_pct=20, game_date="2025-11-16"):
    target_time = f"{game_date}T13:00"
    return {
        "hourly": {
            "time": [target_time],
            "wind_speed_10m": [wind_mph],
            "precipitation_probability": [precip_pct],
        }
    }


def _make_game_line(home_team="KC", game_date="2025-11-16"):
    return {
        "week": 12,
        "home_team": home_team,
        "away_team": "BUF",
        "game_total": 47.5,
        "home_spread": -3.5,
        "home_implied_total": 25.5,
        "away_implied_total": 22.0,
        "game_date": game_date,
    }


# ---------------------------------------------------------------------------
# Test 4: DOME_TEAMS contains exactly the expected 11 teams
# ---------------------------------------------------------------------------

def test_dome_teams_contains_expected_teams():
    """Test 4: DOME_TEAMS frozenset contains exactly ARI, ATL, DAL, DET, HOU, IND, LV, LAR, LAC, MIN, NO."""
    expected = frozenset({"ARI", "ATL", "DAL", "DET", "HOU", "IND", "LV", "LAR", "LAC", "MIN", "NO"})
    assert DOME_TEAMS == expected


# ---------------------------------------------------------------------------
# Test 5: fetch_weather skips dome teams
# ---------------------------------------------------------------------------

def test_fetch_weather_skips_dome_teams():
    """Test 5: Dome teams get is_dome=True, weather_flag=False, wind/precip=None."""
    game_lines = [_make_game_line(home_team="DAL", game_date="2025-11-16")]

    with patch("src.fantasy.fetch.weather.requests.get") as mock_get:
        result = fetch_weather(game_lines)

    # requests.get should NOT be called for dome teams
    mock_get.assert_not_called()

    assert len(result) == 1
    row = result[0]
    assert row["is_dome"] is True
    assert row["weather_flag"] is False
    assert row["wind_mph"] is None
    assert row["precip_probability"] is None


# ---------------------------------------------------------------------------
# Test 6: weather_flag=True when wind_mph > WIND_THRESHOLD_MPH (15)
# ---------------------------------------------------------------------------

def test_fetch_weather_flag_true_high_wind():
    """Test 6: weather_flag=True when wind_mph > 15."""
    game_lines = [_make_game_line(home_team="KC", game_date="2025-11-16")]

    mock_resp = MagicMock()
    mock_resp.json.return_value = _make_meteo_response(wind_mph=20.0, precip_pct=10)
    mock_resp.raise_for_status.return_value = None

    with patch("src.fantasy.fetch.weather.requests.get", return_value=mock_resp):
        result = fetch_weather(game_lines)

    assert len(result) == 1
    row = result[0]
    assert row["is_dome"] is False
    assert row["wind_mph"] == 20.0
    assert row["weather_flag"] is True


# ---------------------------------------------------------------------------
# Test 7: weather_flag=True when precip_probability > PRECIP_THRESHOLD_PCT (30)
# ---------------------------------------------------------------------------

def test_fetch_weather_flag_true_high_precip():
    """Test 7: weather_flag=True when precip_probability > 30."""
    game_lines = [_make_game_line(home_team="KC", game_date="2025-11-16")]

    mock_resp = MagicMock()
    mock_resp.json.return_value = _make_meteo_response(wind_mph=5.0, precip_pct=45)
    mock_resp.raise_for_status.return_value = None

    with patch("src.fantasy.fetch.weather.requests.get", return_value=mock_resp):
        result = fetch_weather(game_lines)

    assert len(result) == 1
    row = result[0]
    assert row["weather_flag"] is True
    assert row["precip_probability"] == 45


# ---------------------------------------------------------------------------
# Test 8: weather_flag=False when wind and precip are below thresholds
# ---------------------------------------------------------------------------

def test_fetch_weather_flag_false_normal_conditions():
    """Test 8: weather_flag=False when wind_mph <= 15 and precip_probability <= 30."""
    game_lines = [_make_game_line(home_team="KC", game_date="2025-11-16")]

    mock_resp = MagicMock()
    mock_resp.json.return_value = _make_meteo_response(wind_mph=10.0, precip_pct=20)
    mock_resp.raise_for_status.return_value = None

    with patch("src.fantasy.fetch.weather.requests.get", return_value=mock_resp):
        result = fetch_weather(game_lines)

    assert len(result) == 1
    row = result[0]
    assert row["is_dome"] is False
    assert row["wind_mph"] == 10.0
    assert row["precip_probability"] == 20
    assert row["weather_flag"] is False


# ---------------------------------------------------------------------------
# Additional: fetch_weather handles request errors gracefully
# ---------------------------------------------------------------------------

def test_fetch_weather_handles_request_error():
    """fetch_weather sets weather_flag=False and None values when request fails."""
    import requests as req
    game_lines = [_make_game_line(home_team="KC", game_date="2025-11-16")]

    with patch("src.fantasy.fetch.weather.requests.get",
               side_effect=req.RequestException("timeout")):
        result = fetch_weather(game_lines)

    assert len(result) == 1
    row = result[0]
    assert row["wind_mph"] is None
    assert row["precip_probability"] is None
    assert row["weather_flag"] is False


# ---------------------------------------------------------------------------
# Additional: fetch_weather with empty list returns empty list
# ---------------------------------------------------------------------------

def test_fetch_weather_empty_list():
    """fetch_weather with empty input returns empty list."""
    result = fetch_weather([])
    assert result == []


# ---------------------------------------------------------------------------
# Additional: thresholds match expected constants
# ---------------------------------------------------------------------------

def test_thresholds():
    """WIND_THRESHOLD_MPH=15 and PRECIP_THRESHOLD_PCT=30."""
    assert WIND_THRESHOLD_MPH == 15
    assert PRECIP_THRESHOLD_PCT == 30
