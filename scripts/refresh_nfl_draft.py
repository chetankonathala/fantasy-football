"""Pull the full 2026 NFL Draft from ESPN and merge into nfl_draft_pick + rookie_pick.

Two-stage flow:
  1. Persist all 257 picks into NFLDraftPick (full board, every position).
  2. Backfill RookiePick rows with real round/pick/college/team for QB/RB/WR/TE
     picks that match by normalized name. Recompute opportunity_grade and
     year1_projection now that draft slot is known.
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

from src.fantasy.db.models import NFLDraftPick, RookiePick
from src.fantasy.fetch.nfl_draft import fetch_normalized_picks, normalize_player_name
from scripts.refresh_rookies import _opportunity_grade, _year1_projection

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

DRAFT_YEAR = 2026


def refresh_nfl_draft(year: int = DRAFT_YEAR) -> dict:
    """Returns dict with counts: {'draft_picks': N, 'rookies_updated': M}."""
    log.info(f"Fetching {year} NFL Draft from ESPN public API...")
    picks = fetch_normalized_picks(year=year, fantasy_only=False)
    log.info(f"Got {len(picks)} total picks from ESPN")

    SessionLocal = get_session_factory()
    db = SessionLocal()
    now = datetime.now(timezone.utc)

    draft_count = 0
    updated_count = 0

    try:
        # ── Stage 1: Persist all picks into NFLDraftPick ──────────
        for p in picks:
            row = {
                "draft_year": year,
                "overall": p["overall"],
                "round": p["round"],
                "pick_in_round": p["pick_in_round"],
                "player_name": p["player_name"],
                "position": p["position"],
                "college": p["college"],
                "college_full": p["college_full"],
                "nfl_team": p["nfl_team"],
                "nfl_team_id": p["nfl_team_id"],
                "nfl_team_name": p["nfl_team_name"],
                "nfl_team_logo": p["nfl_team_logo"],
                "espn_athlete_id": str(p["espn_athlete_id"]) if p.get("espn_athlete_id") else None,
                "traded": bool(p["traded"]),
                "trade_note": p.get("trade_note") or None,
                "headshot_url": p.get("headshot_url"),
                "updated_at": now,
            }
            stmt = (
                insert(NFLDraftPick)
                .values(**row)
                .on_conflict_do_update(
                    index_elements=["draft_year", "overall"],
                    set_={k: v for k, v in row.items() if k not in ("draft_year", "overall")},
                )
            )
            db.execute(stmt)
            draft_count += 1

        db.commit()
        log.info(f"Persisted {draft_count} draft picks into nfl_draft_pick")

        # ── Stage 2: Backfill RookiePick with real draft slots ────
        # Build a normalized-name lookup of fantasy picks
        fantasy_picks = {
            normalize_player_name(p["player_name"]): p
            for p in picks
            if p["position"] in {"QB", "RB", "WR", "TE"}
        }

        rookies = db.query(RookiePick).all()
        for rookie in rookies:
            key = normalize_player_name(rookie.player_name)
            match = fantasy_picks.get(key)
            if not match:
                continue

            rookie.nfl_round = match["round"]
            rookie.nfl_pick = match["overall"]
            if match["college"]:
                rookie.college = match["college"]
            if match["nfl_team"]:
                rookie.team = match["nfl_team"]

            # Recompute grade + projection now that draft slot is real
            grade, note = _opportunity_grade(
                rookie.position or match["position"],
                rookie.nfl_round,
                rookie.dynasty_overall_rank,
                rookie.dynasty_position_rank,
                rookie.nfl_pick,
            )
            proj = _year1_projection(
                rookie.position or match["position"],
                rookie.nfl_round,
                rookie.nfl_pick,
            )
            rookie.opportunity_grade = grade
            rookie.opportunity_note = note
            rookie.year1_projection = proj
            rookie.updated_at = now
            updated_count += 1

        # ── Stage 3: Insert any draft picks not yet in RookiePick ──
        existing_names = {normalize_player_name(r.player_name) for r in rookies}
        inserted = 0
        for key, p in fantasy_picks.items():
            if key in existing_names:
                continue
            grade, note = _opportunity_grade(p["position"], p["round"], None, None, p["overall"])
            proj = _year1_projection(p["position"], p["round"], p["overall"])
            row = {
                "sleeper_id": None,  # to be filled by next refresh_rookies run
                "player_name": p["player_name"],
                "position": p["position"],
                "team": p["nfl_team"],
                "college": p["college"],
                "nfl_round": p["round"],
                "nfl_pick": p["overall"],
                "age": None,
                "dynasty_value": None,
                "dynasty_overall_rank": None,
                "dynasty_position_rank": None,
                "opportunity_grade": grade,
                "opportunity_note": note,
                "year1_projection": proj,
                "updated_at": now,
            }
            stmt = (
                insert(RookiePick)
                .values(**row)
                .on_conflict_do_update(
                    index_elements=["player_name"],
                    set_={k: v for k, v in row.items() if k != "player_name"},
                )
            )
            db.execute(stmt)
            inserted += 1

        db.commit()
        log.info(f"Backfilled {updated_count} existing rookies with real draft slots; inserted {inserted} new")

    except Exception:
        db.rollback()
        log.exception("NFL Draft refresh failed")
        raise
    finally:
        db.close()

    return {"draft_picks": draft_count, "rookies_updated": updated_count, "rookies_inserted": inserted}


if __name__ == "__main__":
    result = refresh_nfl_draft()
    print(f"NFL Draft refresh complete: {result}")
