"""Compute projected 2026 Strength of Schedule by team and position.

Approach:
  1. Load 2025 NFL schedule (each team's actual 2025 opponents — 17 games)
  2. Load 2025 PBP and compute season-aggregate DVP per defense × position
     (fantasy points allowed per game)
  3. For each team T and position P, average T's 2025 opponents' DVP scores at P
  4. Convert to a 0-100 SOS score (50 = league average, higher = easier schedule)
  5. Rank 1-32 within each position (1 = easiest, 32 = hardest)

Why use 2025 schedule as the proxy: the official 2026 schedule isn't released
until mid-May. But ~50% of 2026 opponents are divisional (identical to 2025),
and the rotation games come from a deterministic 4-year cycle that tracks
similar-strength conference matchups. The 2025 opponent profile is the best
available proxy until the 2026 schedule is published.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from collections import defaultdict
from datetime import datetime, timezone

import polars as pl
import nflreadpy as nfl

from src.fantasy.db.base import IS_POSTGRES, get_session_factory

if IS_POSTGRES:
    from sqlalchemy.dialects.postgresql import insert
else:
    from sqlalchemy.dialects.sqlite import insert

from src.fantasy.db.models import ScheduleStrength

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

PRIOR_SEASON = 2025
PROJECTION_SEASON = 2026
FANTASY_POSITIONS = ["QB", "RB", "WR", "TE"]


def compute_season_dvp(prior_season: int = PRIOR_SEASON) -> dict[tuple[str, str], float]:
    """Compute season-total fantasy points allowed by each defense at each position.

    Returns dict keyed by (defense_team, position) with the per-game points-allowed value.
    Uses standard scoring (PPR for receivers).
    """
    log.info(f"Loading {prior_season} PBP for SOS DVP computation...")
    pbp = nfl.load_pbp(seasons=[prior_season])
    log.info(f"PBP rows: {len(pbp)}")

    pbp = pbp.filter(pl.col("week") <= 18)  # regular season only

    out: dict[tuple[str, str], float] = {}

    # ── QB: passing fantasy points allowed per defense ────────────
    pass_plays = pbp.filter(pl.col("passer_player_id").is_not_null())
    if not pass_plays.is_empty():
        qb = (
            pass_plays
            .group_by("defteam")
            .agg([
                (
                    pl.col("passing_yards").fill_null(0) * 0.04
                    + pl.col("pass_touchdown").fill_null(0) * 4.0
                    - pl.col("interception").fill_null(0) * 2.0
                ).sum().alias("pts"),
                pl.col("week").n_unique().alias("games"),
            ])
            .with_columns((pl.col("pts") / pl.col("games")).alias("pts_per_game"))
        )
        for row in qb.to_dicts():
            out[(row["defteam"], "QB")] = float(row["pts_per_game"])

    # ── RB: rushing fantasy points allowed ────────────────────────
    rush_plays = pbp.filter(
        pl.col("rusher_player_id").is_not_null() & pl.col("passer_player_id").is_null()
    )
    if not rush_plays.is_empty():
        rb = (
            rush_plays
            .group_by("defteam")
            .agg([
                (
                    pl.col("rushing_yards").fill_null(0) * 0.1
                    + pl.col("rush_touchdown").fill_null(0) * 6.0
                    - pl.col("fumble_lost").fill_null(0) * 2.0
                ).sum().alias("pts"),
                pl.col("week").n_unique().alias("games"),
            ])
            .with_columns((pl.col("pts") / pl.col("games")).alias("pts_per_game"))
        )
        for row in rb.to_dicts():
            out[(row["defteam"], "RB")] = float(row["pts_per_game"])

    # ── WR/TE: receiving fantasy points allowed (PPR) ─────────────
    # Without explicit position labels in PBP, treat all receiving plays as the
    # "receiver" pool. This produces a single defense-vs-receivers metric — we
    # mirror it for both WR and TE since target distribution is similar by team.
    rec_plays = pbp.filter(pl.col("receiver_player_id").is_not_null())
    if not rec_plays.is_empty():
        rec = (
            rec_plays
            .group_by("defteam")
            .agg([
                (
                    pl.col("receiving_yards").fill_null(0) * 0.1
                    + pl.col("pass_touchdown").fill_null(0) * 6.0
                    + pl.lit(1.0)  # 1 pt per reception (PPR)
                ).sum().alias("pts"),
                pl.col("week").n_unique().alias("games"),
            ])
            .with_columns((pl.col("pts") / pl.col("games")).alias("pts_per_game"))
        )
        for row in rec.to_dicts():
            out[(row["defteam"], "WR")] = float(row["pts_per_game"])
            out[(row["defteam"], "TE")] = float(row["pts_per_game"])

    log.info(f"Season DVP computed for {len(out)} (team,pos) buckets")
    return out


def compute_team_opponents(prior_season: int = PRIOR_SEASON) -> dict[str, list[str]]:
    """Return {team: [opp1, opp2, ...]} for the 17 regular-season games."""
    log.info(f"Loading {prior_season} schedule...")
    sched = nfl.load_schedules(seasons=[prior_season]).filter(pl.col("week") <= 18)

    opponents: dict[str, list[str]] = defaultdict(list)
    for row in sched.to_dicts():
        h, a = row.get("home_team"), row.get("away_team")
        if h and a:
            opponents[h].append(a)
            opponents[a].append(h)

    log.info(f"Opponents for {len(opponents)} teams")
    return dict(opponents)


def refresh_sos(prior_season: int = PRIOR_SEASON, projection_season: int = PROJECTION_SEASON) -> int:
    season_dvp = compute_season_dvp(prior_season)
    opponents = compute_team_opponents(prior_season)

    SessionLocal = get_session_factory()
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    count = 0

    try:
        # Wipe prior SOS for clean rebuild
        db.query(ScheduleStrength).filter(ScheduleStrength.season == projection_season).delete()
        db.commit()

        # Compute average opp DVP per (team, position)
        team_pos_avg: dict[tuple[str, str], tuple[float, int]] = {}
        for team, opps in opponents.items():
            for pos in FANTASY_POSITIONS:
                opp_dvps = [season_dvp.get((opp, pos)) for opp in opps]
                opp_dvps = [v for v in opp_dvps if v is not None]
                if not opp_dvps:
                    continue
                avg = sum(opp_dvps) / len(opp_dvps)
                team_pos_avg[(team, pos)] = (avg, len(opp_dvps))

        # Per-position rank + 0-100 score conversion
        for pos in FANTASY_POSITIONS:
            entries = [(team, avg, n) for (t, p), (avg, n) in team_pos_avg.items() if p == pos for team in [t]]
            if not entries:
                continue
            # Higher avg pts allowed by opponents = easier schedule = higher SOS score
            entries.sort(key=lambda e: e[1], reverse=True)  # easiest first
            avgs = [e[1] for e in entries]
            mean_avg = sum(avgs) / len(avgs)
            std_avg = (sum((a - mean_avg) ** 2 for a in avgs) / len(avgs)) ** 0.5 or 1.0

            for rank, (team, avg, n) in enumerate(entries, start=1):
                # z-score → 0-100 with 50 = league avg
                z = (avg - mean_avg) / std_avg
                sos_score = max(0.0, min(100.0, 50.0 + z * 15))
                row = {
                    "season": projection_season,
                    "team": team,
                    "position": pos,
                    "sos_score": sos_score,
                    "sos_rank": rank,
                    "avg_opp_dvp_rank": avg,  # actually pts/game (kept for transparency)
                    "games_played": n,
                    "updated_at": now,
                }
                db.execute(insert(ScheduleStrength).values(**row))
                count += 1

        db.commit()
        log.info(f"SOS refresh complete: {count} (team,pos) entries")

    except Exception:
        db.rollback()
        log.exception("SOS refresh failed")
        raise
    finally:
        db.close()

    return count


def sos_multiplier(sos_score: float | None) -> float:
    """Convert SOS score (0-100) to a year-1 projection multiplier (0.85-1.15)."""
    if sos_score is None:
        return 1.0
    # 50 → 1.0, 80 → 1.09, 20 → 0.91
    return 1.0 + (sos_score - 50.0) / 333.0


if __name__ == "__main__":
    n = refresh_sos()
    print(f"SOS refresh complete: {n} entries")
