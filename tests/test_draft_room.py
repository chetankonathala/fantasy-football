"""Phase 6 Dynasty Draft Room — full test suite for all new endpoints."""
import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.fantasy.db.base import Base
from src.fantasy.db.models import DraftSession, DynastyValue, KeeperCost


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    """TestClient with in-memory DB override."""
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


def _make_dv(db, **kwargs) -> DynastyValue:
    defaults = dict(
        player_name="Test Player",
        position="WR",
        team="PHI",
        age=24.0,
        value=5000,
        overall_rank=10,
        position_rank=3,
        trend_30day=50,
        is_pick=False,
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(kwargs)
    dv = DynastyValue(**defaults)
    db.add(dv)
    db.commit()
    db.refresh(dv)
    return dv


def _make_pick_dv(db, name="2025 1st", value=8000) -> DynastyValue:
    dv = DynastyValue(
        player_name=name,
        position="PICK",
        is_pick=True,
        value=value,
        overall_rank=None,
        updated_at=datetime.now(timezone.utc),
    )
    db.add(dv)
    db.commit()
    db.refresh(dv)
    return dv


# ---------------------------------------------------------------------------
# /dynasty/rankings tests
# ---------------------------------------------------------------------------

class TestDynastyRankings:
    def test_returns_players_sorted_by_rank(self, client):
        c, db = client
        _make_dv(db, player_name="Justin Jefferson", position="WR", overall_rank=2, position_rank=1)
        _make_dv(db, player_name="CeeDee Lamb", position="WR", overall_rank=5, position_rank=2)
        resp = c.get("/dynasty/rankings")
        assert resp.status_code == 200
        names = [p["player_name"] for p in resp.json()]
        assert names.index("Justin Jefferson") < names.index("CeeDee Lamb")

    def test_excludes_picks(self, client):
        c, db = client
        _make_dv(db, player_name="Justin Jefferson", position="WR", overall_rank=1)
        _make_pick_dv(db, name="2025 1st")
        resp = c.get("/dynasty/rankings")
        assert resp.status_code == 200
        names = [p["player_name"] for p in resp.json()]
        assert "2025 1st" not in names
        assert "Justin Jefferson" in names

    def test_position_filter(self, client):
        c, db = client
        _make_dv(db, player_name="Patrick Mahomes", position="QB", overall_rank=1)
        _make_dv(db, player_name="Justin Jefferson", position="WR", overall_rank=2)
        resp = c.get("/dynasty/rankings?position=QB")
        assert resp.status_code == 200
        positions = {p["position"] for p in resp.json()}
        assert positions == {"QB"}

    def test_age_grade_and_tier_present(self, client):
        c, db = client
        _make_dv(db, player_name="Young RB", position="RB", age=22.0, position_rank=2, overall_rank=5)
        resp = c.get("/dynasty/rankings")
        assert resp.status_code == 200
        player = resp.json()[0]
        assert "age_grade" in player
        assert "position_tier" in player
        assert player["age_grade"] == "A"   # RB age 22 → A
        assert player["position_tier"] == "Tier 1"  # position_rank 2 → Tier 1

    def test_age_grade_old_rb(self, client):
        c, db = client
        _make_dv(db, player_name="Old RB", position="RB", age=30.0, position_rank=5, overall_rank=10)
        resp = c.get("/dynasty/rankings")
        assert resp.status_code == 200
        assert resp.json()[0]["age_grade"] == "D"

    def test_empty_returns_empty_list(self, client):
        c, db = client
        resp = c.get("/dynasty/rankings")
        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# /dynasty/rookies tests
# ---------------------------------------------------------------------------

class TestDynastyRookies:
    def test_returns_only_young_players(self, client):
        c, db = client
        _make_dv(db, player_name="Rookie Star", position="WR", age=21.0, overall_rank=8)
        _make_dv(db, player_name="Vet Player", position="WR", age=29.0, overall_rank=20)
        resp = c.get("/dynasty/rookies")
        assert resp.status_code == 200
        names = [p["player_name"] for p in resp.json()]
        assert "Rookie Star" in names
        assert "Vet Player" not in names

    def test_rookie_fields_present(self, client):
        c, db = client
        _make_dv(db, player_name="Elite Rookie", position="WR", age=21.0, overall_rank=5, position_rank=2, team="KC")
        resp = c.get("/dynasty/rookies")
        assert resp.status_code == 200
        r = resp.json()[0]
        assert "ceiling" in r
        assert "floor" in r
        assert "landing_assessment" in r

    def test_elite_ceiling_for_top_overall(self, client):
        c, db = client
        _make_dv(db, player_name="Top Pick", position="RB", age=22.0, overall_rank=5)
        resp = c.get("/dynasty/rookies")
        assert resp.status_code == 200
        assert resp.json()[0]["ceiling"] == "Elite"

    def test_high_ceiling_for_mid_range(self, client):
        c, db = client
        _make_dv(db, player_name="Mid Rookie", position="WR", age=22.0, overall_rank=25)
        resp = c.get("/dynasty/rookies")
        assert resp.status_code == 200
        assert resp.json()[0]["ceiling"] == "High"

    def test_excludes_picks(self, client):
        c, db = client
        _make_pick_dv(db, name="2025 1st")
        resp = c.get("/dynasty/rookies")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_landing_assessment_featured_starter(self, client):
        c, db = client
        _make_dv(db, player_name="Starter", position="WR", age=22.0, overall_rank=5, position_rank=2, team="PHI")
        resp = c.get("/dynasty/rookies")
        assert resp.status_code == 200
        assert "Featured Starter" in resp.json()[0]["landing_assessment"]


# ---------------------------------------------------------------------------
# /dynasty/keepers tests
# ---------------------------------------------------------------------------

class TestKeeperCosts:
    def test_create_keeper(self, client):
        c, db = client
        dv = _make_dv(db, player_name="Ja'Marr Chase", position="WR", value=9000)
        resp = c.post("/dynasty/keepers", json={
            "player_name": "Ja'Marr Chase",
            "dynasty_value_id": dv.id,
            "keeper_round": 2,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["player_name"] == "Ja'Marr Chase"
        assert data["keeper_round"] == 2

    def test_list_keepers_with_recommendation(self, client):
        c, db = client
        dv = _make_dv(db, player_name="Ja'Marr Chase", position="WR", value=9000, overall_rank=3)
        c.post("/dynasty/keepers", json={
            "player_name": "Ja'Marr Chase",
            "dynasty_value_id": dv.id,
            "keeper_round": 2,
        })
        resp = c.get("/dynasty/keepers")
        assert resp.status_code == 200
        keepers = resp.json()
        assert len(keepers) == 1
        k = keepers[0]
        assert k["dynasty_value"] == 9000
        assert k["keeper_round"] == 2
        assert k["recommendation"] in ("KEEP", "BORDERLINE", "CUT")
        assert k["net_gain"] is not None

    def test_keep_recommendation_for_high_value(self, client):
        c, db = client
        # value=9000, round 2 keeper cost≈5500 → net +3500 → KEEP
        dv = _make_dv(db, player_name="Star WR", position="WR", value=9000)
        c.post("/dynasty/keepers", json={"player_name": "Star WR", "dynasty_value_id": dv.id, "keeper_round": 2})
        resp = c.get("/dynasty/keepers")
        assert resp.json()[0]["recommendation"] == "KEEP"

    def test_cut_recommendation_for_late_round_overpriced(self, client):
        c, db = client
        # value=400, round 1 cost≈8000 → net -7600 → CUT
        dv = _make_dv(db, player_name="Busted Prospect", position="RB", value=400)
        c.post("/dynasty/keepers", json={"player_name": "Busted Prospect", "dynasty_value_id": dv.id, "keeper_round": 1})
        resp = c.get("/dynasty/keepers")
        assert resp.json()[0]["recommendation"] == "CUT"

    def test_upsert_updates_existing(self, client):
        c, db = client
        dv = _make_dv(db, player_name="Player X", position="WR", value=5000)
        c.post("/dynasty/keepers", json={"player_name": "Player X", "dynasty_value_id": dv.id, "keeper_round": 3})
        c.post("/dynasty/keepers", json={"player_name": "Player X", "dynasty_value_id": dv.id, "keeper_round": 5})
        resp = c.get("/dynasty/keepers")
        keepers = resp.json()
        assert len(keepers) == 1
        assert keepers[0]["keeper_round"] == 5

    def test_delete_keeper(self, client):
        c, db = client
        dv = _make_dv(db, player_name="Delete Me", position="WR", value=5000)
        create_resp = c.post("/dynasty/keepers", json={"player_name": "Delete Me", "dynasty_value_id": dv.id, "keeper_round": 4})
        keeper_id = create_resp.json()["id"]
        del_resp = c.delete(f"/dynasty/keepers/{keeper_id}")
        assert del_resp.status_code == 204
        list_resp = c.get("/dynasty/keepers")
        assert list_resp.json() == []

    def test_delete_nonexistent_returns_404(self, client):
        c, db = client
        resp = c.delete("/dynasty/keepers/99999")
        assert resp.status_code == 404

    def test_invalid_keeper_round_rejected(self, client):
        c, db = client
        resp = c.post("/dynasty/keepers", json={"player_name": "Bad Round", "keeper_round": 0})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# /draft/sessions tests
# ---------------------------------------------------------------------------

class TestDraftSessions:
    def _create_session(self, c, num_teams=12, num_rounds=15, user_team_slot=6):
        resp = c.post("/draft/sessions", json={
            "num_teams": num_teams,
            "num_rounds": num_rounds,
            "user_team_slot": user_team_slot,
        })
        assert resp.status_code == 201
        return resp.json()

    def test_create_session_returns_full_state(self, client):
        c, db = client
        session = self._create_session(c)
        assert session["num_teams"] == 12
        assert session["num_rounds"] == 15
        assert session["user_team_slot"] == 6
        assert session["current_pick"] == 1
        assert len(session["drafted_players"]) == 0
        assert len(session["pick_order"]) == 12 * 15

    def test_snake_order_round2_reverses(self, client):
        c, db = client
        session = self._create_session(c, num_teams=4, num_rounds=2, user_team_slot=1)
        pick_order = session["pick_order"]
        # Round 1: team slots 1,2,3,4
        r1 = [p for p in pick_order if p["round"] == 1]
        # Round 2: team slots 4,3,2,1
        r2 = [p for p in pick_order if p["round"] == 2]
        assert [p["team_slot"] for p in r1] == [1, 2, 3, 4]
        assert [p["team_slot"] for p in r2] == [4, 3, 2, 1]

    def test_user_picks_identified(self, client):
        c, db = client
        session = self._create_session(c, num_teams=4, num_rounds=2, user_team_slot=2)
        user_picks = session["user_picks"]
        # In 4-team snake: R1P2 (overall 2) + R2P3 (overall 7)
        assert len(user_picks) == 2
        overall_picks = [p["pick"] for p in user_picks]
        assert 2 in overall_picks  # round 1, slot 2
        assert 7 in overall_picks  # round 2, slot 3 (reversed: 4,3,2,1 → slot 2 is index 2 → pick 7)

    def test_get_session(self, client):
        c, db = client
        created = self._create_session(c)
        resp = c.get(f"/draft/sessions/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == created["id"]

    def test_get_nonexistent_session_404(self, client):
        c, db = client
        resp = c.get("/draft/sessions/does-not-exist")
        assert resp.status_code == 404

    def test_list_sessions(self, client):
        c, db = client
        self._create_session(c)
        self._create_session(c, user_team_slot=3)
        resp = c.get("/draft/sessions")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_invalid_team_slot_rejected(self, client):
        c, db = client
        resp = c.post("/draft/sessions", json={"num_teams": 12, "num_rounds": 15, "user_team_slot": 13})
        assert resp.status_code == 422

    def test_invalid_num_teams_rejected(self, client):
        c, db = client
        resp = c.post("/draft/sessions", json={"num_teams": 1, "num_rounds": 15, "user_team_slot": 1})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# /draft/sessions/{id}/picks tests
# ---------------------------------------------------------------------------

class TestDraftPicks:
    def _setup(self, client, num_teams=4, num_rounds=2, user_team_slot=1):
        c, db = client
        session_resp = c.post("/draft/sessions", json={
            "num_teams": num_teams, "num_rounds": num_rounds, "user_team_slot": user_team_slot,
        })
        session_id = session_resp.json()["id"]
        dv1 = _make_dv(db, player_name="Player A", position="WR", overall_rank=1, value=9000)
        dv2 = _make_dv(db, player_name="Player B", position="RB", overall_rank=2, value=8000)
        return c, db, session_id, dv1, dv2

    def test_make_pick_advances_current_pick(self, client):
        c, db, session_id, dv1, dv2 = self._setup(client)
        resp = c.post(f"/draft/sessions/{session_id}/picks", json={"dynasty_value_id": dv1.id})
        assert resp.status_code == 200
        assert resp.json()["current_pick"] == 2
        assert len(resp.json()["drafted_players"]) == 1

    def test_drafted_player_in_response(self, client):
        c, db, session_id, dv1, dv2 = self._setup(client)
        c.post(f"/draft/sessions/{session_id}/picks", json={"dynasty_value_id": dv1.id})
        resp = c.get(f"/draft/sessions/{session_id}")
        drafted = resp.json()["drafted_players"]
        assert drafted[0]["player_name"] == "Player A"

    def test_duplicate_pick_rejected(self, client):
        c, db, session_id, dv1, dv2 = self._setup(client)
        c.post(f"/draft/sessions/{session_id}/picks", json={"dynasty_value_id": dv1.id})
        resp = c.post(f"/draft/sessions/{session_id}/picks", json={"dynasty_value_id": dv1.id})
        assert resp.status_code == 409

    def test_unknown_player_rejected(self, client):
        c, db, session_id, dv1, dv2 = self._setup(client)
        resp = c.post(f"/draft/sessions/{session_id}/picks", json={"dynasty_value_id": 99999})
        assert resp.status_code == 404

    def test_undo_last_pick(self, client):
        c, db, session_id, dv1, dv2 = self._setup(client)
        c.post(f"/draft/sessions/{session_id}/picks", json={"dynasty_value_id": dv1.id})
        resp = c.delete(f"/draft/sessions/{session_id}/picks")
        assert resp.status_code == 200
        assert resp.json()["current_pick"] == 1
        assert resp.json()["drafted_players"] == []

    def test_undo_with_no_picks_raises_400(self, client):
        c, db, session_id, dv1, dv2 = self._setup(client)
        resp = c.delete(f"/draft/sessions/{session_id}/picks")
        assert resp.status_code == 400

    def test_pick_removes_from_queue(self, client):
        c, db, session_id, dv1, dv2 = self._setup(client)
        c.post(f"/draft/sessions/{session_id}/queue", json={"dynasty_value_id": dv1.id})
        c.post(f"/draft/sessions/{session_id}/picks", json={"dynasty_value_id": dv1.id})
        resp = c.get(f"/draft/sessions/{session_id}")
        assert resp.json()["queued_players"] == []


# ---------------------------------------------------------------------------
# /draft/sessions/{id}/queue tests
# ---------------------------------------------------------------------------

class TestDraftQueue:
    def _setup(self, client):
        c, db = client
        session_resp = c.post("/draft/sessions", json={"num_teams": 4, "num_rounds": 2, "user_team_slot": 1})
        session_id = session_resp.json()["id"]
        dv1 = _make_dv(db, player_name="Queue Me", position="TE", overall_rank=5, value=7000)
        return c, db, session_id, dv1

    def test_add_to_queue(self, client):
        c, db, session_id, dv1 = self._setup(client)
        resp = c.post(f"/draft/sessions/{session_id}/queue", json={"dynasty_value_id": dv1.id})
        assert resp.status_code == 200
        assert len(resp.json()["queued_players"]) == 1
        assert resp.json()["queued_players"][0]["player_name"] == "Queue Me"

    def test_add_duplicate_to_queue_is_idempotent(self, client):
        c, db, session_id, dv1 = self._setup(client)
        c.post(f"/draft/sessions/{session_id}/queue", json={"dynasty_value_id": dv1.id})
        c.post(f"/draft/sessions/{session_id}/queue", json={"dynasty_value_id": dv1.id})
        resp = c.get(f"/draft/sessions/{session_id}")
        assert len(resp.json()["queued_players"]) == 1

    def test_remove_from_queue(self, client):
        c, db, session_id, dv1 = self._setup(client)
        c.post(f"/draft/sessions/{session_id}/queue", json={"dynasty_value_id": dv1.id})
        resp = c.delete(f"/draft/sessions/{session_id}/queue/{dv1.id}")
        assert resp.status_code == 200
        assert resp.json()["queued_players"] == []


# ---------------------------------------------------------------------------
# /draft/available tests
# ---------------------------------------------------------------------------

class TestAvailablePlayers:
    def test_returns_all_players_without_session(self, client):
        c, db = client
        _make_dv(db, player_name="Free Agent", position="WR", overall_rank=5, value=7000)
        _make_pick_dv(db, name="2025 1st")
        resp = c.get("/draft/available")
        assert resp.status_code == 200
        names = [p["player_name"] for p in resp.json()]
        assert "Free Agent" in names
        assert "2025 1st" not in names

    def test_excludes_drafted_players(self, client):
        c, db = client
        dv1 = _make_dv(db, player_name="Drafted", position="WR", overall_rank=1, value=9000)
        _make_dv(db, player_name="Available", position="RB", overall_rank=2, value=8000)
        session_resp = c.post("/draft/sessions", json={"num_teams": 4, "num_rounds": 2, "user_team_slot": 1})
        session_id = session_resp.json()["id"]
        c.post(f"/draft/sessions/{session_id}/picks", json={"dynasty_value_id": dv1.id})
        resp = c.get(f"/draft/available?session_id={session_id}")
        names = [p["player_name"] for p in resp.json()]
        assert "Drafted" not in names
        assert "Available" in names

    def test_position_filter(self, client):
        c, db = client
        _make_dv(db, player_name="WR Guy", position="WR", overall_rank=1, value=9000)
        _make_dv(db, player_name="RB Guy", position="RB", overall_rank=2, value=8000)
        resp = c.get("/draft/available?position=WR")
        names = [p["player_name"] for p in resp.json()]
        assert "WR Guy" in names
        assert "RB Guy" not in names

    def test_search_filter(self, client):
        c, db = client
        _make_dv(db, player_name="Justin Jefferson", position="WR", overall_rank=1, value=9500)
        _make_dv(db, player_name="Ja'Marr Chase", position="WR", overall_rank=2, value=9000)
        resp = c.get("/draft/available?q=Justin")
        names = [p["player_name"] for p in resp.json()]
        assert "Justin Jefferson" in names
        assert "Ja'Marr Chase" not in names


# ---------------------------------------------------------------------------
# Age-grade / position-tier unit tests
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_age_grade_rb(self):
        from main import _age_grade
        assert _age_grade("RB", 22.0) == "A"
        assert _age_grade("RB", 25.5) == "B"
        assert _age_grade("RB", 28.5) == "C"
        assert _age_grade("RB", 31.0) == "D"

    def test_age_grade_qb(self):
        from main import _age_grade
        assert _age_grade("QB", 25.0) == "A"
        assert _age_grade("QB", 30.0) == "B"
        assert _age_grade("QB", 32.0) == "C"
        assert _age_grade("QB", 35.0) == "D"

    def test_age_grade_none_returns_na(self):
        from main import _age_grade
        assert _age_grade("WR", None) == "N/A"

    def test_position_tier_boundaries(self):
        from main import _position_tier
        assert _position_tier(1) == "Tier 1"
        assert _position_tier(3) == "Tier 1"
        assert _position_tier(4) == "Tier 2"
        assert _position_tier(8) == "Tier 2"
        assert _position_tier(9) == "Tier 3"
        assert _position_tier(16) == "Tier 3"
        assert _position_tier(25) == "Tier 5"
        assert _position_tier(None) == "—"

    def test_snake_order_correctness(self):
        from main import _snake_pick_order
        picks = _snake_pick_order(num_teams=3, num_rounds=2)
        assert len(picks) == 6
        slots = [p["team_slot"] for p in picks]
        # R1: 1,2,3  R2: 3,2,1
        assert slots == [1, 2, 3, 3, 2, 1]
