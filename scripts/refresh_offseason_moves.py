"""Detect and record offseason moves by diffing Sleeper player data against the DB.

Logic:
  - Players whose `team` in Sleeper differs from `team` in the Player table → FA/trade
  - Players with years_exp=0 and a team assigned → draft pick (handled by refresh_rookies)
  - Players in the DB with a team whose Sleeper record now has team=None → cut/retired
  - Dynasty value pulled from dynasty_value table to classify fantasy impact tier

Run once after free agency + NFL Draft. Re-run as signings continue through training camp.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from datetime import datetime, timezone

from src.fantasy.db.base import IS_POSTGRES, get_session_factory

if IS_POSTGRES:
    from sqlalchemy.dialects.postgresql import insert
else:
    from sqlalchemy.dialects.sqlite import insert

from src.fantasy.db.models import DynastyValue, OffseasonMove, Player
from src.fantasy.fetch.sleeper import fetch_sleeper_players

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

MOVE_SEASON = 2026
FANTASY_POSITIONS = {"QB", "RB", "WR", "TE"}

# Dynasty value thresholds for impact classification
_HIGH_VALUE = 3000
_MED_VALUE = 1000


def _classify_impact(
    dynasty_value: int | None,
    move_type: str,
    position: str | None,
) -> tuple[str, str, str]:
    """Return (fantasy_impact, impact_direction, impact_note)."""
    val = dynasty_value or 0
    pos = position or "?"

    if move_type == "cut":
        if val >= _HIGH_VALUE:
            return "high", "down", f"{pos} cut — high dynasty value player loses role"
        if val >= _MED_VALUE:
            return "medium", "down", f"{pos} released — monitor for new signing"
        return "low", "neutral", f"{pos} cut — minimal fantasy impact"

    if move_type == "free_agent":
        if val >= _HIGH_VALUE:
            return "high", "up", f"High-value {pos} changes teams — new scheme/role"
        if val >= _MED_VALUE:
            return "medium", "up", f"{pos} signs with new team — opportunity TBD"
        return "low", "neutral", f"Depth {pos} signs elsewhere"

    if move_type == "trade":
        if val >= _HIGH_VALUE:
            return "high", "up", f"Elite {pos} traded — landing spot changes everything"
        if val >= _MED_VALUE:
            return "medium", "neutral", f"{pos} traded — role clarification needed"
        return "low", "neutral", f"Depth {pos} traded"

    return "low", "neutral", "Roster move"


def refresh_offseason_moves(season: int = MOVE_SEASON) -> int:
    log.info("Fetching all Sleeper players for offseason diff...")
    sleeper_players = fetch_sleeper_players()

    SessionLocal = get_session_factory()
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    count = 0

    try:
        # Build dynasty_value lookup by sleeper_id
        dv_rows = db.query(DynastyValue).filter(DynastyValue.sleeper_id.isnot(None)).all()
        dv_by_sleeper: dict[str, int] = {str(dv.sleeper_id): dv.value for dv in dv_rows}

        # Load current DB players (only fantasy positions with a known sleeper_id)
        db_players = (
            db.query(Player)
            .filter(Player.position.in_(FANTASY_POSITIONS), Player.sleeper_id.isnot(None))
            .all()
        )
        db_by_sleeper: dict[str, Player] = {str(p.sleeper_id): p for p in db_players}

        moves: list[dict] = []

        for sid, player in sleeper_players.items():
            position = player.get("position")
            if position not in FANTASY_POSITIONS:
                continue

            name = (player.get("full_name") or "").strip()
            if not name:
                continue

            # Skip rookies — handled by refresh_rookies
            if player.get("years_exp") == 0:
                continue

            sleeper_team = player.get("team") or None
            db_player = db_by_sleeper.get(sid)

            if db_player is None:
                continue

            db_team = db_player.team or None

            if sleeper_team == db_team:
                continue  # no move

            dynasty_val = dv_by_sleeper.get(sid)

            if sleeper_team is None and db_team is not None:
                move_type = "cut"
                from_team, to_team = db_team, None
            elif db_team is None and sleeper_team is not None:
                # Previously unknown team → signed somewhere (undrafted FA / late signing)
                move_type = "free_agent"
                from_team, to_team = None, sleeper_team
            else:
                move_type = "free_agent"
                from_team, to_team = db_team, sleeper_team

            impact, direction, note = _classify_impact(dynasty_val, move_type, position)

            # Add context to note
            if from_team and to_team:
                note = f"{from_team} → {to_team}: {note}"
            elif to_team:
                note = f"Signs with {to_team}: {note}"
            elif from_team:
                note = f"Released by {from_team}: {note}"

            moves.append({
                "sleeper_id": sid,
                "player_name": name,
                "position": position,
                "from_team": from_team,
                "to_team": to_team,
                "move_type": move_type,
                "fantasy_impact": impact,
                "impact_direction": direction,
                "impact_note": note,
                "dynasty_value": dynasty_val,
                "move_season": season,
                "updated_at": now,
            })

        log.info(f"Detected {len(moves)} offseason moves")

        for row in moves:
            stmt = (
                insert(OffseasonMove)
                .values(**row)
                .on_conflict_do_update(
                    index_elements=["sleeper_id", "move_season", "move_type"],
                    set_={k: v for k, v in row.items() if k not in ("sleeper_id", "move_season", "move_type")},
                )
            )
            db.execute(stmt)
            count += 1

        db.commit()
        log.info(f"Upserted {count} offseason move entries")
    except Exception:
        db.rollback()
        log.exception("Offseason moves refresh failed")
        raise
    finally:
        db.close()

    return count


if __name__ == "__main__":
    n = refresh_offseason_moves()
    print(f"Offseason moves refresh complete: {n} moves upserted")
