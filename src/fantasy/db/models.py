"""SQLAlchemy ORM models for Player, Matchup, GameLine, DynastyValue, KeeperCost, and DraftSession tables."""
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
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


class DynastyValue(Base):
    """Dynasty value table: FantasyCalc dynasty trade values for players and picks."""

    __tablename__ = "dynasty_value"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fantasycalc_id = Column(Integer, nullable=True)
    sleeper_id = Column(String(20), nullable=True, index=True)
    player_name = Column(String(100), nullable=False, unique=True)
    position = Column(String(10), nullable=True)   # QB, RB, WR, TE, PICK
    team = Column(String(10), nullable=True)
    age = Column(Float, nullable=True)
    value = Column(Integer, nullable=False)
    overall_rank = Column(Integer, nullable=True)
    position_rank = Column(Integer, nullable=True)
    trend_30day = Column(Integer, nullable=True)    # value change over last 30 days
    is_pick = Column(Boolean, nullable=False, default=False)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class KeeperCost(Base):
    """Keeper cost table: user-managed keeper acquisition costs per player."""

    __tablename__ = "keeper_cost"

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_name = Column(String(100), nullable=False, unique=True)
    dynasty_value_id = Column(Integer, ForeignKey("dynasty_value.id"), nullable=True)
    keeper_round = Column(Integer, nullable=False)  # draft round you'd spend to keep them
    notes = Column(String(200), nullable=True)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class DraftSession(Base):
    """Draft session table: live snake draft board state."""

    __tablename__ = "draft_session"

    id = Column(String(36), primary_key=True)           # UUID
    num_teams = Column(Integer, nullable=False)          # 8-14
    num_rounds = Column(Integer, nullable=False)         # typically 15-20
    user_team_slot = Column(Integer, nullable=False)     # 1-indexed draft position
    drafted_ids = Column(Text, nullable=False, default="[]")   # JSON list of dynasty_value IDs in pick order
    queued_ids = Column(Text, nullable=False, default="[]")    # JSON list of dynasty_value IDs user wants
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class UserLeague(Base):
    """User-created fantasy league with custom roster."""

    __tablename__ = "user_league"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), nullable=False, index=True)   # Clerk sub claim
    name = Column(String(100), nullable=False)
    scoring_format = Column(String(10), nullable=False, default="ppr")  # ppr / half_ppr / standard
    num_teams = Column(Integer, nullable=False, default=12)
    draft_session_id = Column(String(36), ForeignKey("draft_session.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class UserRosterPlayer(Base):
    """A player on a user's league roster."""

    __tablename__ = "user_roster_player"

    id = Column(Integer, primary_key=True, autoincrement=True)
    league_id = Column(Integer, ForeignKey("user_league.id", ondelete="CASCADE"), nullable=False)
    player_id = Column(Integer, ForeignKey("player.id"), nullable=False)
    position_slot = Column(String(10), nullable=False, default="roster")  # starter / bench / ir / roster
    added_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("league_id", "player_id", name="uq_roster_league_player"),
    )
