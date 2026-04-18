"""ESPN Fantasy API client — fetches roster data for a specific team.

Credentials are read from env vars ESPN_S2 and ESPN_SWID.
Never hardcode credentials in source code.
"""
import os
import requests
from typing import Optional

ESPN_API_BASE = "https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl"

# Lineup slot ID → position label
SLOT_MAP: dict[int, str] = {
    0:  "QB",
    2:  "RB",
    4:  "WR",
    6:  "TE",
    16: "D/ST",
    17: "K",
    20: "BE",
    21: "BE",
    22: "BE",
    23: "FLEX",
    24: "IR",
}


def _get_credentials() -> tuple[str, str]:
    """Return (espn_s2, swid) from env vars. Raises if missing."""
    espn_s2 = os.environ.get("ESPN_S2", "")
    swid = os.environ.get("ESPN_SWID", "")
    if not espn_s2 or not swid:
        raise EnvironmentError(
            "ESPN_S2 and ESPN_SWID env vars are required. "
            "Set them in your .env or Render environment."
        )
    return espn_s2, swid


def fetch_league_rosters(
    league_id: int,
    season: int,
    espn_s2: Optional[str] = None,
    swid: Optional[str] = None,
) -> list[dict]:
    """Fetch all team rosters for a league. Returns raw team list from ESPN API."""
    if espn_s2 is None or swid is None:
        espn_s2, swid = _get_credentials()

    url = f"{ESPN_API_BASE}/seasons/{season}/segments/0/leagues/{league_id}"
    resp = requests.get(
        url,
        params={"view": ["mRoster", "mTeam"]},
        cookies={"espn_s2": espn_s2, "SWID": swid},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("teams", [])


def fetch_my_roster(
    league_id: int,
    team_id: int,
    season: int,
    espn_s2: Optional[str] = None,
    swid: Optional[str] = None,
) -> dict:
    """Fetch roster + metadata for a single team. Returns structured dict."""
    teams = fetch_league_rosters(league_id, season, espn_s2, swid)

    team = next((t for t in teams if t.get("id") == team_id), None)
    if team is None:
        raise ValueError(f"Team ID {team_id} not found in league {league_id}")

    record = team.get("record", {}).get("overall", {})
    players = []

    for entry in team.get("roster", {}).get("entries", []):
        slot_id = entry.get("lineupSlotId", 99)
        slot = SLOT_MAP.get(slot_id, "BE")
        pool = entry.get("playerPoolEntry", {})
        player = pool.get("player", {})

        espn_id = player.get("id")
        full_name = player.get("fullName", "")
        default_pos = player.get("defaultPositionId")

        # defaultPositionId: 1=QB, 2=RB, 3=WR, 4=TE, 5=K, 16=D/ST
        POS_ID_MAP = {1: "QB", 2: "RB", 3: "WR", 4: "TE", 5: "K", 16: "D/ST"}
        position = POS_ID_MAP.get(default_pos, slot if slot not in ("BE", "FLEX", "IR") else "")

        injury_status = pool.get("injuryStatus", "")
        on_ir = slot == "IR"
        is_bench = slot in ("BE", "IR")

        players.append({
            "espn_id": espn_id,
            "full_name": full_name,
            "position": position,
            "lineup_slot": slot,
            "is_bench": is_bench,
            "on_ir": on_ir,
            "espn_injury_status": injury_status if injury_status != "ACTIVE" else None,
        })

    return {
        "team_id": team_id,
        "wins": record.get("wins", 0),
        "losses": record.get("losses", 0),
        "points_for": record.get("pointsFor", 0.0),
        "players": players,
    }
