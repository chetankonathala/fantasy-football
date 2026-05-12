"""Compute 3-year dynasty trajectory for every player with a current dynasty value.

Output: dynasty_projection table with one row per (player, projection_year ∈ {1,2,3}).
Each row stores projected_value, projected_age, decay_factor, and role_label
(ascending / peak / declining / cliff).

Re-run whenever refresh_dynasty.py refreshes current values.
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

from src.fantasy.db.models import DynastyProjection, DynastyValue
from src.fantasy.age_curves import age_multiplier, project_value, role_label

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

FANTASY_POSITIONS = {"QB", "RB", "WR", "TE"}
BASE_YEAR = 2026
PROJECTION_HORIZON = 3


def refresh_projections(base_year: int = BASE_YEAR, horizon: int = PROJECTION_HORIZON) -> int:
    SessionLocal = get_session_factory()
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    count = 0

    try:
        # Wipe existing projections for this base year
        db.query(DynastyProjection).filter(DynastyProjection.base_year == base_year).delete()
        db.commit()

        players = (
            db.query(DynastyValue)
            .filter(
                DynastyValue.is_pick == False,  # noqa: E712
                DynastyValue.position.in_(list(FANTASY_POSITIONS)),
                DynastyValue.value > 0,
                DynastyValue.age.isnot(None),
            )
            .all()
        )
        log.info(f"Projecting {horizon}-year arc for {len(players)} players...")

        for dv in players:
            for years_out in range(1, horizon + 1):
                cur_mult = age_multiplier(dv.position, dv.age)
                fut_age = dv.age + years_out
                fut_mult = age_multiplier(dv.position, fut_age)
                decay = (fut_mult / cur_mult) if cur_mult > 0 else 0.0
                projected = project_value(dv.value, dv.position, dv.age, years_out)
                label = role_label(dv.age, dv.position, years_out)

                row = {
                    "player_name": dv.player_name,
                    "sleeper_id": dv.sleeper_id,
                    "position": dv.position,
                    "base_year": base_year,
                    "projection_year": years_out,
                    "projected_value": projected,
                    "projected_age": fut_age,
                    "decay_factor": round(decay, 3),
                    "role_label": label,
                    "updated_at": now,
                }
                db.execute(insert(DynastyProjection).values(**row))
                count += 1

        db.commit()
        log.info(f"Wrote {count} projection rows ({len(players)} players × {horizon} years)")

    except Exception:
        db.rollback()
        log.exception("Projection refresh failed")
        raise
    finally:
        db.close()

    return count


if __name__ == "__main__":
    n = refresh_projections()
    print(f"Dynasty projections complete: {n} rows")
