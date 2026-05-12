"""ESPN public NFL Draft API client.

Pulls the full 257-pick 2026 NFL Draft (or any year) with player names, colleges,
positions, and NFL team landing spots. Exposes a normalized list ready to merge
into RookiePick.

Endpoint: https://site.api.espn.com/apis/site/v2/sports/football/nfl/draft?year=YYYY
No auth required. Returns ~50KB of JSON.
"""
from __future__ import annotations

import logging
from typing import Optional

import requests

log = logging.getLogger(__name__)

ESPN_DRAFT_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/draft"

# Fantasy-relevant positions only. ESPN uses string IDs.
FANTASY_POSITION_IDS = {
    "8":  "QB",
    "9":  "RB",
    "1":  "WR",
    "7":  "TE",
}

# All positions ESPN tracks — used for the broader draft board view.
ALL_POSITION_IDS = {
    "8":   "QB",  "9":   "RB",  "1":   "WR",  "7":   "TE",  "10":  "FB",
    "46":  "OT",  "47":  "OG",  "91":  "C",   "32":  "DT",  "30":  "LB",
    "264": "EDGE","29":  "CB",  "36":  "S",   "96":  "LS",  "80":  "PK",  "94": "P",
}


def fetch_nfl_draft(year: int = 2026) -> dict:
    """Fetch the raw ESPN draft response for a given year. Raises on HTTP error."""
    resp = requests.get(ESPN_DRAFT_URL, params={"year": year}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def build_team_lookup(draft_response: dict) -> dict[str, dict]:
    """Map ESPN teamId → {abbreviation, location, displayName} dict."""
    out = {}
    for t in draft_response.get("teams", []) or []:
        tid = str(t.get("id") or "")
        if tid:
            out[tid] = {
                "abbreviation": t.get("abbreviation"),
                "location": t.get("location"),
                "displayName": t.get("displayName"),
                "logo": t.get("logo"),
            }
    return out


def build_position_lookup(draft_response: dict) -> dict[str, str]:
    """Map ESPN position id → abbreviation, falling back to ALL_POSITION_IDS."""
    out = dict(ALL_POSITION_IDS)
    for p in draft_response.get("positions", []) or []:
        pid = str(p.get("id") or "")
        abbr = p.get("abbreviation")
        if pid and abbr:
            out[pid] = abbr
    return out


def normalize_picks(draft_response: dict, fantasy_only: bool = True) -> list[dict]:
    """Convert raw ESPN picks into a flat normalized list.

    Each pick dict contains:
      overall, round, pick_in_round, traded, trade_note,
      player_name, espn_athlete_id, position, college,
      nfl_team, nfl_team_id, nfl_team_logo, headshot_url
    """
    teams = build_team_lookup(draft_response)
    positions = build_position_lookup(draft_response)
    out: list[dict] = []

    for p in draft_response.get("picks", []) or []:
        athlete = p.get("athlete") or {}
        pos_id = str((athlete.get("position") or {}).get("id") or "")
        position_abbr = positions.get(pos_id)

        if fantasy_only and position_abbr not in {"QB", "RB", "WR", "TE"}:
            continue

        team_id = str(p.get("teamId") or "")
        team_info = teams.get(team_id, {})
        college = athlete.get("team") or {}

        out.append({
            "overall": p.get("overall"),
            "round": p.get("round"),
            "pick_in_round": p.get("pick"),
            "traded": p.get("traded", False),
            "trade_note": p.get("tradeNote") or "",
            "player_name": (athlete.get("displayName") or "").strip(),
            "espn_athlete_id": athlete.get("id"),
            "alt_athlete_id": athlete.get("alternativeId"),
            "position": position_abbr,
            "position_id": pos_id,
            "college": college.get("location") or college.get("shortDisplayName") or college.get("name"),
            "college_full": college.get("displayName") if isinstance(college, dict) else None,
            "nfl_team": team_info.get("abbreviation"),
            "nfl_team_id": team_id or None,
            "nfl_team_name": team_info.get("displayName"),
            "nfl_team_logo": team_info.get("logo"),
            "headshot_url": (athlete.get("headshot") or {}).get("href"),
            "espn_link": athlete.get("link"),
            "status": p.get("status"),
        })

    return out


def fetch_normalized_picks(year: int = 2026, fantasy_only: bool = True) -> list[dict]:
    """One-shot: fetch + normalize. Returns list of pick dicts."""
    raw = fetch_nfl_draft(year)
    return normalize_picks(raw, fantasy_only=fantasy_only)


def normalize_player_name(name: str) -> str:
    """Lowercase, strip, drop punctuation/Jr/Sr/III suffixes — for matching across sources."""
    import re
    s = (name or "").lower().strip()
    s = re.sub(r"[.,'`]", "", s)
    s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s
