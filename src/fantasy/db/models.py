"""SQLAlchemy ORM models for Player, Matchup, GameLine, DynastyValue, KeeperCost, DraftSession, RookiePick, and OffseasonMove tables."""
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
    value = Column(Integer, nullable=False)              # dynasty value
    overall_rank = Column(Integer, nullable=True)         # dynasty overall rank
    position_rank = Column(Integer, nullable=True)        # dynasty position rank
    trend_30day = Column(Integer, nullable=True)
    redraft_value = Column(Integer, nullable=True)        # current-season redraft value
    redraft_overall_rank = Column(Integer, nullable=True)
    redraft_position_rank = Column(Integer, nullable=True)
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


class RookiePick(Base):
    """2026 NFL Draft class with landing team, dynasty value, and year-1 fantasy projection."""

    __tablename__ = "rookie_pick"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sleeper_id = Column(String(20), nullable=True, index=True)
    player_name = Column(String(100), nullable=False, unique=True)
    position = Column(String(5), nullable=True)
    team = Column(String(5), nullable=True)          # landing NFL team
    college = Column(String(100), nullable=True)
    nfl_round = Column(Integer, nullable=True)        # 1-7
    nfl_pick = Column(Integer, nullable=True)         # overall pick number 1-262
    age = Column(Float, nullable=True)
    dynasty_value = Column(Integer, nullable=True)    # FantasyCalc dynasty value snapshot
    dynasty_overall_rank = Column(Integer, nullable=True)
    dynasty_position_rank = Column(Integer, nullable=True)
    opportunity_grade = Column(String(2), nullable=True)   # A, B, C, D
    opportunity_note = Column(String(200), nullable=True)
    year1_projection = Column(Float, nullable=True)        # projected PPR points season total
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class OffseasonMove(Base):
    """Offseason transactions: free agent signings, trades, draft picks, cuts."""

    __tablename__ = "offseason_move"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sleeper_id = Column(String(20), nullable=True, index=True)
    player_name = Column(String(100), nullable=False)
    position = Column(String(5), nullable=True)
    from_team = Column(String(5), nullable=True)     # None for rookies / undrafted
    to_team = Column(String(5), nullable=True)       # None for cuts / retirements
    move_type = Column(String(20), nullable=False)   # free_agent | trade | draft_pick | cut | undrafted_fa
    fantasy_impact = Column(String(10), nullable=True)   # high | medium | low
    impact_direction = Column(String(10), nullable=True) # up | down | neutral
    impact_note = Column(String(300), nullable=True)
    dynasty_value = Column(Integer, nullable=True)
    move_season = Column(Integer, nullable=False, default=2026)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("sleeper_id", "move_season", "move_type", name="uq_offseason_move"),
    )


class NFLDraftPick(Base):
    """Complete NFL Draft record — all 257 picks (every position) for a given year.

    Source of truth for round/pick/college/landing team. RookiePick references this
    by player_name to inherit real draft slot data when available.
    """

    __tablename__ = "nfl_draft_pick"

    id = Column(Integer, primary_key=True, autoincrement=True)
    draft_year = Column(Integer, nullable=False, index=True)
    overall = Column(Integer, nullable=False)
    round = Column(Integer, nullable=False)
    pick_in_round = Column(Integer, nullable=False)
    player_name = Column(String(100), nullable=False)
    position = Column(String(5), nullable=True)             # QB/RB/WR/TE/OT/DT/EDGE/CB/etc
    college = Column(String(100), nullable=True)
    college_full = Column(String(150), nullable=True)
    nfl_team = Column(String(5), nullable=True)              # 2-3 letter abbreviation
    nfl_team_id = Column(String(10), nullable=True)          # ESPN team id
    nfl_team_name = Column(String(100), nullable=True)
    nfl_team_logo = Column(String(300), nullable=True)
    espn_athlete_id = Column(String(20), nullable=True)
    traded = Column(Boolean, nullable=False, default=False)
    trade_note = Column(String(300), nullable=True)
    headshot_url = Column(String(300), nullable=True)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("draft_year", "overall", name="uq_nfl_draft_year_overall"),
    )


