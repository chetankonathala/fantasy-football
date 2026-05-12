"""FantasyCalc API client — fetch dynasty trade values for players and picks."""
import requests

FANTASYCALC_URL = "https://api.fantasycalc.com/values/current"


def fetch_dynasty_values(
    is_dynasty: bool = True,
    num_qbs: int = 1,
    num_teams: int = 12,
    ppr: int = 1,
) -> list[dict]:
    """Fetch all dynasty trade values from FantasyCalc.

    Returns a list of entry dicts, each containing:
      - player: {id, name, sleeperId, position, maybeTeam, maybeAge, ...}
      - value: int (dynasty trade value, higher = better)
      - overallRank: int
      - positionRank: int
      - trend30Day: int (positive = rising, negative = falling)
    """
    params = {
        "isDynasty": str(is_dynasty).lower(),
        "numQbs": num_qbs,
        "numTeams": num_teams,
        "ppr": ppr,
    }
    resp = requests.get(FANTASYCALC_URL, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def is_pick_entry(entry: dict) -> bool:
    """Return True if this FantasyCalc entry represents a draft pick."""
    name: str = entry.get("player", {}).get("name", "")
    return "Pick" in name or "pick" in name


def fetch_redraft_values(num_qbs: int = 1, num_teams: int = 12, ppr: int = 1) -> list[dict]:
    """Fetch redraft (single-season) values from FantasyCalc.

    Same shape as dynasty values, but `value` reflects 2026-only fantasy production
    consensus rather than long-term dynasty asset value. Use for depth charts and
    year-1 opportunity assessment.
    """
    return fetch_dynasty_values(is_dynasty=False, num_qbs=num_qbs, num_teams=num_teams, ppr=ppr)
