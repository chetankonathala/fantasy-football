"""Synthesize fantasy depth charts from FantasyCalc REDRAFT values × team rosters.

For each team and fantasy position, sort players by current-season redraft value
DESC and assign depth_order 1, 2, 3, ... Redraft values reflect 2026-only
production consensus (vs. dynasty which weights long-term career arc heavily),
so this gives the right answer for "who gets touches in the upcoming season."

Rookies that aren't in FantasyCalc yet (Sleeper/dynasty lag post-draft) are
appended at the end of their depth bucket so the chart is complete.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from collections import defaultdict
from datetime import datetime, timezone

from src.fantasy.db.base import IS_POSTGRES, get_session_factory

if IS_POSTGRES:
    from sqlalchemy.dialects.postgresql import insert
else:
    from sqlalchemy.dialects.sqlite import insert

from src.fantasy.db.models import DynastyValue, RookiePick, TeamDepthChart
from src.fantasy.fetch.fantasycalc import fetch_redraft_values, is_pick_entry
from src.fantasy.fetch.nfl_draft import normalize_player_name

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

FANTASY_POSITIONS = {"QB", "RB", "WR", "TE"}
SEASON = 2026


def refresh_depth_charts(season: int = SEASON) -> int:
    log.info("Fetching FantasyCalc redraft values for depth chart ordering...")
    redraft_entries = fetch_redraft_values(num_qbs=1, num_teams=12, ppr=1)

    # Index redraft entries by name (normalized) — also build per-team-pos buckets
    redraft_by_name: dict[str, dict] = {}
    redraft_by_team_pos: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for entry in redraft_entries:
        if is_pick_entry(entry):
            continue
        p = entry.get("player", {})
        team = p.get("maybeTeam")
        pos = p.get("position")
        name = (p.get("name") or "").strip()
        if not team or pos not in FANTASY_POSITIONS or not name:
            continue
        record = {
            "name": name,
            "sleeper_id": p.get("sleeperId"),
            "age": p.get("maybeAge"),
            "value": entry.get("value", 0),
            "position_rank": entry.get("positionRank"),
        }
        redraft_by_name[normalize_player_name(name)] = record
        redraft_by_team_pos[(team, pos)].append(record)

    # Sort each (team, pos) bucket by redraft value desc
    for key in redraft_by_team_pos:
        redraft_by_team_pos[key].sort(key=lambda r: r["value"], reverse=True)

    SessionLocal = get_session_factory()
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    count = 0

    try:
        # Lookup tables for dynasty values and rookies
        dynasty_lookup = {
            normalize_player_name(dv.player_name): dv
            for dv in db.query(DynastyValue).filter(
                DynastyValue.is_pick == False,  # noqa: E712
                DynastyValue.position.in_(FANTASY_POSITIONS),
            ).all()
        }
        rookies = db.query(RookiePick).all()
        rookie_lookup = {normalize_player_name(r.player_name): r for r in rookies}

        # Wipe existing season rows for clean rebuild
        db.query(TeamDepthChart).filter(TeamDepthChart.season == season).delete()
        db.commit()

        # ── Stage 1: Insert all redraft-ranked players ────────────
        seen_per_team_pos: dict[tuple[str, str], set[str]] = defaultdict(set)
        for (team, position), players in redraft_by_team_pos.items():
            for order, rd in enumerate(players, start=1):
                norm = normalize_player_name(rd["name"])
                seen_per_team_pos[(team, position)].add(norm)
                dv = dynasty_lookup.get(norm)
                row = {
                    "team": team,
                    "position": position,
                    "depth_order": order,
                    "player_name": rd["name"],
                    "sleeper_id": rd["sleeper_id"] or (dv.sleeper_id if dv else None),
                    "age": rd["age"] or (dv.age if dv else None),
                    "dynasty_value": dv.value if dv else None,
                    "dynasty_position_rank": dv.position_rank if dv else None,
                    "is_rookie": norm in rookie_lookup,
                    "season": season,
                    "updated_at": now,
                }
                db.execute(insert(TeamDepthChart).values(**row))
                count += 1

        # ── Stage 2: Append rookies missing from redraft data ────
        # (e.g. Fernando Mendoza — drafted but FantasyCalc hasn't ingested yet)
        for r in rookies:
            if not r.team or not r.position or r.position not in FANTASY_POSITIONS:
                continue
            norm = normalize_player_name(r.player_name)
            key = (r.team, r.position)
            if norm in seen_per_team_pos[key]:
                continue
            # Append to end of depth chart for this team/pos
            current_count = len(seen_per_team_pos[key])
            current_count += 1
            seen_per_team_pos[key].add(norm)
            row = {
                "team": r.team,
                "position": r.position,
                "depth_order": current_count,
                "player_name": r.player_name,
                "sleeper_id": r.sleeper_id,
                "age": r.age,
                "dynasty_value": r.dynasty_value,
                "dynasty_position_rank": r.dynasty_position_rank,
                "is_rookie": True,
                "season": season,
                "updated_at": now,
            }
            db.execute(insert(TeamDepthChart).values(**row))
            count += 1

        db.commit()
        log.info(f"Depth chart refresh complete: {count} entries across {len(redraft_by_team_pos)} (team,pos) buckets")

    except Exception:
        db.rollback()
        log.exception("Depth chart refresh failed")
        raise
    finally:
        db.close()

    return count


def get_depth_order(team: str, position: str, player_name: str, db, season: int = SEASON) -> int | None:
    """Helper — return depth_order for a player or None if absent."""
    row = (
        db.query(TeamDepthChart)
        .filter(
            TeamDepthChart.season == season,
            TeamDepthChart.team == team,
            TeamDepthChart.position == position,
            TeamDepthChart.player_name == player_name,
        )
        .first()
    )
    return row.depth_order if row else None


if __name__ == "__main__":
    n = refresh_depth_charts()
    print(f"Depth chart refresh complete: {n} entries")