class TeamDepthChart(Base):
    """Team depth chart by position with fantasy-relevant ordering.

    One row per (team, position, depth_order). depth_order=1 is the projected starter,
    2 is RB2/WR2/etc., 3+ is reserve. Synthesized from FantasyCalc dynasty position
    rank within team + roster context.
    """

    __tablename__ = "team_depth_chart"

    id = Column(Integer, primary_key=True, autoincrement=True)
    team = Column(String(5), nullable=False, index=True)
    position = Column(String(5), nullable=False)
    depth_order = Column(Integer, nullable=False)            # 1 = starter, 2 = backup, ...
    player_name = Column(String(100), nullable=False)
    sleeper_id = Column(String(20), nullable=True)
    age = Column(Float, nullable=True)
    dynasty_value = Column(Integer, nullable=True)
    dynasty_position_rank = Column(Integer, nullable=True)
    is_rookie = Column(Boolean, nullable=False, default=False)
    season = Column(Integer, nullable=False, default=2026)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("season", "team", "position", "depth_order", name="uq_depth_team_pos_order"),
    )


class ScheduleStrength(Base):
    """Strength of schedule per team per position, derived from prior-season DVP.

    Higher sos_score = harder schedule (faces tougher position defenses on average).
    Used to apply a multiplier to year-1 rookie projections.
    """

    __tablename__ = "schedule_strength"

    id = Column(Integer, primary_key=True, autoincrement=True)
    season = Column(Integer, nullable=False)
    team = Column(String(5), nullable=False, index=True)
    position = Column(String(5), nullable=False)             # QB/RB/WR/TE
    sos_score = Column(Float, nullable=False)                # 0-100, 50 = league average
    sos_rank = Column(Integer, nullable=True)                # 1 = easiest, 32 = hardest
    avg_opp_dvp_rank = Column(Float, nullable=True)          # mean opponent DVP rank faced
    games_played = Column(Integer, nullable=True)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("season", "team", "position", name="uq_sos_season_team_pos"),
    )


class DynastyProjection(Base):
    """Multi-year dynasty value forecast — one row per (player, projection_year).

    Computed from current FantasyCalc value × position-specific age curve × role decay.
    """

    __tablename__ = "dynasty_projection"

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_name = Column(String(100), nullable=False, index=True)
    sleeper_id = Column(String(20), nullable=True, index=True)
    position = Column(String(5), nullable=True)
    base_year = Column(Integer, nullable=False)              # current year of the snapshot
    projection_year = Column(Integer, nullable=False)        # 1, 2, or 3 years out
    projected_value = Column(Integer, nullable=False)
    projected_age = Column(Float, nullable=True)
    decay_factor = Column(Float, nullable=True)              # multiplier applied
    role_label = Column(String(30), nullable=True)           # ascending / peak / declining / cliff
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("player_name", "base_year", "projection_year", name="uq_proj_player_year"),
    )


class HistoricalRookieComp(Base):
    """Historical rookie outcomes — used to find comps for current rookies.

    Seeded from nflverse data 2018-2025. Each row is one past rookie's year-1 outcome.
    """

    __tablename__ = "historical_rookie_comp"

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_name = Column(String(100), nullable=False)
    season = Column(Integer, nullable=False)                 # rookie year
    position = Column(String(5), nullable=False)
    nfl_round = Column(Integer, nullable=True)
    nfl_pick = Column(Integer, nullable=True)
    college = Column(String(100), nullable=True)
    nfl_team = Column(String(5), nullable=True)
    age_at_draft = Column(Float, nullable=True)
    year1_ppr_points = Column(Float, nullable=True)          # season total in PPR
    year1_games = Column(Integer, nullable=True)
    year1_starts = Column(Integer, nullable=True)
    year1_target_share = Column(Float, nullable=True)
    year1_carry_share = Column(Float, nullable=True)
    hit_label = Column(String(20), nullable=True)            # bust / depth / starter / breakout / elite
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("player_name", "season", name="uq_hist_rookie_player_season"),
    )
