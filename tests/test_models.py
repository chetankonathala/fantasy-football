"""Tests for Player and Matchup ORM models (TDD RED phase)."""
import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from src.fantasy.db.base import Base
from src.fantasy.db.models import Player, Matchup


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session(engine):
    Session = sessionmaker(bind=engine)
    sess = Session()
    yield sess
    sess.close()


def test_player_model_has_required_columns(engine):
    """Test 1: Player model has all required columns."""
    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("player")}

    required_columns = {
        "id",
        "nflverse_id",
        "sleeper_id",
        "full_name",
        "first_name",
        "last_name",
        "position",
        "team",
        "injury_status",
        "practice_participation",
        "status",
        "injury_start_date",
        "week1_snap_pct",
        "week2_snap_pct",
        "week3_snap_pct",
        "week4_snap_pct",
        "week1_target_share",
        "week2_target_share",
        "week3_target_share",
        "week4_target_share",
        "week1_carry_share",
        "week2_carry_share",
        "week3_carry_share",
        "week4_carry_share",
        "matchup_id",
        "updated_at",
    }
    missing = required_columns - columns
    assert not missing, f"Player model missing columns: {missing}"


def test_matchup_model_has_required_columns(engine):
    """Test 2: Matchup model has all required columns."""
    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("matchup")}

    required_columns = {
        "id",
        "week",
        "team",
        "position",
        "opponent_rank",
        "dvp_score",
    }
    missing = required_columns - columns
    assert not missing, f"Matchup model missing columns: {missing}"


def test_player_nflverse_id_unique_constraint(session):
    """Test 3: Player.nflverse_id has a unique constraint."""
    from datetime import datetime, timezone

    p1 = Player(nflverse_id="00-0001234", full_name="Test Player", updated_at=datetime.now(timezone.utc))
    session.add(p1)
    session.commit()

    from sqlalchemy.exc import IntegrityError
    p2 = Player(nflverse_id="00-0001234", full_name="Duplicate Player", updated_at=datetime.now(timezone.utc))
    session.add(p2)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_matchup_unique_constraint_week_team_position(session):
    """Test 4: Matchup has a unique constraint on (week, team, position)."""
    m1 = Matchup(week=1, team="KC", position="QB")
    session.add(m1)
    session.commit()

    from sqlalchemy.exc import IntegrityError
    m2 = Matchup(week=1, team="KC", position="QB")
    session.add(m2)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_player_matchup_id_foreign_key(engine):
    """Test 5: Player.matchup_id is a foreign key to Matchup table."""
    inspector = inspect(engine)
    fks = inspector.get_foreign_keys("player")
    assert len(fks) > 0, "Player table has no foreign keys"

    matchup_fk = [fk for fk in fks if fk["referred_table"] == "matchup"]
    assert len(matchup_fk) == 1, "Player.matchup_id does not reference matchup table"
    assert "matchup_id" in matchup_fk[0]["constrained_columns"]
