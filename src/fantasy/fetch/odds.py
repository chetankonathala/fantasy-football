"""The Odds API client — fetches NFL game lines and computes implied team totals."""
import logging
import os
from datetime import datetime, timezone

import requests

log = logging.getLogger(__name__)

ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds/"


def fetch_game_lines(week: int) -> list[dict]:
    """Fetch NFL game lines from The Odds API.

    Only call Wed-Sat (weekday 2-5). Returns list of game_line dicts
    ready for upsert_game_lines.

    Quota note: each call uses ~2 quota units (totals + spreads markets).
    """
    api_key = os.environ.get("ODDS_API_KEY", "")
    if not api_key:
        log.warning("ODDS_API_KEY not set — skipping odds fetch")
        return []

    # Day-of-week guard: only fetch Wed(2) through Sat(5)
    if datetime.now(timezone.utc).weekday() not in (2, 3, 4, 5):
        log.info("Skipping odds fetch — not Wed-Sat")
        return []

    try:
        resp = requests.get(
            ODDS_API_URL,
            params={
                "apiKey": api_key,
                "regions": "us",
                "markets": "totals,spreads",
                "oddsFormat": "american",
            },
            timeout=15,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        log.error("Odds API request failed: %s", exc)
        return []

    events = resp.json()
    if not isinstance(events, list):
        log.error("Unexpected Odds API response format")
        return []

    results = []
    for event in events:
        home_team = _normalize_team(event.get("home_team", ""))
        away_team = _normalize_team(event.get("away_team", ""))
        if not home_team or not away_team:
            continue

        game_date = event.get("commence_time", "")[:10]  # "YYYY-MM-DD"

        # Extract totals and spreads from first bookmaker
        bookmakers = event.get("bookmakers", [])
        if not bookmakers:
            continue

        game_total = None
        home_spread = None

        for market in bookmakers[0].get("markets", []):
            if market["key"] == "totals":
                for outcome in market.get("outcomes", []):
                    if outcome["name"] == "Over":
                        game_total = outcome.get("point")
                        break
            elif market["key"] == "spreads":
                for outcome in market.get("outcomes", []):
                    if _normalize_team(outcome.get("name", "")) == home_team:
                        home_spread = outcome.get("point")
                        break

        if game_total is None or home_spread is None:
            continue

        home_implied = (game_total / 2) - (home_spread / 2)
        away_implied = (game_total / 2) + (home_spread / 2)

        results.append({
            "week": week,
            "home_team": home_team,
            "away_team": away_team,
            "game_total": game_total,
            "home_spread": home_spread,
            "home_implied_total": round(home_implied, 1),
            "away_implied_total": round(away_implied, 1),
            "game_date": game_date,
            "updated_at": datetime.now(timezone.utc),
        })

    log.info("Fetched %d game lines from Odds API", len(results))
    return results


# Team name mapping from Odds API full names to abbreviations
_TEAM_MAP = {
    "Arizona Cardinals": "ARI", "Atlanta Falcons": "ATL", "Baltimore Ravens": "BAL",
    "Buffalo Bills": "BUF", "Carolina Panthers": "CAR", "Chicago Bears": "CHI",
    "Cincinnati Bengals": "CIN", "Cleveland Browns": "CLE", "Dallas Cowboys": "DAL",
    "Denver Broncos": "DEN", "Detroit Lions": "DET", "Green Bay Packers": "GB",
    "Houston Texans": "HOU", "Indianapolis Colts": "IND", "Jacksonville Jaguars": "JAX",
    "Kansas City Chiefs": "KC", "Las Vegas Raiders": "LV", "Los Angeles Chargers": "LAC",
    "Los Angeles Rams": "LAR", "Miami Dolphins": "MIA", "Minnesota Vikings": "MIN",
    "New England Patriots": "NE", "New Orleans Saints": "NO", "New York Giants": "NYG",
    "New York Jets": "NYJ", "Philadelphia Eagles": "PHI", "Pittsburgh Steelers": "PIT",
    "San Francisco 49ers": "SF", "Seattle Seahawks": "SEA", "Tampa Bay Buccaneers": "TB",
    "Tennessee Titans": "TEN", "Washington Commanders": "WAS",
}


def _normalize_team(name: str) -> str:
    """Convert full team name (from Odds API) to 2-3 letter abbreviation."""
    return _TEAM_MAP.get(name, name if len(name) <= 5 else "")
