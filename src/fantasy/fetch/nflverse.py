"""nflreadpy wrappers — stats, snap counts, PBP, crosswalk, DVP, schema validation."""
import logging

import polars as pl
import nflreadpy as nfl

log = logging.getLogger(__name__)

REQUIRED_PBP_COLUMNS = [
    "season",
    "week",
    "defteam",
    "posteam",
    "passing_yards",
    "rushing_yards",
    "receiving_yards",
    "pass_touchdown",
    "rush_touchdown",
    "interception",
    "fumble_lost",
    "receiver_player_id",
    "rusher_player_id",
    "passer_player_id",
]


def validate_pbp_schema(pbp_df: pl.DataFrame) -> tuple[bool, list[str]]:
    """Check that required PBP columns exist.

    Returns (valid, missing_columns).
    MUST be called before compute_dvp. If valid=False, DVP cannot be computed safely.
    """
    existing = set(pbp_df.columns)
    missing = [c for c in REQUIRED_PBP_COLUMNS if c not in existing]
    if missing:
        log.error("PBP schema validation failed. Missing columns: %s", missing)
    return (len(missing) == 0, missing)


def load_ff_playerids() -> pl.DataFrame:
    """Load the nflverse player ID crosswalk.

    Key columns: gsis_id (nflverse canonical), sleeper_id.
    """
    return nfl.load_ff_playerids()


def load_player_stats(season: int) -> pl.DataFrame:
    """Load weekly player stats for a season. Returns Polars DataFrame.

    Key columns: player_id (gsis_id), recent_team, week, targets, receptions,
    target_share, carries, passing_yards, rushing_yards, receiving_yards.
    Note: carry_share is NOT pre-computed — use compute_carry_share().
    """
    return nfl.load_player_stats(seasons=[season])


def load_snap_counts(season: int) -> pl.DataFrame:
    """Load snap count data. Key column: offense_pct (snap %)."""
    return nfl.load_snap_counts(seasons=[season])


def load_pbp(season: int) -> pl.DataFrame:
    """Load play-by-play data for DVP computation."""
    return nfl.load_pbp(seasons=[season])


def compute_carry_share(stats_df: pl.DataFrame) -> pl.DataFrame:
    """Derive carry_share = player_carries / team_total_carries per week.

    carry_share is NOT pre-computed in nflreadpy (Pitfall 2).
    Returns DataFrame with columns: player_id, week, carry_share.
    """
    # Get team total carries per (team, week)
    team_carries = (
        stats_df
        .filter(pl.col("carries") > 0)
        .group_by(["recent_team", "week"])
        .agg(pl.col("carries").sum().alias("team_carries"))
    )
    # Join back to individual player carries and compute share
    result = (
        stats_df
        .join(team_carries, on=["recent_team", "week"], how="left")
        .with_columns(
            pl.when(pl.col("team_carries").is_not_null() & (pl.col("team_carries") > 0))
            .then(pl.col("carries") / pl.col("team_carries"))
            .otherwise(0.0)
            .alias("carry_share")
        )
        .select(["player_id", "week", "carry_share"])
    )
    return result


def compute_dvp(pbp_df: pl.DataFrame, current_week: int, season: int) -> list[dict]:
    """Compute Defense vs Position scores from play-by-play data over last 4 weeks.

    DVP = fantasy points allowed by each defense to each offensive position.
    Returns list of dicts with keys: week, team, position, dvp_score, opponent_rank.

    Fantasy points derived from PBP (standard scoring):
    - Passing: passing_yards * 0.04 + pass_touchdown * 4 - interception * 2
    - Rushing: rushing_yards * 0.1 + rush_touchdown * 6
    - Receiving: receiving_yards * 0.1 + pass_touchdown * 6
    (Used for ranking defenses, not player projections)

    Rank 1 = most points allowed = easiest matchup.
    """
    valid, missing = validate_pbp_schema(pbp_df)
    if not valid:
        log.error("Cannot compute DVP — missing PBP columns: %s", missing)
        return []

    week_start = max(1, current_week - 4)
    week_end = current_week
    weeks = list(range(week_start, week_end))

    filtered = pbp_df.filter(
        (pl.col("season") == season) &
        (pl.col("week").is_in(weeks))
    )

    if filtered.is_empty():
        log.warning("No PBP data found for season=%s weeks=%s", season, weeks)
        return []

    results = []

    # --- QB DVP: points from passing plays (passer_player_id is not null) ---
    # Passing fantasy points allowed per defense
    pass_plays = filtered.filter(pl.col("passer_player_id").is_not_null())
    if not pass_plays.is_empty():
        qb_dvp = (
            pass_plays
            .group_by("defteam")
            .agg(
                (
                    pl.col("passing_yards").fill_null(0) * 0.04
                    + pl.col("pass_touchdown").fill_null(0) * 4.0
                    - pl.col("interception").fill_null(0) * 2.0
                ).sum().alias("dvp_score")
            )
        )
        # Rank: rank 1 = most points allowed (easiest matchup for QB)
        qb_dvp = qb_dvp.with_columns(
            pl.col("dvp_score")
            .rank(method="ordinal", descending=True)
            .cast(pl.Int32)
            .alias("opponent_rank")
        )
        for row in qb_dvp.to_dicts():
            results.append({
                "week": current_week,
                "team": row["defteam"],
                "position": "QB",
                "dvp_score": float(row["dvp_score"]),
                "opponent_rank": int(row["opponent_rank"]),
            })

    # --- RB DVP: points from rushing plays (rusher_player_id not null, passer null) ---
    rush_plays = filtered.filter(
        pl.col("rusher_player_id").is_not_null() &
        pl.col("passer_player_id").is_null()
    )
    if not rush_plays.is_empty():
        rb_dvp = (
            rush_plays
            .group_by("defteam")
            .agg(
                (
                    pl.col("rushing_yards").fill_null(0) * 0.1
                    + pl.col("rush_touchdown").fill_null(0) * 6.0
                    - pl.col("fumble_lost").fill_null(0) * 2.0
                ).sum().alias("dvp_score")
            )
        )
        rb_dvp = rb_dvp.with_columns(
            pl.col("dvp_score")
            .rank(method="ordinal", descending=True)
            .cast(pl.Int32)
            .alias("opponent_rank")
        )
        for row in rb_dvp.to_dicts():
            results.append({
                "week": current_week,
                "team": row["defteam"],
                "position": "RB",
                "dvp_score": float(row["dvp_score"]),
                "opponent_rank": int(row["opponent_rank"]),
            })

    # --- WR/TE DVP: points from pass plays (receiver_player_id not null) ---
    # Use pass_plays already filtered above but group for receiving
    if not pass_plays.is_empty():
        rec_plays = pass_plays.filter(pl.col("receiver_player_id").is_not_null())
        if not rec_plays.is_empty():
            wr_dvp = (
                rec_plays
                .group_by("defteam")
                .agg(
                    (
                        pl.col("receiving_yards").fill_null(0) * 0.1
                        + pl.col("pass_touchdown").fill_null(0) * 6.0
                    ).sum().alias("dvp_score")
                )
            )
            wr_dvp = wr_dvp.with_columns(
                pl.col("dvp_score")
                .rank(method="ordinal", descending=True)
                .cast(pl.Int32)
                .alias("opponent_rank")
            )
            for row in wr_dvp.to_dicts():
                results.append({
                    "week": current_week,
                    "team": row["defteam"],
                    "position": "WR",
                    "dvp_score": float(row["dvp_score"]),
                    "opponent_rank": int(row["opponent_rank"]),
                })

    return results
