#!/usr/bin/env python3
"""Standalone data refresh script invoked by cron.

Orchestrates: fetch (Sleeper + nflreadpy) -> normalize -> upsert to SQLite.
Off-season guard returns early when NFL season is not active.
On failure: logs error, retains last good data, next cron run retries.

All file paths are absolute (computed from __file__) per Pitfall 6.
"""
import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

# Compute project root from script location (scripts/ is one level below root)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
# Add project root to sys.path so src.fantasy imports work
sys.path.insert(0, str(PROJECT_ROOT))

import nflreadpy as nfl
from sqlalchemy.orm import Session  # noqa: F401 (imported for type reference)

from src.fantasy.db.base import get_engine, get_session_factory
from src.fantasy.db.upsert import upsert_players, upsert_matchups, upsert_game_lines
from src.fantasy.fetch.sleeper import fetch_sleeper_players
from src.fantasy.fetch.odds import fetch_game_lines
from src.fantasy.fetch.weather import fetch_weather
from src.fantasy.fetch.nflverse import (
    load_ff_playerids,
    load_player_stats,
    load_snap_counts,
    load_pbp,
    compute_dvp,
)
from src.fantasy.normalize import normalize_players, normalize_matchups

LOG_PATH = PROJECT_ROOT / "logs" / "refresh.log"


def setup_logging():
    """Configure TimedRotatingFileHandler with 7-day retention.
    Also logs to stdout for cron capture.

    Directly sets handlers on the root logger so this is idempotent across
    repeated calls (logging.basicConfig is a no-op when handlers already exist).
    """
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")

    file_handler = TimedRotatingFileHandler(
        filename=str(LOG_PATH),
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(file_handler)
    root.addHandler(stdout_handler)


log = logging.getLogger("refresh")


def main() -> dict:
    """Run full data refresh pipeline.

    Returns:
        dict with keys:
        - season_active (bool): False if off-season early return
        - players_upserted (int): number of player rows upserted (0 if off-season)
        - matchups_upserted (int): number of matchup rows upserted (0 if off-season)
        - game_lines_upserted (int): number of game line rows upserted (0 if off-season or non-Wed-Sat)
    """
    setup_logging()

    # Off-season guard (DATA-03)
    week = nfl.get_current_week(use_date=True)
    if not (1 <= week <= 22):
        log.info("season_active=false week=%s — skipping refresh", week)
        return {"season_active": False, "players_upserted": 0, "matchups_upserted": 0, "game_lines_upserted": 0}

    season = nfl.get_current_season()
    log.info("Starting refresh season=%s week=%s", season, week)

    # Fetch phase — any failure here retains last good data
    try:
        sleeper_players = fetch_sleeper_players()
        stats_df = load_player_stats(season)
        snaps_df = load_snap_counts(season)
        crosswalk_df = load_ff_playerids()
        pbp_df = load_pbp(season)
    except Exception as exc:
        log.error("Fetch failed: %s — retaining last good data", exc)
        return {"season_active": True, "players_upserted": 0, "matchups_upserted": 0, "game_lines_upserted": 0}

    # Normalize phase
    player_dicts = normalize_players(sleeper_players, stats_df, snaps_df, crosswalk_df, week)
    dvp_results = compute_dvp(pbp_df, week, season)
    matchup_dicts = normalize_matchups(dvp_results)

    # Persist phase — upsert (never full wipe)
    engine = get_engine()
    SessionFactory = get_session_factory(engine)
    with SessionFactory() as session:
        players_count = upsert_players(session, player_dicts)
        matchups_count = upsert_matchups(session, matchup_dicts)

        # Game lines: Vegas odds + weather (ENRI-01, ENRI-02)
        try:
            game_line_dicts = fetch_game_lines(week)
            if game_line_dicts:
                game_line_dicts = fetch_weather(game_line_dicts)
                game_lines_count = upsert_game_lines(session, game_line_dicts)
            else:
                game_lines_count = 0
        except Exception as exc:
            log.error("Game lines fetch/persist failed: %s — continuing", exc)
            game_lines_count = 0

    log.info(
        "Refresh complete: %d players, %d matchups, %d game lines upserted",
        players_count, matchups_count, game_lines_count,
    )
    return {
        "season_active": True,
        "players_upserted": players_count,
        "matchups_upserted": matchups_count,
        "game_lines_upserted": game_lines_count,
    }


if __name__ == "__main__":
    result = main()
    log.info("Result: %s", result)
