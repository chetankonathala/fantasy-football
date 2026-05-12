"""Seed historical_rookie_comp from nflverse — past rookies with year-1 PPR outcomes.

Pulls ff_playerids (player draft data) and player_stats (weekly stats) for seasons
2018-2025, identifies each player's rookie season, sums year-1 PPR points, then
classifies each as bust / depth / starter / breakout / elite based on rank within
position cohort.

These rows back the /offseason/comps/{rookie_id} endpoint which finds historical
players with similar draft profiles to current rookies.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from datetime import datetime, timezone

import polars as pl
import nflreadpy as nfl

from src.fantasy.db.base import IS_POSTGRES, get_session_factory

if IS_POSTGRES:
    from sqlalchemy.dialects.postgresql import insert
else:
    from sqlalchemy.dialects.sqlite import insert

from src.fantasy.db.models import HistoricalRookieComp

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

FANTASY_POSITIONS = {"QB", "RB", "WR", "TE"}
SEASONS_TO_SEED = list(range(2018, 2026))  # 2018-2025 inclusive


def _classify_rookie_year(position: str, ppr_points: float, position_rank: int) -> str:
    """Classify rookie year-1 outcome into a hit_label tier."""
    # Rank-based primary, points-based secondary
    if position == "QB":
        if ppr_points >= 280: return "elite"
        if ppr_points >= 200: return "breakout"
        if ppr_points >= 120: return "starter"
        if ppr_points >= 40:  return "depth"
        return "bust"
    if position == "RB":
        if ppr_points >= 280: return "elite"
        if ppr_points >= 200: return "breakout"
        if ppr_points >= 120: return "starter"
        if ppr_points >= 60:  return "depth"
        return "bust"
    if position in ("WR", "TE"):
        if ppr_points >= 240: return "elite"
        if ppr_points >= 170: return "breakout"
        if ppr_points >= 100: return "starter"
        if ppr_points >= 40:  return "depth"
        return "bust"
    return "depth"


def _compute_ppr(row: dict) -> float:
    """Compute PPR fantasy points from a weekly player_stats row."""
    p = row.get
    pts = 0.0
    pts += (p("passing_yards") or 0) * 0.04
    pts += (p("passing_tds") or 0) * 4.0
    pts -= (p("passing_interceptions") or 0) * 2.0
    pts += (p("rushing_yards") or 0) * 0.1
    pts += (p("rushing_tds") or 0) * 6.0
    pts += (p("receiving_yards") or 0) * 0.1
    pts += (p("receiving_tds") or 0) * 6.0
    pts += (p("receptions") or 0) * 1.0      # PPR
    # Fumble lost is across all play types
    pts -= (p("rushing_fumbles_lost") or 0) * 2.0
    pts -= (p("receiving_fumbles_lost") or 0) * 2.0
    pts -= (p("sack_fumbles_lost") or 0) * 2.0
    return pts


def refresh_historical_rookies(seasons: list[int] | None = None) -> int:
    seasons = seasons or SEASONS_TO_SEED
    log.info(f"Loading ff_playerids for draft metadata...")
    ids = nfl.load_ff_playerids()

    rookies_by_season: dict[int, list[dict]] = {}
    for s in seasons:
        rookies = ids.filter(
            (pl.col("draft_year") == s) & (pl.col("position").is_in(list(FANTASY_POSITIONS)))
        )
        rookies_by_season[s] = rookies.to_dicts()
        log.info(f"  {s}: {len(rookies_by_season[s])} drafted fantasy rookies (any round)")

    SessionLocal = get_session_factory()
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    total = 0

    try:
        # Wipe and reseed
        db.query(HistoricalRookieComp).delete()
        db.commit()

        for season in seasons:
            log.info(f"Loading {season} player_stats for year-1 outcomes...")
            try:
                stats = nfl.load_player_stats(seasons=[season])
            except Exception:
                log.warning(f"player_stats unavailable for {season} — skipping")
                continue

            stats = stats.filter(pl.col("season_type") == "REG")
            # Aggregate per player
            stats_dicts = stats.to_dicts()
            agg: dict[str, dict] = {}
            for row in stats_dicts:
                pid = row.get("player_id")
                if not pid:
                    continue
                bucket = agg.setdefault(pid, {
                    "player_id": pid,
                    "player_name": row.get("player_name") or row.get("player_display_name"),
                    "position": row.get("position"),
                    "team": row.get("team"),
                    "ppr": 0.0,
                    "games": 0,
                    "targets": 0.0,
                    "carries": 0.0,
                    "team_targets": 0.0,
                    "team_carries": 0.0,
                })
                bucket["ppr"] += _compute_ppr(row)
                bucket["games"] += 1
                bucket["targets"] += (row.get("targets") or 0)
                bucket["carries"] += (row.get("carries") or 0)

            # Match each rookie of this season
            rookies = rookies_by_season.get(season, [])
            position_buckets: dict[str, list[tuple[float, dict]]] = {p: [] for p in FANTASY_POSITIONS}

            for r in rookies:
                pid = r.get("gsis_id")
                if not pid:
                    continue
                pos = r.get("position")
                if pos not in FANTASY_POSITIONS:
                    continue
                row_stats = agg.get(pid, {"ppr": 0.0, "games": 0, "targets": 0.0, "carries": 0.0})
                rookie_row = {
                    "player_name": r.get("name") or r.get("merge_name"),
                    "season": season,
                    "position": pos,
                    "nfl_round": r.get("draft_round"),
                    "nfl_pick": r.get("draft_ovr") or r.get("draft_pick"),
                    "college": r.get("college"),
                    "nfl_team": r.get("team"),
                    "age_at_draft": r.get("age"),
                    "year1_ppr_points": round(row_stats["ppr"], 1),
                    "year1_games": row_stats["games"],
                    "year1_starts": None,  # not directly available
                    "year1_target_share": None,  # team totals not aggregated here
                    "year1_carry_share": None,
                }
                # Position rank within cohort (computed after we collect all)
                position_buckets[pos].append((row_stats["ppr"], rookie_row))

            # Rank within each position cohort
            for pos, entries in position_buckets.items():
                entries.sort(key=lambda e: e[0], reverse=True)
                for rank, (ppr, rookie_row) in enumerate(entries, start=1):
                    rookie_row["hit_label"] = _classify_rookie_year(pos, ppr, rank)
                    rookie_row["updated_at"] = now
                    if not rookie_row["player_name"]:
                        continue
                    stmt = (
                        insert(HistoricalRookieComp)
                        .values(**rookie_row)
                        .on_conflict_do_update(
                            index_elements=["player_name", "season"],
                            set_={k: v for k, v in rookie_row.items() if k not in ("player_name", "season")},
                        )
                    )
                    db.execute(stmt)
                    total += 1

            db.commit()
            log.info(f"  {season}: persisted {sum(len(v) for v in position_buckets.values())} rookies")

        log.info(f"Historical rookie comp seed complete: {total} rows across {len(seasons)} seasons")
    except Exception:
        db.rollback()
        log.exception("Historical rookie refresh failed")
        raise
    finally:
        db.close()

    return total


if __name__ == "__main__":
    n = refresh_historical_rookies()
    print(f"Historical rookie comps complete: {n} rows")
