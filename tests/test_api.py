"""FastAPI route tests via TestClient — TDD RED/GREEN for /search and /player/{id}."""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.fantasy.db.base import Base
from src.fantasy.db.models import GameLine, Matchup, Player


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


# ---------------------------------------------------------------------------
# /compare endpoint tests
# ---------------------------------------------------------------------------


@pytest.fixture
def compare_fixture(client):
    """Two players: WR with matchup, RB without matchup."""
    c, session = client
    matchup = Matchup(week=1, team="MIN", position="WR", opponent_rank=5, dvp_score=45.0)
    session.add(matchup)
    session.flush()

    player_a = make_player(
        "nfl_cmp_01",
        "Justin Jefferson",
        "WR",
        "MIN",
        week1_snap_pct=0.85,
        week2_snap_pct=0.80,
        week3_snap_pct=0.75,
        week4_snap_pct=0.82,
        week1_target_share=0.28,
        week2_target_share=0.25,
        week3_target_share=0.22,
        week4_target_share=0.30,
        matchup_id=matchup.id,
    )
    player_b = make_player(
        "nfl_cmp_02",
        "Dalvin Cook",
        "RB",
        "MIN",
        week1_snap_pct=0.60,
        week2_snap_pct=0.55,
        week3_snap_pct=0.65,
        week4_snap_pct=0.58,
        week1_carry_share=0.40,
        week2_carry_share=0.38,
        week3_carry_share=0.42,
        week4_carry_share=0.35,
    )
    session.add(player_a)
    session.add(player_b)
    session.commit()
    return c, session, player_a, player_b


def test_compare_returns_both_players(compare_fixture):
    """GET /compare?a=&b= returns 200 with player_a and player_b payloads."""
    c, session, player_a, player_b = compare_fixture
    resp = c.get(f"/compare?a={player_a.id}&b={player_b.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert "player_a" in data
    assert "player_b" in data
    for key in ("verdict", "full_name", "score", "reasons"):
        assert key in data["player_a"], f"missing key '{key}' in player_a"
        assert key in data["player_b"], f"missing key '{key}' in player_b"


def test_compare_invalid_b_returns_404(compare_fixture):
    """GET /compare?a={valid}&b={invalid} returns 404."""
    c, session, player_a, player_b = compare_fixture
    resp = c.get(f"/compare?a={player_a.id}&b=999999")
    assert resp.status_code == 404


def test_compare_invalid_a_returns_404(compare_fixture):
    """GET /compare?a={invalid}&b={valid} returns 404."""
    c, session, player_a, player_b = compare_fixture
    resp = c.get(f"/compare?a=999999&b={player_b.id}")
    assert resp.status_code == 404


def test_compare_format_standard(compare_fixture):
    """GET /compare?format=standard returns scoring_format='standard' for both players."""
    c, session, player_a, player_b = compare_fixture
    resp = c.get(f"/compare?a={player_a.id}&b={player_b.id}&format=standard")
    assert resp.status_code == 200
    data = resp.json()
    assert data["player_a"]["scoring_format"] == "standard"
    assert data["player_b"]["scoring_format"] == "standard"


def test_compare_both_invalid_returns_404(compare_fixture):
    """GET /compare?a={invalid}&b={invalid} returns 404."""
    c, session, player_a, player_b = compare_fixture
    resp = c.get("/compare?a=999998&b=999999")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Vegas / weather GameLine tests
# ---------------------------------------------------------------------------


def test_player_detail_includes_vegas_and_weather(client):
    """GET /player/{id} includes vegas_implied_total and weather_flag when GameLine exists."""
    c, session = client
    matchup = Matchup(week=1, team="KC", position="QB", opponent_rank=10, dvp_score=30.0)
    session.add(matchup)
    session.flush()
    gl = GameLine(
        week=1, home_team="KC", away_team="BUF",
        game_total=47.5, home_spread=-3.5,
        home_implied_total=25.5, away_implied_total=22.0,
        is_dome=False, wind_mph=20.0, precip_probability=10,
        weather_flag=True, game_date="2026-01-04",
    )
    session.add(gl)
    session.flush()
    player = make_player("nfl_vegas_01", "Patrick Mahomes", "QB", "KC", matchup_id=matchup.id)
    session.add(player)
    session.commit()
    resp = c.get(f"/player/{player.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["vegas_implied_total"] == 25.5
    assert data["game_total"] == 47.5
    assert data["weather_flag"] is True
    assert data["wind_mph"] == 20.0


def test_player_detail_away_team_implied_total(client):
    """Away team player gets away_implied_total, not home_implied_total."""
    c, session = client
    matchup = Matchup(week=2, team="BUF", position="QB", opponent_rank=15, dvp_score=25.0)
    session.add(matchup)
    session.flush()
    gl = GameLine(
        week=2, home_team="KC", away_team="BUF",
        game_total=50.0, home_spread=-3.5,
        home_implied_total=26.75, away_implied_total=23.25,
        is_dome=False, wind_mph=5.0, precip_probability=0,
        weather_flag=False, game_date="2026-01-11",
    )
    session.add(gl)
    session.flush()
    player = make_player("nfl_vegas_02", "Josh Allen", "QB", "BUF", matchup_id=matchup.id)
    session.add(player)
    session.commit()
    resp = c.get(f"/player/{player.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["vegas_implied_total"] == 23.25
    assert data["weather_flag"] is False


def test_player_detail_no_game_line(client):
    """Player with no GameLine returns vegas_implied_total=None and weather_flag=False."""
    c, session = client
    matchup = Matchup(week=3, team="PHI", position="WR", opponent_rank=8, dvp_score=40.0)
    session.add(matchup)
    session.flush()
    player = make_player("nfl_vegas_03", "A.J. Brown", "WR", "PHI", matchup_id=matchup.id)
    session.add(player)
    session.commit()
    resp = c.get(f"/player/{player.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["vegas_implied_total"] is None
    assert data["game_total"] is None
    assert data["weather_flag"] is False
    assert data["wind_mph"] is None
    assert data["precip_probability"] is None
    assert data["is_dome"] is None


def test_compare_includes_vegas_fields(client):
    """/compare returns vegas_implied_total and weather_flag for both players."""
    c, session = client
    matchup = Matchup(week=1, team="SF", position="WR", opponent_rank=3, dvp_score=50.0)
    session.add(matchup)
    session.flush()
    gl = GameLine(
        week=1, home_team="SF", away_team="DAL",
        game_total=48.0, home_spread=-7.0,
        home_implied_total=27.5, away_implied_total=20.5,
        is_dome=False, wind_mph=8.0, precip_probability=5,
        weather_flag=False, game_date="2026-01-04",
    )
    session.add(gl)
    session.flush()
    player_a = make_player("nfl_cmp_sf_01", "Deebo Samuel", "WR", "SF", matchup_id=matchup.id)
    player_b = make_player("nfl_cmp_dal_01", "CeeDee Lamb", "WR", "DAL", matchup_id=matchup.id)
    session.add(player_a)
    session.add(player_b)
    session.commit()
    resp = c.get(f"/compare?a={player_a.id}&b={player_b.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["player_a"]["vegas_implied_total"] == 27.5  # SF is home
    assert data["player_b"]["vegas_implied_total"] == 20.5  # DAL is away
    for key in ("game_total", "weather_flag", "wind_mph", "precip_probability", "is_dome"):
        assert key in data["player_a"]
        assert key in data["player_b"]
