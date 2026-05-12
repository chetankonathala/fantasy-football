"""Refresh 2026 rookie class: FantasyCalc (source of truth) × Sleeper (enrichment).

FantasyCalc updates dynasty values within 1-2 days of the NFL Draft. Sleeper's
draft_year field lags by several days. So FantasyCalc drives the rookie list
(players age ≤ 23 who are not draft picks), and Sleeper enriches with team,
college, and draft slot once that data populates.

Computes opportunity_grade (A-D) and year1_projection (PPR season total) for each rookie.
Run once after the NFL Draft and re-run as Sleeper populates draft_round/draft_number.
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

from src.fantasy.db.models import RookiePick
from src.fantasy.fetch.sleeper import fetch_sleeper_players
from src.fantasy.fetch.fantasycalc import fetch_dynasty_values, is_pick_entry

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

ROOKIE_MAX_AGE = 23.5   # true first-year players are college graduates, typically 21-23
FANTASY_POSITIONS = {"QB", "RB", "WR", "TE"}

# ── Year-1 PPR projections by position + draft capital ──────────────────────
# Based on historical rookie averages. Conservative — upside varies by landing spot.
_Y1_PROJ: dict[str, list[float]] = {
    # [round1_top10, round1_11plus, round2, round3plus_or_unknown]
    "QB":  [220.0, 160.0,  80.0,  40.0],
    "RB":  [180.0, 140.0, 100.0,  60.0],
    "WR":  [160.0, 120.0,  90.0,  55.0],
    "TE":  [100.0,  75.0,  55.0,  35.0],
}


def _year1_projection(position: str, nfl_round: int | None, nfl_pick: int | None) -> float | None:
    table = _Y1_PROJ.get(position)
    if table is None:
        return None
    if nfl_round is None:
        return table[3]
    if nfl_round == 1 and (nfl_pick or 99) <= 10:
        return table[0]
    if nfl_round == 1:
        return table[1]
    if nfl_round == 2:
        return table[2]
    return table[3]


def _opportunity_grade(
    position: str,
    nfl_round: int | None,
    dynasty_overall_rank: int | None,
    dynasty_position_rank: int | None,
    nfl_pick: int | None = None,
) -> tuple[str, str]:
    """Return (grade, note) blending NFL Draft capital with FantasyCalc consensus.

    NFL draft slot is the primary signal — even without FantasyCalc data, a top-10
    pick rates Grade A. FantasyCalc rank refines the narrative when available.
    """
    r = nfl_round or 99
    pk = nfl_pick or 999
    drank = dynasty_overall_rank or 999
    prank = dynasty_position_rank or 999
    has_fc = dynasty_overall_rank is not None

    # Top-10 overall: always Grade A
    if pk <= 10:
        if has_fc:
            return "A", f"Top-10 NFL pick #{pk} · dynasty #{drank} — premium draft + market capital"
        return "A", f"Top-10 NFL pick #{pk} — premium draft capital, market value pending"

    # R1 picks 11-32
    if r == 1:
        if drank <= 50:
            return "A", f"Round 1 (#{pk}) · dynasty #{drank} overall — strong starter projection"
        if has_fc:
            return "B", f"Round 1 (#{pk}) · dynasty #{drank} — starter role with role-clarity risk"
        return "B", f"Round 1 (#{pk}) — starter projection, market value pending"

    # R2
    if r == 2:
        if drank <= 75:
            return "B", f"Round 2 (#{pk}) · dynasty #{drank} — Day 2 capital + market endorsement"
        if has_fc:
            return "C", f"Round 2 (#{pk}) · dynasty #{drank} — role depth with breakout upside"
        return "C", f"Round 2 (#{pk}) — Day 2 pick, role TBD pending dynasty consensus"

    # R3
    if r == 3:
        if drank <= 150:
            return "C", f"Round 3 (#{pk}) · dynasty #{drank} — rotational role, contingent upside"
        return "C", f"Round 3 (#{pk}) — depth role"

    # R4+: Late capital. FantasyCalc love can lift to C.
    if drank <= 150:
        return "C", f"Round {r} (#{pk}) · dynasty #{drank} — late-round value the market believes in"
    if drank <= 250:
        return "D", f"Round {r} (#{pk}) · dynasty #{drank} — deep dynasty depth"
    return "D", f"Round {r} (#{pk}) — minimal year-1 fantasy relevance"


def refresh_rookies(rookie_max_age: float = ROOKIE_MAX_AGE) -> int:
    """Use FantasyCalc as source of truth for rookie class; enrich with Sleeper."""
    log.info("Fetching dynasty values from FantasyCalc (rookie source of truth)...")
    fc_entries = fetch_dynasty_values(is_dynasty=True, num_qbs=1, num_teams=12, ppr=1)

    # Filter to fantasy-relevant non-pick players under rookie age threshold
    rookie_entries = [
        e for e in fc_entries
        if not is_pick_entry(e)
        and (e.get("player", {}).get("position") in FANTASY_POSITIONS)
        and ((e.get("player", {}).get("maybeAge") or 99) <= rookie_max_age)
    ]
    log.info(f"FantasyCalc: {len(rookie_entries)} players age≤{rookie_max_age} across fantasy positions")

    log.info("Fetching Sleeper player data for enrichment (team, college, draft slot)...")
    sleeper_players = fetch_sleeper_players()
    # Build Sleeper lookups by sleeper_id and by name
    sleeper_by_id: dict[str, dict] = {}
    sleeper_by_name: dict[str, dict] = {}
    for pid, p in sleeper_players.items():
        if p.get("position") not in FANTASY_POSITIONS:
            continue
        sleeper_by_id[pid] = p
        name = (p.get("full_name") or "").strip().lower()
        if name:
            sleeper_by_name[name] = p

    SessionLocal = get_session_factory()
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    count = 0

    try:
        for entry in rookie_entries:
            fc_player = entry.get("player", {})
            name = (fc_player.get("name") or "").strip()
            if not name:
                continue

            position = fc_player.get("position") or ""
            fc_sleeper_id = str(fc_player.get("sleeperId") or "")
            age = fc_player.get("maybeAge")
            fc_team = fc_player.get("maybeTeam")

            # FantasyCalc values
            dynasty_value = entry.get("value")
            dynasty_overall_rank = entry.get("overallRank")
            dynasty_position_rank = entry.get("positionRank")

            # Enrich from Sleeper — prefer sleeperId match, fall back to name
            sl = sleeper_by_id.get(fc_sleeper_id) or sleeper_by_name.get(name.lower())
            nfl_round = (sl or {}).get("draft_round")
            nfl_pick = (sl or {}).get("draft_number")
            college = (sl or {}).get("college")
            team = (sl or {}).get("team") or fc_team  # Sleeper team is more current
            sleeper_id = fc_sleeper_id or None

            grade, note = _opportunity_grade(position, nfl_round, dynasty_overall_rank, dynasty_position_rank, nfl_pick)
            proj = _year1_projection(position, nfl_round, nfl_pick)

            row = {
                "sleeper_id": sleeper_id or None,
                "player_name": name,
                "position": position or None,
                "team": team or None,
                "college": college or None,
                "nfl_round": nfl_round,
                "nfl_pick": nfl_pick,
                "age": age,
                "dynasty_value": dynasty_value,
                "dynasty_overall_rank": dynasty_overall_rank,
                "dynasty_position_rank": dynasty_position_rank,
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
            count += 1

        db.commit()
        log.info(f"Upserted {count} rookie entries")
    except Exception:
        db.rollback()
        log.exception("Rookie refresh failed")
        raise
    finally:
        db.close()

    return count


if __name__ == "__main__":
    n = refresh_rookies()
    print(f"Rookie refresh complete: {n} rookies upserted")
