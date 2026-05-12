"""Phase 7 Offseason Analysis Hub — tests for models, scripts, and API endpoints."""
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.fantasy.db.base import Base
from src.fantasy.db.models import DynastyValue, OffseasonMove, Player, RookiePick


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
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


def _now():
    return datetime.now(timezone.utc)


def _make_rookie(db, **kwargs) -> RookiePick:
    defaults = dict(
        player_name="Travis Hunter",
        position="WR",
        team="CIN",
        college="Colorado",
        nfl_round=1,
        nfl_pick=2,
        age=21.0,
        dynasty_value=7500,
        dynasty_overall_rank=5,
        dynasty_position_rank=2,
        opportunity_grade="A",
        opportunity_note="Top-5 dynasty asset, Round 1 capital — featured role expected",
        year1_projection=160.0,
        updated_at=_now(),
    )
    defaults.update(kwargs)
    row = RookiePick(**defaults)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _make_move(db, **kwargs) -> OffseasonMove:
    defaults = dict(
        player_name="Davante Adams",
        position="WR",
        from_team="LV",
        to_team="LAR",
        move_type="free_agent",
        fantasy_impact="high",
        impact_direction="up",
        impact_note="LV → LAR: High-value WR changes teams — new scheme/role",
        dynasty_value=4500,
        move_season=2026,
        updated_at=_now(),
    )
    defaults.update(kwargs)
    row = OffseasonMove(**defaults)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _make_dv(db, **kwargs) -> DynastyValue:
    defaults = dict(
        player_name="CeeDee Lamb",
        position="WR",
        team="DAL",
        age=25.0,
        value=8500,
        overall_rank=2,
        position_rank=1,
        trend_30day=200,
        is_pick=False,
        updated_at=_now(),
    )
    defaults.update(kwargs)
    row = DynastyValue(**defaults)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class TestRookiePickModel:
    def test_create_and_retrieve(self, client):
        _, db = client
        r = _make_rookie(db)
        fetched = db.query(RookiePick).filter_by(id=r.id).first()
        assert fetched.player_name == "Travis Hunter"
        assert fetched.position == "WR"
        assert fetched.nfl_round == 1
        assert fetched.nfl_pick == 2
        assert fetched.opportunity_grade == "A"
        assert fetched.year1_projection == 160.0

    def test_unique_player_name(self, client):
        from sqlalchemy.exc import IntegrityError
        _, db = client
        _make_rookie(db)
        with pytest.raises(IntegrityError):
            _make_rookie(db)  # duplicate player_name


class TestOffseasonMoveModel:
    def test_create_and_retrieve(self, client):
        _, db = client
        m = _make_move(db)
        fetched = db.query(OffseasonMove).filter_by(id=m.id).first()
        assert fetched.player_name == "Davante Adams"
        assert fetched.move_type == "free_agent"
        assert fetched.from_team == "LV"
        assert fetched.to_team == "LAR"
        assert fetched.fantasy_impact == "high"
        assert fetched.impact_direction == "up"

    def test_unique_constraint(self, client):
        from sqlalchemy.exc import IntegrityError
        _, db = client
        _make_move(db, sleeper_id="s1")
        with pytest.raises(IntegrityError):
            _make_move(db, sleeper_id="s1")  # same sleeper_id + season + move_type


# ---------------------------------------------------------------------------
# refresh_rookies logic tests (unit — no live network calls)
# ---------------------------------------------------------------------------

class TestRefreshRookiesLogic:
    def test_year1_projection_qb_top10(self):
        from scripts.refresh_rookies import _year1_projection
        assert _year1_projection("QB", 1, 5) == 220.0

    def test_year1_projection_qb_r1_late(self):
        from scripts.refresh_rookies import _year1_projection
        assert _year1_projection("QB", 1, 15) == 160.0

    def test_year1_projection_wr_r2(self):
        from scripts.refresh_rookies import _year1_projection
        assert _year1_projection("WR", 2, 45) == 90.0

    def test_year1_projection_rb_r3plus(self):
        from scripts.refresh_rookies import _year1_projection
        assert _year1_projection("RB", 3, 80) == 60.0

    def test_year1_projection_unknown_position(self):
        from scripts.refresh_rookies import _year1_projection
        assert _year1_projection("K", 1, 1) is None

    def test_year1_projection_no_round(self):
        from scripts.refresh_rookies import _year1_projection
        assert _year1_projection("WR", None, None) == 55.0

    def test_opportunity_grade_a_top_pick(self):
        from scripts.refresh_rookies import _opportunity_grade
        grade, note = _opportunity_grade("WR", 1, 5, 2)
        assert grade == "A"
        assert "dynasty" in note.lower() or "round 1" in note.lower()

    def test_opportunity_grade_b_day2(self):
        from scripts.refresh_rookies import _opportunity_grade
        grade, note = _opportunity_grade("RB", 2, 60, 8)
        assert grade == "B"

    def test_opportunity_grade_c_day3(self):
        from scripts.refresh_rookies import _opportunity_grade
        grade, note = _opportunity_grade("WR", 3, 120, 20)
        assert grade == "C"

    def test_opportunity_grade_d_late(self):
        from scripts.refresh_rookies import _opportunity_grade
        grade, note = _opportunity_grade("TE", 5, 200, 30)
        assert grade == "D"


