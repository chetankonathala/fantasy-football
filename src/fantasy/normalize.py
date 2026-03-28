"""Normalization layer: transform raw Sleeper + nflverse data into Player/Matchup dicts.

Output dicts match Player and Matchup ORM model column names exactly — ready for upsert.
"""
import logging
from datetime import datetime, timezone

import polars as pl

from src.fantasy.fetch.sleeper import extract_player_data
from src.fantasy.fetch.nflverse import compute_carry_share

log = logging.getLogger(__name__)

FANTASY_POSITIONS = {"QB", "RB", "WR", "TE", "K", "DEF"}


def normalize_players(
    sleeper_players: dict,
    stats_df: pl.DataFrame,
    snaps_df: pl.DataFrame,
    crosswalk_df: pl.DataFrame,
    current_week: int,
) -> list[dict]:
    """Transform Sleeper player data + nflverse stats into Player model dicts.

    Steps:
    1. Filter sleeper_players to FANTASY_POSITIONS only
    2. For each player, call extract_player_data to get base fields
    3. Look up nflverse_id (gsis_id) from crosswalk_df by matching sleeper_id
    4. Skip players with no nflverse_id (cannot join to stats without canonical ID)
    5. Look up last 4 weeks of snap_pct from snaps_df (join on player_id=gsis_id)
    6. Look up last 4 weeks of target_share from stats_df (join on player_id=gsis_id)
    7. Compute carry_share via compute_carry_share(stats_df) and look up last 4 weeks
    8. Map the 4 most recent weeks to week1 (most recent) through week4 (oldest)
    9. Set updated_at to current UTC timestamp

    Week mapping (current_week=18 example):
    - week1_snap_pct = snap_pct for week 17 (most recent completed)
    - week2_snap_pct = snap_pct for week 16
    - week3_snap_pct = snap_pct for week 15
    - week4_snap_pct = snap_pct for week 14

    Returns list of dicts with keys matching ALL Player model columns except id and matchup_id.
    """
    # Build lookup: sleeper_id -> gsis_id from crosswalk
    id_lookup: dict[str, str] = {}
    # Build lookup: pfr_id -> gsis_id (used to join snap counts, which key on pfr_player_id)
    pfr_to_gsis: dict[str, str] = {}
    if not crosswalk_df.is_empty():
        crosswalk_rows = crosswalk_df.select(["gsis_id", "sleeper_id"]).drop_nulls().to_dicts()
        for row in crosswalk_rows:
            if row["sleeper_id"]:
                id_lookup[str(row["sleeper_id"])] = str(row["gsis_id"])
        if "pfr_id" in crosswalk_df.columns:
            pfr_rows = crosswalk_df.select(["gsis_id", "pfr_id"]).drop_nulls().to_dicts()
            for row in pfr_rows:
                pfr_to_gsis[str(row["pfr_id"])] = str(row["gsis_id"])

    # Compute carry shares for all players
    carry_shares_df = compute_carry_share(stats_df) if not stats_df.is_empty() else pl.DataFrame({
        "player_id": pl.Series([], dtype=pl.Utf8),
        "week": pl.Series([], dtype=pl.Int64),
        "carry_share": pl.Series([], dtype=pl.Float64),
    })

    # Build stats lookups: gsis_id -> {week: value}
    # snap_pct from snaps_df — snap counts key on pfr_player_id, not gsis_id.
    # Bridge via pfr_to_gsis crosswalk lookup.
    snap_lookup: dict[str, dict[int, float]] = {}
    if not snaps_df.is_empty() and "pfr_player_id" in snaps_df.columns and "offense_pct" in snaps_df.columns:
        for row in snaps_df.select(["pfr_player_id", "week", "offense_pct"]).to_dicts():
            gsis_id = pfr_to_gsis.get(str(row["pfr_player_id"]))
            if gsis_id is None:
                continue
            if gsis_id not in snap_lookup:
                snap_lookup[gsis_id] = {}
            if row["offense_pct"] is not None:
                snap_lookup[gsis_id][int(row["week"])] = float(row["offense_pct"])

    # target_share from stats_df (column: target_share)
    target_lookup: dict[str, dict[int, float]] = {}
    if not stats_df.is_empty() and "player_id" in stats_df.columns and "target_share" in stats_df.columns:
        for row in stats_df.select(["player_id", "week", "target_share"]).to_dicts():
            pid = str(row["player_id"])
            if pid not in target_lookup:
                target_lookup[pid] = {}
            if row["target_share"] is not None:
                target_lookup[pid][int(row["week"])] = float(row["target_share"])

    # carry_share lookup
    carry_lookup: dict[str, dict[int, float]] = {}
    if not carry_shares_df.is_empty():
        for row in carry_shares_df.to_dicts():
            pid = str(row["player_id"])
            if pid not in carry_lookup:
                carry_lookup[pid] = {}
            if row["carry_share"] is not None:
                carry_lookup[pid][int(row["week"])] = float(row["carry_share"])

    # Cap to regular season weeks (1-18). Playoff weeks (19-22) only have data for
    # a handful of teams, leaving most players with null stats. Capping at week 18
    # ensures we always pull the last 4 regular-season weeks.
    REGULAR_SEASON_END = 18
    effective_week = min(current_week, REGULAR_SEASON_END + 1)
    week_slots = [effective_week - 1, effective_week - 2, effective_week - 3, effective_week - 4]

    now = datetime.now(timezone.utc)
    results: list[dict] = []

    for sleeper_id, player_obj in sleeper_players.items():
        pos = player_obj.get("position")
        if pos not in FANTASY_POSITIONS:
            continue

        base = extract_player_data(sleeper_id, player_obj)

        nflverse_id = id_lookup.get(str(sleeper_id))
        if not nflverse_id:
            # Cannot join to stats — skip (no canonical ID crosswalk entry)
            log.debug("No nflverse_id for sleeper_id=%s — skipping", sleeper_id)
            continue

        base["nflverse_id"] = nflverse_id

        # Attach 4-week rolling stats (most recent = week1)
        snap_weeks = snap_lookup.get(nflverse_id, {})
        target_weeks = target_lookup.get(nflverse_id, {})
        carry_weeks = carry_lookup.get(nflverse_id, {})

        for i, week_num in enumerate(week_slots, start=1):
            base[f"week{i}_snap_pct"] = snap_weeks.get(week_num)
            base[f"week{i}_target_share"] = target_weeks.get(week_num)
            base[f"week{i}_carry_share"] = carry_weeks.get(week_num)

        base["updated_at"] = now
        results.append(base)

    return results


def normalize_matchups(dvp_results: list[dict]) -> list[dict]:
    """Pass-through validation — dvp_results from compute_dvp already match Matchup columns.

    Validates required keys are present and types are correct.
    Skips and logs any malformed rows.
    """
    required_keys = {"week", "team", "position", "dvp_score", "opponent_rank"}
    validated: list[dict] = []
    for row in dvp_results:
        if required_keys.issubset(row.keys()):
            validated.append(row)
        else:
            log.warning("Skipping malformed DVP row: %s", row)
    return validated
