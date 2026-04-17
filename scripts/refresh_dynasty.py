"""Refresh dynasty trade values from FantasyCalc into the dynasty_value table."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone

from sqlalchemy.dialects.sqlite import insert

from src.fantasy.db.base import get_session_factory
from src.fantasy.db.models import DynastyValue
from src.fantasy.fetch.fantasycalc import fetch_dynasty_values, is_pick_entry
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def refresh_dynasty(num_qbs: int = 1, num_teams: int = 12, ppr: int = 1) -> int:
    """Fetch FantasyCalc values and upsert into dynasty_value. Returns count upserted."""
    log.info("Fetching dynasty values from FantasyCalc...")
    entries = fetch_dynasty_values(is_dynasty=True, num_qbs=num_qbs, num_teams=num_teams, ppr=ppr)
    log.info(f"Fetched {len(entries)} entries from FantasyCalc")

    SessionLocal = get_session_factory()
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    count = 0

    try:
        for entry in entries:
            player = entry.get("player", {})
            name = player.get("name", "").strip()
            if not name:
                continue

            is_pick = is_pick_entry(entry)
            position = "PICK" if is_pick else (player.get("position") or None)

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

        db.commit()
        log.info(f"Upserted {count} dynasty value entries")
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
