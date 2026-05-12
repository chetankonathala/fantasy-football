"""Refresh dynasty + redraft FantasyCalc values into the dynasty_value table.

Two FantasyCalc fetches:
  - Dynasty (long-term career-arc weighted) → value/overall_rank/position_rank
  - Redraft (current-season-only) → redraft_value/redraft_overall_rank/redraft_position_rank
The redraft fields enable VBD computation and depth chart ordering for year-1 fantasy.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone

from src.fantasy.db.base import IS_POSTGRES
if IS_POSTGRES:
    from sqlalchemy.dialects.postgresql import insert
else:
    from sqlalchemy.dialects.sqlite import insert

from src.fantasy.db.base import get_session_factory
from src.fantasy.db.models import DynastyValue
from src.fantasy.fetch.fantasycalc import fetch_dynasty_values, fetch_redraft_values, is_pick_entry
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def refresh_dynasty(num_qbs: int = 1, num_teams: int = 12, ppr: int = 1) -> int:
    """Fetch dynasty + redraft FantasyCalc values and upsert into dynasty_value.

    Both views share player_name as the upsert key. Players present only in dynasty
    (e.g. deep prospects) get NULL redraft fields; players only in redraft get
    NULL dynasty fields. Returns total rows upserted.
    """
    log.info("Fetching dynasty values from FantasyCalc...")
    dyn_entries = fetch_dynasty_values(is_dynasty=True, num_qbs=num_qbs, num_teams=num_teams, ppr=ppr)
    log.info(f"Fetched {len(dyn_entries)} dynasty entries")

    log.info("Fetching redraft values from FantasyCalc...")
    redraft_entries = fetch_redraft_values(num_qbs=num_qbs, num_teams=num_teams, ppr=ppr)
    log.info(f"Fetched {len(redraft_entries)} redraft entries")

    # Index redraft entries by name for join
    redraft_by_name: dict[str, dict] = {}
    for e in redraft_entries:
        if is_pick_entry(e):
            continue
        name = (e.get("player", {}).get("name") or "").strip()
        if name:
            redraft_by_name[name] = e

    SessionLocal = get_session_factory()
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    count = 0

    try:
        # Build the set of names already covered by dynasty pass
        dynasty_names: set[str] = set()

        for entry in dyn_entries:
            player = entry.get("player", {})
            name = player.get("name", "").strip()
            if not name:
                continue
            dynasty_names.add(name)
            is_pick = is_pick_entry(entry)
            position = "PICK" if is_pick else (player.get("position") or None)

            redraft = redraft_by_name.get(name)
            redraft_value = redraft.get("value") if redraft else None
            redraft_overall = redraft.get("overallRank") if redraft else None
            redraft_pos_rank = redraft.get("positionRank") if redraft else None

            row = {
                "fantasycalc_id": player.get("id"),
                "sleeper_id": player.get("sleeperId") or None,
                "player_name": name,
                "position": position,
                "team": player.get("maybeTeam") or None,
                "age": player.get("maybeAge") or None,
                "value": entry.get("value", 0),
                "overall_rank": entry.get("overallRank"),
                "position_rank": entry.get("positionRank"),
                "trend_30day": entry.get("trend30Day"),
                "redraft_value": redraft_value,
                "redraft_overall_rank": redraft_overall,
                "redraft_position_rank": redraft_pos_rank,
                "is_pick": is_pick,
                "updated_at": now,
            }
            stmt = (
                insert(DynastyValue)
                .values(**row)
                .on_conflict_do_update(
                    index_elements=["player_name"],
                    set_={k: v for k, v in row.items() if k != "player_name"},
                )
            )
            db.execute(stmt)
            count += 1

        # Insert redraft-only players (rare — mostly aging vets w/ year-1 value but no dynasty)
        for name, entry in redraft_by_name.items():
            if name in dynasty_names:
                continue
            player = entry.get("player", {})
            row = {
                "fantasycalc_id": player.get("id"),
                "sleeper_id": player.get("sleeperId") or None,
                "player_name": name,
                "position": player.get("position") or None,
                "team": player.get("maybeTeam") or None,
                "age": player.get("maybeAge") or None,
                "value": 0,                       # no dynasty value
                "overall_rank": None,
                "position_rank": None,
                "trend_30day": None,
                "redraft_value": entry.get("value"),
                "redraft_overall_rank": entry.get("overallRank"),
                "redraft_position_rank": entry.get("positionRank"),
                "is_pick": False,
                "updated_at": now,
            }
            stmt = (
                insert(DynastyValue)
                .values(**row)
                .on_conflict_do_update(
                    index_elements=["player_name"],
                    set_={k: v for k, v in row.items() if k != "player_name"},
                )
            )
            db.execute(stmt)
            count += 1

        db.commit()
        log.info(f"Upserted {count} entries (dynasty + redraft merged)")
    except Exception:
        db.rollback()
        log.exception("Dynasty refresh failed")
        raise
    finally:
        db.close()

    return count


if __name__ == "__main__":
    n = refresh_dynasty()
    print(f"Dynasty refresh complete: {n} entries upserted")