# ---------------------------------------------------------------------------
# refresh_offseason_moves logic tests
# ---------------------------------------------------------------------------

class TestRefreshMovesLogic:
    def test_classify_impact_cut_high_value(self):
        from scripts.refresh_offseason_moves import _classify_impact
        impact, direction, note = _classify_impact(5000, "cut", "WR")
        assert impact == "high"
        assert direction == "down"

    def test_classify_impact_fa_high_value(self):
        from scripts.refresh_offseason_moves import _classify_impact
        impact, direction, note = _classify_impact(4000, "free_agent", "WR")
        assert impact == "high"
        assert direction == "up"

    def test_classify_impact_fa_low_value(self):
        from scripts.refresh_offseason_moves import _classify_impact
        impact, direction, note = _classify_impact(500, "free_agent", "RB")
        assert impact == "low"
        assert direction == "neutral"

    def test_classify_impact_trade_medium(self):
        from scripts.refresh_offseason_moves import _classify_impact
        impact, direction, note = _classify_impact(1500, "trade", "TE")
        assert impact == "medium"

    def test_classify_impact_none_value(self):
        from scripts.refresh_offseason_moves import _classify_impact
        impact, direction, note = _classify_impact(None, "free_agent", "QB")
        assert impact == "low"


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------

class TestOffseasonRookiesEndpoint:
    def test_empty_returns_zero(self, client):
        c, _ = client
        resp = c.get("/offseason/rookies")
        assert resp.status_code == 200
        data = resp.json()
        assert data["rookies"] == []
        assert data["total"] == 0

    def test_returns_seeded_rookies(self, client):
        c, db = client
        _make_rookie(db, player_name="Travis Hunter", position="WR", opportunity_grade="A")
        _make_rookie(db, player_name="Ashton Jeanty", position="RB", opportunity_grade="A",
                     dynasty_overall_rank=3, nfl_pick=4)
        resp = c.get("/offseason/rookies")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2

    def test_filter_by_position(self, client):
        c, db = client
        _make_rookie(db, player_name="Travis Hunter", position="WR")
        _make_rookie(db, player_name="Ashton Jeanty", position="RB", dynasty_overall_rank=3, nfl_pick=4)
        resp = c.get("/offseason/rookies?position=WR")
        data = resp.json()
        assert data["total"] == 1
        assert data["rookies"][0]["position"] == "WR"

    def test_filter_by_grade(self, client):
        c, db = client
        _make_rookie(db, player_name="Travis Hunter", opportunity_grade="A")
        _make_rookie(db, player_name="Tier C Rookie", opportunity_grade="C",
                     dynasty_overall_rank=150, nfl_round=3, nfl_pick=80)
        resp = c.get("/offseason/rookies?grade=A")
        data = resp.json()
        assert data["total"] == 1
        assert data["rookies"][0]["opportunity_grade"] == "A"

    def test_sorted_by_dynasty_rank(self, client):
        c, db = client
        _make_rookie(db, player_name="Lesser Rook", dynasty_overall_rank=50, nfl_pick=30)
        _make_rookie(db, player_name="Top Rook", dynasty_overall_rank=2, nfl_pick=2)
        resp = c.get("/offseason/rookies")
        names = [r["player_name"] for r in resp.json()["rookies"]]
        assert names[0] == "Top Rook"


class TestOffseasonMovesEndpoint:
    def test_empty(self, client):
        c, _ = client
        resp = c.get("/offseason/moves")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_returns_moves(self, client):
        c, db = client
        _make_move(db, sleeper_id="s1")
        _make_move(db, player_name="Other Guy", sleeper_id="s2", position="RB",
                   from_team="KC", to_team="PHI", move_type="trade", dynasty_value=2000)
        resp = c.get("/offseason/moves")
        assert resp.json()["total"] == 2

    def test_filter_by_position(self, client):
        c, db = client
        _make_move(db, sleeper_id="s1", position="WR")
        _make_move(db, player_name="RB Guy", sleeper_id="s2", position="RB",
                   move_type="trade", dynasty_value=1000)
        resp = c.get("/offseason/moves?position=WR")
        data = resp.json()
        assert data["total"] == 1

    def test_filter_by_impact(self, client):
        c, db = client
        _make_move(db, sleeper_id="s1", fantasy_impact="high")
        _make_move(db, player_name="Low Guy", sleeper_id="s2", fantasy_impact="low",
                   dynasty_value=500, move_type="trade")
        resp = c.get("/offseason/moves?impact=high")
        assert resp.json()["total"] == 1

    def test_filter_by_team(self, client):
        c, db = client
        _make_move(db, sleeper_id="s1", from_team="LV", to_team="LAR")
        _make_move(db, player_name="PHI Guy", sleeper_id="s2", from_team="NYG", to_team="PHI",
                   move_type="trade", dynasty_value=2000)
        resp = c.get("/offseason/moves?team=LAR")
        assert resp.json()["total"] == 1

    def test_sorted_by_dynasty_value_desc(self, client):
        c, db = client
        _make_move(db, player_name="Low Val", sleeper_id="s1", dynasty_value=500)
        _make_move(db, player_name="High Val", sleeper_id="s2", dynasty_value=8000, move_type="trade")
        moves = c.get("/offseason/moves").json()["moves"]
        assert moves[0]["player_name"] == "High Val"


