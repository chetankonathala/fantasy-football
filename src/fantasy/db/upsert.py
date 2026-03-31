"""SQLite upsert helpers for Player and Matchup tables.

Uses SQLite-specific insert().on_conflict_do_update() for atomic upsert semantics.
Never does a full-wipe; always upserts by canonical ID.
"""
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from src.fantasy.db.models import GameLine, Matchup, Player


def upsert_players(session: Session, player_dicts: list[dict]) -> int:
    """Upsert a list of player records by nflverse_id.

    Inserts new players; updates all mutable fields when nflverse_id already exists.

    Args:
        session: SQLAlchemy session
        player_dicts: list of dicts with player field values

    Returns:
        Number of rows affected (0 for empty input).
    """
    if not player_dicts:
        return 0

    # SQLite has a 999-variable limit per statement. Player has 24 columns,
    # so batch at 41 rows (41 * 24 = 984 variables).
    BATCH_SIZE = 41
    total = 0
    for i in range(0, len(player_dicts), BATCH_SIZE):
        batch = player_dicts[i : i + BATCH_SIZE]
        stmt = insert(Player).values(batch)
        stmt = stmt.on_conflict_do_update(
            index_elements=["nflverse_id"],
            set_={
                "sleeper_id": stmt.excluded.sleeper_id,
                "full_name": stmt.excluded.full_name,
                "first_name": stmt.excluded.first_name,
                "last_name": stmt.excluded.last_name,
                "position": stmt.excluded.position,
                "team": stmt.excluded.team,
                "injury_status": stmt.excluded.injury_status,
                "practice_participation": stmt.excluded.practice_participation,
                "status": stmt.excluded.status,
                "injury_start_date": stmt.excluded.injury_start_date,
                "week1_snap_pct": stmt.excluded.week1_snap_pct,
                "week2_snap_pct": stmt.excluded.week2_snap_pct,
                "week3_snap_pct": stmt.excluded.week3_snap_pct,
                "week4_snap_pct": stmt.excluded.week4_snap_pct,
                "week1_target_share": stmt.excluded.week1_target_share,
                "week2_target_share": stmt.excluded.week2_target_share,
                "week3_target_share": stmt.excluded.week3_target_share,
                "week4_target_share": stmt.excluded.week4_target_share,
                "week1_carry_share": stmt.excluded.week1_carry_share,
                "week2_carry_share": stmt.excluded.week2_carry_share,
                "week3_carry_share": stmt.excluded.week3_carry_share,
                "week4_carry_share": stmt.excluded.week4_carry_share,
                "matchup_id": stmt.excluded.matchup_id,
                "updated_at": stmt.excluded.updated_at,
            },
        )
        result = session.execute(stmt)
        total += result.rowcount
    session.commit()
    return total


def upsert_matchups(session: Session, matchup_dicts: list[dict]) -> int:
    """Upsert a list of matchup records by (week, team, position).

    Inserts new matchups; updates dvp_score and opponent_rank when key already exists.

    Args:
        session: SQLAlchemy session
        matchup_dicts: list of dicts with matchup field values

    Returns:
        Number of rows affected (0 for empty input).
    """
    if not matchup_dicts:
        return 0

    stmt = insert(Matchup).values(matchup_dicts)
    stmt = stmt.on_conflict_do_update(
        index_elements=["week", "team", "position"],
        set_={
            "opponent_rank": stmt.excluded.opponent_rank,
            "dvp_score": stmt.excluded.dvp_score,
        },
    )
    result = session.execute(stmt)
    session.commit()
    return result.rowcount


def upsert_game_lines(session: Session, game_line_dicts: list[dict]) -> int:
    """Upsert a list of game line records by (week, home_team, away_team).

    Inserts new game lines; updates all mutable fields when key already exists.

    Args:
        session: SQLAlchemy session
        game_line_dicts: list of dicts with game line field values

    Returns:
        Number of rows affected (0 for empty input).
    """
    if not game_line_dicts:
        return 0

    stmt = insert(GameLine).values(game_line_dicts)
    stmt = stmt.on_conflict_do_update(
        index_elements=["week", "home_team", "away_team"],
        set_={
            "game_total": stmt.excluded.game_total,
            "home_spread": stmt.excluded.home_spread,
            "home_implied_total": stmt.excluded.home_implied_total,
            "away_implied_total": stmt.excluded.away_implied_total,
            "is_dome": stmt.excluded.is_dome,
            "wind_mph": stmt.excluded.wind_mph,
            "precip_probability": stmt.excluded.precip_probability,
            "weather_flag": stmt.excluded.weather_flag,
            "game_date": stmt.excluded.game_date,
            "updated_at": stmt.excluded.updated_at,
        },
    )
    result = session.execute(stmt)
    session.commit()
    return result.rowcount
