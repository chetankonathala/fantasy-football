"""Sleeper API client — fetch all NFL players and extract injury fields."""
import requests

SLEEPER_PLAYERS_URL = "https://api.sleeper.app/v1/players/nfl"


def fetch_sleeper_players() -> dict:
    """Fetch all NFL players from Sleeper API.

    Returns dict keyed by sleeper_player_id with player objects.
    Note: payload is ~5MB — call once per refresh cycle, not per lookup.
    """
    resp = requests.get(SLEEPER_PLAYERS_URL, timeout=30)
    resp.raise_for_status()
    return resp.json()


SLEEPER_PROJECTIONS_URL = "https://api.sleeper.com/projections/nfl/{season}/{week}"


def fetch_projected_points(season: int, week: int) -> dict:
    """Fetch weekly projections from Sleeper. Returns dict keyed by sleeper_player_id.

    Returns empty dict on any error (endpoint is undocumented/unreliable).
    """
    try:
        url = SLEEPER_PROJECTIONS_URL.format(season=season, week=week)
        resp = requests.get(url, params={"season_type": "regular"}, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return {}


def extract_projected_points(projections: dict, sleeper_id: str, scoring_format: str) -> float | None:
    """Extract pts_ppr/pts_half_ppr/pts_std for a player from projections dict."""
    player_proj = projections.get(sleeper_id)
    if not player_proj:
        return None
    field_map = {"ppr": "pts_ppr", "half_ppr": "pts_half_ppr", "standard": "pts_std"}
    return player_proj.get(field_map.get(scoring_format, "pts_ppr"))


def extract_player_data(sleeper_id: str, player: dict) -> dict:
    """Extract relevant fields from a single Sleeper player object.

    Returns dict with keys matching Player model columns.
    Normalizes injury_status=None to empty string per Pitfall 5
    (Sleeper returns null for healthy players, not 'Healthy').
    """
    return {
        "sleeper_id": sleeper_id,
        "full_name": player.get("full_name", ""),
        "first_name": player.get("first_name", ""),
        "last_name": player.get("last_name", ""),
        "position": player.get("position"),
        "team": player.get("team"),
        "injury_status": player.get("injury_status") or "",
        "practice_participation": player.get("practice_participation") or "",
        "status": player.get("status") or "",
        "injury_start_date": player.get("injury_start_date") or "",
    }