class TestOffseasonRisersFallersEndpoint:
    def test_empty(self, client):
        c, _ = client
        resp = c.get("/offseason/risers-fallers")
        assert resp.status_code == 200
        data = resp.json()
        assert data["risers"] == []
        assert data["fallers"] == []

    def test_risers_positive_trend(self, client):
        c, db = client
        _make_dv(db, player_name="Hot WR", trend_30day=500)
        _make_dv(db, player_name="Cold RB", position="RB", trend_30day=-300, value=3000,
                 overall_rank=20, position_rank=5)
        data = c.get("/offseason/risers-fallers").json()
        assert len(data["risers"]) == 1
        assert data["risers"][0]["player_name"] == "Hot WR"
        assert len(data["fallers"]) == 1
        assert data["fallers"][0]["player_name"] == "Cold RB"

    def test_excludes_picks(self, client):
        c, db = client
        _make_dv(db, player_name="2027 1st", is_pick=True, trend_30day=100)
        data = c.get("/offseason/risers-fallers").json()
        assert data["risers"] == []


class TestOffseasonCheatSheetEndpoint:
    def test_empty(self, client):
        c, _ = client
        resp = c.get("/offseason/cheat-sheet")
        assert resp.status_code == 200
        data = resp.json()
        assert data["positions"] == {}

    def test_groups_by_position(self, client):
        c, db = client
        _make_dv(db, player_name="WR1", position="WR", overall_rank=1, position_rank=1)
        _make_dv(db, player_name="QB1", position="QB", value=7000, overall_rank=5, position_rank=1)
        data = c.get("/offseason/cheat-sheet").json()
        assert "WR" in data["positions"]
        assert "QB" in data["positions"]

    def test_rookie_flag_annotated(self, client):
        c, db = client
        _make_dv(db, player_name="Travis Hunter", position="WR", overall_rank=5, position_rank=2)
        _make_rookie(db, player_name="Travis Hunter", opportunity_grade="A", year1_projection=160.0)
        data = c.get("/offseason/cheat-sheet").json()
        wr = data["positions"]["WR"]
        hunter = next(p for p in wr if p["player_name"] == "Travis Hunter")
        assert hunter["is_rookie"] is True
        assert hunter["opportunity_grade"] == "A"
        assert hunter["year1_projection"] == 160.0

    def test_tier_assignment(self, client):
        c, db = client
        _make_dv(db, player_name="Elite Guy", value=7000, overall_rank=1, position_rank=1)
        _make_dv(db, player_name="Depth Guy", position="RB", value=500, overall_rank=200,
                 position_rank=40)
        data = c.get("/offseason/cheat-sheet").json()
        elite = data["positions"]["WR"][0]
        assert elite["tier"] == "elite"
        depth = data["positions"]["RB"][0]
        assert depth["tier"] == "depth"

    def test_excludes_picks(self, client):
        c, db = client
        _make_dv(db, player_name="2027 Pick", is_pick=True, overall_rank=30, position_rank=5)
        data = c.get("/offseason/cheat-sheet").json()
        # Picks have no position bucket in the standard QB/RB/WR/TE grouping
        for pos_list in data["positions"].values():
            names = [p["player_name"] for p in pos_list]
            assert "2027 Pick" not in names


class TestOffseasonTeamEndpoint:
    def test_empty_team(self, client):
        c, _ = client
        resp = c.get("/offseason/team/PHI")
        assert resp.status_code == 200
        data = resp.json()
        assert data["team"] == "PHI"
        assert data["arrivals"] == []
        assert data["departures"] == []
        assert data["draft_picks"] == []

    def test_arrivals_and_departures(self, client):
        c, db = client
        _make_move(db, player_name="Arrival Guy", sleeper_id="s1", from_team="NYG", to_team="PHI")
        _make_move(db, player_name="Departure Guy", sleeper_id="s2", from_team="PHI",
                   to_team="DAL", move_type="trade", dynasty_value=3000)
        data = c.get("/offseason/team/PHI").json()
        assert len(data["arrivals"]) == 1
        assert data["arrivals"][0]["player_name"] == "Arrival Guy"
        assert len(data["departures"]) == 1
        assert data["departures"][0]["player_name"] == "Departure Guy"

    def test_draft_picks_shown(self, client):
        c, db = client
        _make_rookie(db, player_name="PHI Rookie", team="PHI")
        data = c.get("/offseason/team/PHI").json()
        assert len(data["draft_picks"]) == 1
        assert data["draft_picks"][0]["team"] == "PHI"
