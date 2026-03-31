"""SQLAlchemy ORM models for Player, Matchup, and GameLine tables."""
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)

from src.fantasy.db.base import Base


class Matchup(Base):
    """Matchup table: DVP grade and opponent rank per week/team/position."""

    __tablename__ = "matchup"

    id = Column(Integer, primary_key=True, autoincrement=True)
    week = Column(Integer, nullable=False)
    team = Column(String(5), nullable=False)
    position = Column(String(5), nullable=False)
    opponent_rank = Column(Integer, nullable=True)  # rank 1-32 (1 = toughest)
    dvp_score = Column(Float, nullable=True)  # raw points allowed

    __table_args__ = (
        UniqueConstraint("week", "team", "position", name="uq_matchup_week_team_pos"),
    )


class Player(Base):
    """Player table: canonical player data with injury and usage stats."""

    __tablename__ = "player"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Canonical IDs
    nflverse_id = Column(String(20), unique=True, nullable=False, index=True)
    sleeper_id = Column(String(10), nullable=True, index=True)

    # Identity
    full_name = Column(String(100), nullable=False)
    first_name = Column(String(50), nullable=True)
    last_name = Column(String(50), nullable=True)

    # Roster info
    position = Column(String(5), nullable=True)  # QB, RB, WR, TE, K, DST
    team = Column(String(5), nullable=True)  # 2-3 letter team abbreviation

    # Injury / status fields (from Sleeper API)
    injury_status = Column(String(20), nullable=True)  # "Out", "Questionable", "Doubtful", "Probable", None=healthy
    practice_participation = Column(String(30), nullable=True)  # "Did Not Participate", "Limited", "Full", None
    status = Column(String(30), nullable=True)  # "Active", "Injured Reserve", "Practice Squad", etc.
    injury_start_date = Column(String(10), nullable=True)  # "YYYY-MM-DD" format

    # Usage stats: snap percentage (last 4 weeks)
    week1_snap_pct = Column(Float, nullable=True)
    week2_snap_pct = Column(Float, nullable=True)
    week3_snap_pct = Column(Float, nullable=True)
    week4_snap_pct = Column(Float, nullable=True)

    # Usage stats: target share (last 4 weeks)
    week1_target_share = Column(Float, nullable=True)
    week2_target_share = Column(Float, nullable=True)
    week3_target_share = Column(Float, nullable=True)
    week4_target_share = Column(Float, nullable=True)

    # Usage stats: carry share (last 4 weeks)
    week1_carry_share = Column(Float, nullable=True)
    week2_carry_share = Column(Float, nullable=True)
    week3_carry_share = Column(Float, nullable=True)
    week4_carry_share = Column(Float, nullable=True)

    # Matchup foreign key
    matchup_id = Column(Integer, ForeignKey("matchup.id"), nullable=True)

    # Audit
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class GameLine(Base):
    """GameLine table: Vegas odds and weather context per game per week."""

    __tablename__ = "game_line"

    id = Column(Integer, primary_key=True, autoincrement=True)
    week = Column(Integer, nullable=False)
    home_team = Column(String(5), nullable=False)
    away_team = Column(String(5), nullable=False)
    game_total = Column(Float, nullable=True)          # over/under line
    home_spread = Column(Float, nullable=True)         # home team spread (neg = favored)
    home_implied_total = Column(Float, nullable=True)  # (total/2) - (spread/2)
    away_implied_total = Column(Float, nullable=True)  # (total/2) + (spread/2)
    is_dome = Column(Boolean, nullable=False, default=False)
    wind_mph = Column(Float, nullable=True)
    precip_probability = Column(Integer, nullable=True)  # 0-100
    weather_flag = Column(Boolean, nullable=False, default=False)
    game_date = Column(String(10), nullable=True)  # "YYYY-MM-DD" for weather lookup timing
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("week", "home_team", "away_team", name="uq_gameline_week_home_away"),
    )
