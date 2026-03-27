"""FastAPI route tests via TestClient — TDD RED/GREEN for /search and /player/{id}."""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.fantasy.db.base import Base
from src.fantasy.db.models import Matchup, Player


@pytest.fixture
def client():
    """TestClient with dependency override to use in-memory test DB (shared via StaticPool)."""
    from main import app, get_db

    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        session = TestingSession()
        yield c, session
        session.close()
    app.dependency_overrides.clear()
    engine.dispose()


def make_player(nflverse_id, full_name, position, team, **kwargs):
    defaults = dict(
        nflverse_id=nflverse_id,
        full_name=full_name,
        position=position,
        team=team,
        updated_at=datetime.now(timezone.utc),
        week1_snap_pct=None,
        week2_snap_pct=None,
        week3_snap_pct=None,
        week4_snap_pct=None,
        week1_target_share=None,
        week2_target_share=None,
        week3_target_share=None,
        week4_target_share=None,
        week1_carry_share=None,
        week2_carry_share=None,
        week3_carry_share=None,
        week4_carry_share=None,
        injury_status=None,
        practice_participation=None,
    )
    defaults.update(kwargs)
    return Player(**defaults)


# ---------------------------------------------------------------------------
# Search tests
# ---------------------------------------------------------------------------


def test_search_returns_autocomplete(client):
    c, session = client
    session.add(make_player("nfl_001", "Justin Jefferson", "WR", "MIN"))
    session.add(make_player("nfl_002", "Justin Herbert", "QB", "LAC"))
    session.add(make_player("nfl_003", "Jalen Hurts", "QB", "PHI"))
    session.commit()

    resp = c.get("/search?q=jus")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    names = {p["full_name"] for p in data}
    assert names == {"Justin Jefferson", "Justin Herbert"}
    # Verify expected keys in each result
    for p in data:
        assert set(p.keys()) >= {"id", "full_name", "position", "team"}


def test_search_min_chars(client):
    c, session = client
    session.add(make_player("nfl_004", "Patrick Mahomes", "QB", "KC"))
    session.commit()

    resp = c.get("/search?q=j")
    assert resp.status_code == 200
    assert resp.json() == []


def test_search_no_results(client):
    c, session = client
    session.add(make_player("nfl_005", "Davante Adams", "WR", "LV"))
    session.commit()

    resp = c.get("/search?q=zzzzz")
    assert resp.status_code == 200
    assert resp.json() == []


def test_search_limit_5(client):
    c, session = client
    for i in range(7):
        session.add(make_player(f"nfl_l{i}", f"Test Player {i}", "WR", "MIN"))
    session.commit()

    resp = c.get("/search?q=Test")
    assert resp.status_code == 200
    assert len(resp.json()) == 5


# ---------------------------------------------------------------------------
# Player detail tests
# ---------------------------------------------------------------------------


@pytest.fixture
def player_with_matchup(client):
    c, session = client
    matchup = Matchup(week=1, team="MIN", position="WR", opponent_rank=5, dvp_score=45.0)
    session.add(matchup)
    session.flush()

    player = make_player(
        "nfl_rec_01",
        "Justin Jefferson",
        "WR",
        "MIN",
        week1_snap_pct=0.85,
        week2_snap_pct=0.0,
        week3_snap_pct=0.0,
        week4_snap_pct=0.0,
        week1_target_share=0.28,
        week2_target_share=0.0,
        week3_target_share=0.0,
        week4_target_share=0.0,
        matchup_id=matchup.id,
    )
    session.add(player)
    session.commit()
    return c, session, player, matchup


def test_player_detail_returns_recommendation(player_with_matchup):
    c, session, player, _ = player_with_matchup
    resp = c.get(f"/player/{player.id}")
    assert resp.status_code == 200
    data = resp.json()
    expected_keys = {"verdict", "score", "reasons", "low_confidence", "scoring_format",
                     "full_name", "position", "team"}
    assert expected_keys.issubset(data.keys())


def test_player_detail_injury_fields(player_with_matchup):
    c, session, player, _ = player_with_matchup
    resp = c.get(f"/player/{player.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert "injury_status" in data
    assert "practice_participation" in data


def test_player_detail_usage_fields(player_with_matchup):
    c, session, player, _ = player_with_matchup
    resp = c.get(f"/player/{player.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert "snap_pct_l4w" in data
    assert isinstance(data["snap_pct_l4w"], list)
    assert len(data["snap_pct_l4w"]) == 4
    assert "target_share_l4w" in data
    assert isinstance(data["target_share_l4w"], list)
    assert len(data["target_share_l4w"]) == 4
    assert "carry_share_l4w" in data
    assert isinstance(data["carry_share_l4w"], list)
    assert len(data["carry_share_l4w"]) == 4


def test_player_detail_updated_at(player_with_matchup):
    c, session, player, _ = player_with_matchup
    resp = c.get(f"/player/{player.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert "updated_at" in data
    assert isinstance(data["updated_at"], str)
    # Should be a valid ISO format string
    datetime.fromisoformat(data["updated_at"])


def test_player_format_selector(player_with_matchup):
    c, session, player, _ = player_with_matchup
    resp = c.get(f"/player/{player.id}?format=standard")
    assert resp.status_code == 200
    data = resp.json()
    assert data["scoring_format"] == "standard"


def test_player_not_found(client):
    c, session = client
    resp = c.get("/player/999999")
    assert resp.status_code == 404
