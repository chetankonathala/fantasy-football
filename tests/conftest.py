"""Shared pytest fixtures: in-memory SQLite engine and session, mock data fixtures."""
import pytest
import polars as pl
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.fantasy.db.base import Base


@pytest.fixture
def db_engine():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def mock_sleeper_response():
    """Three sample Sleeper players: healthy (None injury_status), Questionable, Out."""
    return {
        "123": {
            "full_name": "Patrick Mahomes",
            "first_name": "Patrick",
            "last_name": "Mahomes",
            "position": "QB",
            "team": "KC",
            "injury_status": None,
            "practice_participation": None,
            "status": "Active",
            "injury_start_date": None,
        },
        "456": {
            "full_name": "Travis Kelce",
            "first_name": "Travis",
            "last_name": "Kelce",
            "position": "TE",
            "team": "KC",
            "injury_status": "Questionable",
            "practice_participation": "Limited",
            "status": "Active",
            "injury_start_date": "2025-11-15",
        },
        "789": {
            "full_name": "Christian McCaffrey",
            "first_name": "Christian",
            "last_name": "McCaffrey",
            "position": "RB",
            "team": "SF",
            "injury_status": "Out",
            "practice_participation": "Did Not Participate",
            "status": "Active",
            "injury_start_date": "2025-11-10",
        },
    }


@pytest.fixture
def mock_pbp_df():
    """Polars DataFrame with all REQUIRED_PBP_COLUMNS, ~20 rows covering 4 weeks, 2 teams."""
    rows = []
    # Generate play rows covering weeks 14-17, 2 teams (KC def, SF def)
    for week in [14, 15, 16, 17]:
        # KC defense vs SF offense (passing plays)
        for i in range(2):
            rows.append({
                "season": 2025,
                "week": week,
                "defteam": "KC",
                "posteam": "SF",
                "passing_yards": 20.0 + i * 5,
                "rushing_yards": 0.0,
                "receiving_yards": 20.0 + i * 5,
                "pass_touchdown": 0,
                "rush_touchdown": 0,
                "interception": 0,
                "fumble_lost": 0,
                "receiver_player_id": f"00-000000{i+1}",
                "rusher_player_id": None,
                "passer_player_id": "00-0000001",
                "play_type": "pass",
                "fantasy_points": (20.0 + i * 5) * 0.1,
            })
        # SF defense vs KC offense (rushing plays)
        for i in range(2):
            rows.append({
                "season": 2025,
                "week": week,
                "defteam": "SF",
                "posteam": "KC",
                "passing_yards": 0.0,
                "rushing_yards": 10.0 + i * 3,
                "receiving_yards": 0.0,
                "pass_touchdown": 0,
                "rush_touchdown": 1 if i == 1 else 0,
                "interception": 0,
                "fumble_lost": 0,
                "receiver_player_id": None,
                "rusher_player_id": f"00-000000{i+3}",
                "passer_player_id": None,
                "play_type": "run",
                "fantasy_points": (10.0 + i * 3) * 0.1 + (6.0 if i == 1 else 0),
            })
    return pl.DataFrame(rows)


@pytest.fixture
def mock_stats_df():
    """Polars DataFrame with player_id, recent_team, week, carries, targets, receptions, target_share."""
    rows = []
    players = [
        ("00-0000001", "KC", 0.0, 5, 4, 0.25),
        ("00-0000002", "KC", 8.0, 3, 2, 0.15),
        ("00-0000003", "SF", 0.0, 0, 0, 0.0),
        ("00-0000004", "SF", 12.0, 0, 0, 0.0),
    ]
    for week in [14, 15, 16, 17]:
        for pid, team, carries, targets, receptions, target_share in players:
            rows.append({
                "player_id": pid,
                "recent_team": team,
                "week": week,
                "carries": carries,
                "targets": float(targets),
                "receptions": float(receptions),
                "target_share": target_share,
                "rushing_yards": carries * 4.0,
                "receiving_yards": receptions * 10.0,
                "passing_yards": 0.0,
            })
    return pl.DataFrame(rows)
