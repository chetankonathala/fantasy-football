"""FastAPI application — /search, /player/{id}, /compare, /dynasty/*, /draft/* routes."""
import json
import os
import uuid
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.fantasy.db.base import get_session_factory
from src.fantasy.db.models import DraftSession, DynastyValue, GameLine, KeeperCost, Matchup, Player
from src.fantasy.engine import (
    DSTSignals,
    KickerSignals,
    Recommendation,
    ScoringFormat,
    SkillSignals,
    score_player,
)

app = FastAPI(title="Fantasy Football API", version="1.0.0")

_cors_origins = ["http://localhost:3000"]
if os.environ.get("FRONTEND_URL"):
    _cors_origins.append(os.environ["FRONTEND_URL"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

SessionLocal = get_session_factory()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _build_recommendation(player_id: int, format: str, db: Session) -> dict:
    """Build recommendation payload for a single player. Raises HTTPException(404) if not found."""
    player = db.query(Player).filter(Player.id == player_id).first()
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")

    # Fetch matchup if linked
    matchup = None
    if player.matchup_id is not None:
        matchup = db.query(Matchup).filter(Matchup.id == player.matchup_id).first()

    matchup_rank = matchup.opponent_rank if matchup else None

    # Fetch game line (Vegas + weather) if matchup exists
    game_line = None
    if matchup is not None:
        team = player.team
        game_line = db.query(GameLine).filter(
            GameLine.week == matchup.week,
            (GameLine.home_team == team) | (GameLine.away_team == team),
        ).first()

    # Compute player's implied total (home or away)
    vegas_implied_total = None
    if game_line is not None:
        if player.team == game_line.home_team:
            vegas_implied_total = game_line.home_implied_total
        else:
            vegas_implied_total = game_line.away_implied_total

    # Build signals based on position
    position = player.position or ""
    scoring_fmt = ScoringFormat(format)

    if position in ("QB", "RB", "WR", "TE"):
        snap_pct_l4w = [
            player.week1_snap_pct,
            player.week2_snap_pct,
            player.week3_snap_pct,
            player.week4_snap_pct,
        ]
        if position in ("WR", "TE"):
            usage_share_l4w = [
                player.week1_target_share,
                player.week2_target_share,
                player.week3_target_share,
                player.week4_target_share,
            ]
        elif position == "RB":
            usage_share_l4w = [
                player.week1_carry_share,
                player.week2_carry_share,
                player.week3_carry_share,
                player.week4_carry_share,
            ]
        else:  # QB
            usage_share_l4w = [None, None, None, None]

        signals = SkillSignals(
            position=position,
            matchup_rank=matchup_rank,
            injury_status=player.injury_status or None,
            snap_pct_l4w=snap_pct_l4w,
            usage_share_l4w=usage_share_l4w,
            projected_points=None,
        )
    elif position == "K":
        signals = KickerSignals(matchup_rank=matchup_rank)
    else:
        # DST or unknown
        signals = DSTSignals(opponent_offense_rank=matchup_rank)

    rec: Recommendation = score_player(signals, scoring_fmt)

    return {
        "id": player.id,
        "verdict": rec.verdict.value,
        "score": rec.score,
        "reasons": rec.reasons,
        "low_confidence": rec.low_confidence,
        "scoring_format": rec.scoring_format.value,
        "full_name": player.full_name,
        "position": player.position,
        "team": player.team,
        "injury_status": player.injury_status,
        "practice_participation": player.practice_participation,
        "snap_pct_l4w": [
            player.week1_snap_pct,
            player.week2_snap_pct,
            player.week3_snap_pct,
            player.week4_snap_pct,
        ],
        "target_share_l4w": [
            player.week1_target_share,
            player.week2_target_share,
            player.week3_target_share,
            player.week4_target_share,
        ],
        "carry_share_l4w": [
            player.week1_carry_share,
            player.week2_carry_share,
            player.week3_carry_share,
            player.week4_carry_share,
        ],
        "updated_at": player.updated_at.isoformat() if player.updated_at is not None else None,
        "sleeper_id": player.sleeper_id,
        "vegas_implied_total": vegas_implied_total,
        "game_total": game_line.game_total if game_line else None,
        "weather_flag": game_line.weather_flag if game_line else False,
        "wind_mph": game_line.wind_mph if game_line else None,
        "precip_probability": game_line.precip_probability if game_line else None,
        "is_dome": game_line.is_dome if game_line else None,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/search")
def search_players(q: str, db: Session = Depends(get_db)):
    """Search players by name (case-insensitive substring match). Minimum 2 chars."""
    if len(q) < 2:
        return []
    players = db.query(Player).filter(Player.full_name.ilike(f"%{q}%")).limit(5).all()
    return [
        {
            "id": p.id,
            "full_name": p.full_name,
            "position": p.position,
            "team": p.team,
        }
        for p in players
    ]


@app.get("/player/{player_id}")
def get_player_recommendation(
    player_id: int,
    format: str = "ppr",
    db: Session = Depends(get_db),
):
    """Return a start/sit recommendation for a player with supporting signals."""
    return _build_recommendation(player_id, format, db)


@app.get("/spotlight")
def get_spotlight(format: str = "ppr", db: Session = Depends(get_db)):
    """Return the top-scored player per skill position for the home page spotlight."""
    result = {}
    for pos in ["QB", "RB", "WR", "TE"]:
        players = (
            db.query(Player)
            .filter(
                Player.team.isnot(None),
                Player.position == pos,
                Player.week1_snap_pct.isnot(None),
            )
            .limit(60)
            .all()
        )
        best = None
        for p in players:
            try:
                rec = _build_recommendation(p.id, format, db)
                if best is None or rec["score"] > best["score"]:
                    best = rec
            except HTTPException:
                continue
        if best:
            result[pos] = best
    return result


@app.get("/top-players")
def get_top_players(
    position: str = "ALL",
    limit: int = 12,
    format: str = "ppr",
    db: Session = Depends(get_db),
):
    """Return top N players by score for the home page leaderboard."""
    SKILL_POSITIONS = ["QB", "RB", "WR", "TE"]
    query = db.query(Player).filter(Player.team.isnot(None))
    if position != "ALL":
        query = query.filter(Player.position == position)
    else:
        query = query.filter(Player.position.in_(SKILL_POSITIONS))
    query = query.filter(Player.week1_snap_pct.isnot(None))
    players = query.limit(150).all()
    results = []
    for p in players:
        try:
            results.append(_build_recommendation(p.id, format, db))
        except HTTPException:
            continue
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]


# ---------------------------------------------------------------------------
# Dynasty Trade Analyzer routes
# ---------------------------------------------------------------------------

class TradeRequest(BaseModel):
    side_a: List[int]  # dynasty_value IDs — what YOU receive
    side_b: List[int]  # dynasty_value IDs — what YOU give


def _dynasty_item(dv: DynastyValue) -> dict:
    return {
        "id": dv.id,
        "player_name": dv.player_name,
        "position": dv.position,
        "team": dv.team,
        "age": dv.age,
        "value": dv.value,
        "overall_rank": dv.overall_rank,
        "position_rank": dv.position_rank,
        "trend_30day": dv.trend_30day,
        "is_pick": dv.is_pick,
        "sleeper_id": dv.sleeper_id,
    }


def _analyze_trade(side_a: list[dict], side_b: list[dict]) -> dict:
    total_a = sum(item["value"] for item in side_a)
    total_b = sum(item["value"] for item in side_b)
    combined = total_a + total_b

    if combined == 0:
        differential_pct = 0.0
        verdict = "FAIR"
    else:
        differential_pct = (total_a - total_b) / combined * 100
        if differential_pct > 12:
            verdict = "WIN"
        elif differential_pct < -12:
            verdict = "LOSE"
        else:
            verdict = "FAIR"

    reasons = []
    if verdict == "WIN":
        reasons.append(
            f"You gain {differential_pct:.0f}% more value — you receive {total_a:,} pts vs. giving {total_b:,} pts."
        )
    elif verdict == "LOSE":
        reasons.append(
            f"You give up {abs(differential_pct):.0f}% more value than you receive ({total_b:,} pts vs. {total_a:,} pts)."
        )
    else:
        reasons.append(
            f"Roughly even exchange — you receive {total_a:,} pts vs. {total_b:,} pts ({abs(differential_pct):.1f}% gap)."
        )

    if side_a:
        best_in = max(side_a, key=lambda x: x["value"])
        rank_str = f"#{best_in['overall_rank']} overall" if best_in.get("overall_rank") else ""
        reasons.append(
            f"Best asset you receive: {best_in['player_name']} ({best_in['value']:,} pts{', ' + rank_str if rank_str else ''})."
        )
    if side_b:
        best_out = max(side_b, key=lambda x: x["value"])
        rank_str = f"#{best_out['overall_rank']} overall" if best_out.get("overall_rank") else ""
        reasons.append(
            f"Best asset you give: {best_out['player_name']} ({best_out['value']:,} pts{', ' + rank_str if rank_str else ''})."
        )

    picks_in = [x for x in side_a if x["is_pick"]]
    picks_out = [x for x in side_b if x["is_pick"]]
    if picks_in or picks_out:
        pick_val_in = sum(p["value"] for p in picks_in)
        pick_val_out = sum(p["value"] for p in picks_out)
        if pick_val_in > pick_val_out:
            reasons.append(f"You gain the pick capital edge ({pick_val_in:,} pts in picks vs. {pick_val_out:,} pts).")
        elif pick_val_out > pick_val_in:
            reasons.append(f"You give away the pick capital edge ({pick_val_out:,} pts in picks vs. {pick_val_in:,} pts).")

    return {
        "verdict": verdict,
        "side_a_total": total_a,
        "side_b_total": total_b,
        "differential_pct": round(differential_pct, 1),
        "reasons": reasons,
    }


@app.get("/dynasty/search")
def dynasty_search(q: str, db: Session = Depends(get_db)):
    """Search dynasty values by player/pick name. Minimum 2 chars."""
    if len(q) < 2:
        return []
    rows = (
        db.query(DynastyValue)
        .filter(DynastyValue.player_name.ilike(f"%{q}%"))
        .order_by(DynastyValue.overall_rank)
        .limit(8)
        .all()
    )
    return [_dynasty_item(r) for r in rows]


@app.post("/dynasty/trade")
def analyze_trade(body: TradeRequest, db: Session = Depends(get_db)):
    """Analyze a dynasty trade. side_a = what you receive, side_b = what you give."""
    if not body.side_a and not body.side_b:
        raise HTTPException(status_code=400, detail="Trade must have at least one item on each side.")

    def fetch_items(ids: List[int]) -> list[dict]:
        rows = db.query(DynastyValue).filter(DynastyValue.id.in_(ids)).all()
        id_map = {r.id: _dynasty_item(r) for r in rows}
        missing = [i for i in ids if i not in id_map]
        if missing:
            raise HTTPException(status_code=404, detail=f"Dynasty value IDs not found: {missing}")
        return [id_map[i] for i in ids]

    side_a_items = fetch_items(body.side_a)
    side_b_items = fetch_items(body.side_b)
    analysis = _analyze_trade(side_a_items, side_b_items)
    return {**analysis, "side_a_items": side_a_items, "side_b_items": side_b_items}


@app.get("/compare")
def compare_players(a: int, b: int, format: str = "ppr", db: Session = Depends(get_db)):
    """Return side-by-side recommendations for two players."""
    # Validate both exist before building either (no partial comparisons)
    player_a = db.query(Player).filter(Player.id == a).first()
    player_b = db.query(Player).filter(Player.id == b).first()
    if player_a is None or player_b is None:
        missing = []
        if player_a is None:
            missing.append(str(a))
        if player_b is None:
            missing.append(str(b))
        raise HTTPException(status_code=404, detail=f"Player(s) not found: {', '.join(missing)}")
    rec_a = _build_recommendation(a, format, db)
    rec_b = _build_recommendation(b, format, db)
    return {"player_a": rec_a, "player_b": rec_b}


# ---------------------------------------------------------------------------
# Dynasty Draft Room — helpers
# ---------------------------------------------------------------------------

# Age-curve grade by position (dynasty value peaks differ by position)
_AGE_GRADE_THRESHOLDS: dict[str, list[tuple[float, str]]] = {
    "RB": [(24.0, "A"), (27.0, "B"), (29.0, "C"), (99.0, "D")],
    "WR": [(25.0, "A"), (28.0, "B"), (30.0, "C"), (99.0, "D")],
    "TE": [(26.0, "A"), (29.0, "B"), (31.0, "C"), (99.0, "D")],
    "QB": [(27.0, "A"), (31.0, "B"), (33.0, "C"), (99.0, "D")],
}
_AGE_GRADE_DEFAULT: list[tuple[float, str]] = [(26.0, "A"), (29.0, "B"), (32.0, "C"), (99.0, "D")]


def _age_grade(position: Optional[str], age: Optional[float]) -> str:
    if age is None:
        return "N/A"
    thresholds = _AGE_GRADE_THRESHOLDS.get(position or "", _AGE_GRADE_DEFAULT)
    for cutoff, grade in thresholds:
        if age <= cutoff:
            return grade
    return "D"


def _position_tier(position_rank: Optional[int]) -> str:
    if position_rank is None:
        return "—"
    if position_rank <= 3:
        return "Tier 1"
    if position_rank <= 8:
        return "Tier 2"
    if position_rank <= 16:
        return "Tier 3"
    if position_rank <= 24:
        return "Tier 4"
    return "Tier 5"


def _rookie_ceiling(overall_rank: Optional[int], position: Optional[str]) -> str:
    """Derive dynasty ceiling label from overall rank."""
    if overall_rank is None:
        return "Unknown"
    if overall_rank <= 12:
        return "Elite"
    if overall_rank <= 36:
        return "High"
    if overall_rank <= 72:
        return "Mid"
    return "Low"


def _rookie_floor(overall_rank: Optional[int], position: Optional[str]) -> str:
    """Derive dynasty floor label — RBs/WRs are more volatile than QBs/TEs."""
    volatile = position in ("RB", "WR")
    if overall_rank is None:
        return "Unknown"
    if overall_rank <= 12:
        return "High" if volatile else "Elite"
    if overall_rank <= 36:
        return "Mid" if volatile else "High"
    if overall_rank <= 72:
        return "Low" if volatile else "Mid"
    return "Low"


def _landing_assessment(position_rank: Optional[int], team: Optional[str]) -> str:
    team_str = f" ({team})" if team else ""
    if position_rank is None:
        return f"Unranked{team_str}"
    if position_rank <= 3:
        return f"Featured Starter{team_str}"
    if position_rank <= 8:
        return f"Starter{team_str}"
    if position_rank <= 16:
        return f"Target{team_str}"
    return f"Depth Chart{team_str}"


def _dynasty_item_full(dv: DynastyValue) -> dict:
    return {
        "id": dv.id,
        "player_name": dv.player_name,
        "position": dv.position,
        "team": dv.team,
        "age": dv.age,
        "value": dv.value,
        "overall_rank": dv.overall_rank,
        "position_rank": dv.position_rank,
        "trend_30day": dv.trend_30day,
        "is_pick": dv.is_pick,
        "sleeper_id": dv.sleeper_id,
        "age_grade": _age_grade(dv.position, dv.age),
        "position_tier": _position_tier(dv.position_rank),
    }


def _snake_pick_order(num_teams: int, num_rounds: int) -> list[dict]:
    """Return list of {pick, round, pick_in_round, team_slot} for a snake draft."""
    picks = []
    overall = 1
    for r in range(1, num_rounds + 1):
        slots = list(range(1, num_teams + 1))
        if r % 2 == 0:
            slots = list(reversed(slots))
        for slot in slots:
            picks.append({"pick": overall, "round": r, "pick_in_round": slots.index(slot) + 1, "team_slot": slot})
            overall += 1
    return picks


def _session_to_dict(session: DraftSession, db: Session) -> dict:
    drafted_ids: list[int] = json.loads(session.drafted_ids)
    queued_ids: list[int] = json.loads(session.queued_ids)

    drafted_players = []
    for did in drafted_ids:
        dv = db.query(DynastyValue).filter(DynastyValue.id == did).first()
        drafted_players.append(_dynasty_item_full(dv) if dv else {"id": did, "player_name": "Unknown"})

    queued_players = []
    for qid in queued_ids:
        dv = db.query(DynastyValue).filter(DynastyValue.id == qid).first()
        if dv:
            queued_players.append(_dynasty_item_full(dv))

    pick_order = _snake_pick_order(session.num_teams, session.num_rounds)
    user_picks = [p for p in pick_order if p["team_slot"] == session.user_team_slot]

    return {
        "id": session.id,
        "num_teams": session.num_teams,
        "num_rounds": session.num_rounds,
        "user_team_slot": session.user_team_slot,
        "total_picks": len(pick_order),
        "current_pick": len(drafted_ids) + 1,
        "drafted_players": drafted_players,
        "queued_players": queued_players,
        "pick_order": pick_order,
        "user_picks": user_picks,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
    }


# ---------------------------------------------------------------------------
# Dynasty Draft Room — rankings endpoints
# ---------------------------------------------------------------------------

@app.get("/dynasty/rankings")
def dynasty_rankings(
    position: str = "ALL",
    limit: int = 200,
    db: Session = Depends(get_db),
):
    """Full dynasty rankings with age-curve grade and position tier."""
    query = db.query(DynastyValue).filter(DynastyValue.is_pick == False)  # noqa: E712
    if position != "ALL":
        query = query.filter(DynastyValue.position == position)
    rows = query.order_by(DynastyValue.overall_rank).limit(limit).all()
    return [_dynasty_item_full(r) for r in rows]


@app.get("/dynasty/rookies")
def dynasty_rookies(limit: int = 100, db: Session = Depends(get_db)):
    """Rookie class rankings: players age ≤ 23, enriched with ceiling/floor/landing grades."""
    rows = (
        db.query(DynastyValue)
        .filter(
            DynastyValue.is_pick == False,  # noqa: E712
            DynastyValue.age.isnot(None),
            DynastyValue.age <= 23.0,
        )
        .order_by(DynastyValue.overall_rank)
        .limit(limit)
        .all()
    )
    result = []
    for r in rows:
        item = _dynasty_item_full(r)
        item["ceiling"] = _rookie_ceiling(r.overall_rank, r.position)
        item["floor"] = _rookie_floor(r.overall_rank, r.position)
        item["landing_assessment"] = _landing_assessment(r.position_rank, r.team)
        result.append(item)
    return result


# ---------------------------------------------------------------------------
# Dynasty Draft Room — keeper endpoints
# ---------------------------------------------------------------------------

class KeeperUpsertRequest(BaseModel):
    player_name: str
    dynasty_value_id: Optional[int] = None
    keeper_round: int
    notes: Optional[str] = None


@app.get("/dynasty/keepers")
def list_keepers(db: Session = Depends(get_db)):
    """Return all keeper costs with dynasty value side-by-side."""
    keepers = db.query(KeeperCost).order_by(KeeperCost.keeper_round).all()
    result = []
    for k in keepers:
        dv = None
        if k.dynasty_value_id:
            dv = db.query(DynastyValue).filter(DynastyValue.id == k.dynasty_value_id).first()
        if dv is None:
            dv = db.query(DynastyValue).filter(DynastyValue.player_name.ilike(k.player_name)).first()

        dynasty_value = dv.value if dv else None
        dynasty_rank = dv.overall_rank if dv else None
        position = dv.position if dv else None
        age = dv.age if dv else None
        sleeper_id = dv.sleeper_id if dv else None

        # Pick value heuristic: round 1 ≈ 8000pts, round 2 ≈ 5500, round 3 ≈ 3500, etc.
        _round_pick_values = {1: 8000, 2: 5500, 3: 3500, 4: 2200, 5: 1400, 6: 900, 7: 600}
        keeper_cost_value = _round_pick_values.get(k.keeper_round, max(300, 600 - (k.keeper_round - 7) * 100))

        net_gain = (dynasty_value - keeper_cost_value) if dynasty_value is not None else None
        recommendation = None
        if net_gain is not None:
            if net_gain >= 1000:
                recommendation = "KEEP"
            elif net_gain <= -500:
                recommendation = "CUT"
            else:
                recommendation = "BORDERLINE"

        result.append({
            "id": k.id,
            "player_name": k.player_name,
            "dynasty_value_id": k.dynasty_value_id or (dv.id if dv else None),
            "keeper_round": k.keeper_round,
            "notes": k.notes,
            "dynasty_value": dynasty_value,
            "dynasty_rank": dynasty_rank,
            "keeper_cost_value": keeper_cost_value,
            "net_gain": net_gain,
            "recommendation": recommendation,
            "position": position,
            "age": age,
            "sleeper_id": sleeper_id,
            "age_grade": _age_grade(position, age),
        })
    return result


@app.post("/dynasty/keepers", status_code=201)
def upsert_keeper(body: KeeperUpsertRequest, db: Session = Depends(get_db)):
    """Create or update a keeper cost entry."""
    if body.keeper_round < 1 or body.keeper_round > 20:
        raise HTTPException(status_code=422, detail="keeper_round must be 1-20")

    existing = db.query(KeeperCost).filter(KeeperCost.player_name.ilike(body.player_name)).first()
    if existing:
        existing.keeper_round = body.keeper_round
        existing.notes = body.notes
        if body.dynasty_value_id:
            existing.dynasty_value_id = body.dynasty_value_id
        db.commit()
        db.refresh(existing)
        return {"id": existing.id, "player_name": existing.player_name, "keeper_round": existing.keeper_round}

    new_keeper = KeeperCost(
        player_name=body.player_name,
        dynasty_value_id=body.dynasty_value_id,
        keeper_round=body.keeper_round,
        notes=body.notes,
    )
    db.add(new_keeper)
    db.commit()
    db.refresh(new_keeper)
    return {"id": new_keeper.id, "player_name": new_keeper.player_name, "keeper_round": new_keeper.keeper_round}


@app.delete("/dynasty/keepers/{keeper_id}", status_code=204)
def delete_keeper(keeper_id: int, db: Session = Depends(get_db)):
    """Remove a keeper cost entry."""
    keeper = db.query(KeeperCost).filter(KeeperCost.id == keeper_id).first()
    if keeper is None:
        raise HTTPException(status_code=404, detail="Keeper not found")
    db.delete(keeper)
    db.commit()


# ---------------------------------------------------------------------------
# Dynasty Draft Room — draft session endpoints
# ---------------------------------------------------------------------------

class DraftSessionCreateRequest(BaseModel):
    num_teams: int
    num_rounds: int
    user_team_slot: int


class DraftPickRequest(BaseModel):
    dynasty_value_id: int


class QueueRequest(BaseModel):
    dynasty_value_id: int


@app.post("/draft/sessions", status_code=201)
def create_draft_session(body: DraftSessionCreateRequest, db: Session = Depends(get_db)):
    """Create a new snake draft session."""
    if not (2 <= body.num_teams <= 20):
        raise HTTPException(status_code=422, detail="num_teams must be 2-20")
    if not (1 <= body.num_rounds <= 30):
        raise HTTPException(status_code=422, detail="num_rounds must be 1-30")
    if not (1 <= body.user_team_slot <= body.num_teams):
        raise HTTPException(status_code=422, detail="user_team_slot must be 1-num_teams")

    session = DraftSession(
        id=str(uuid.uuid4()),
        num_teams=body.num_teams,
        num_rounds=body.num_rounds,
        user_team_slot=body.user_team_slot,
        drafted_ids="[]",
        queued_ids="[]",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return _session_to_dict(session, db)


@app.get("/draft/sessions")
def list_draft_sessions(db: Session = Depends(get_db)):
    """List all draft sessions, newest first."""
    sessions = db.query(DraftSession).order_by(DraftSession.created_at.desc()).limit(10).all()
    return [
        {
            "id": s.id,
            "num_teams": s.num_teams,
            "num_rounds": s.num_rounds,
            "user_team_slot": s.user_team_slot,
            "picks_made": len(json.loads(s.drafted_ids)),
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in sessions
    ]


@app.get("/draft/sessions/{session_id}")
def get_draft_session(session_id: str, db: Session = Depends(get_db)):
    """Get full draft session state."""
    session = db.query(DraftSession).filter(DraftSession.id == session_id).first()
    if session is None:
        raise HTTPException(status_code=404, detail="Draft session not found")
    return _session_to_dict(session, db)


@app.post("/draft/sessions/{session_id}/picks")
def make_pick(session_id: str, body: DraftPickRequest, db: Session = Depends(get_db)):
    """Mark the next pick in the draft."""
    session = db.query(DraftSession).filter(DraftSession.id == session_id).first()
    if session is None:
        raise HTTPException(status_code=404, detail="Draft session not found")

    dv = db.query(DynastyValue).filter(DynastyValue.id == body.dynasty_value_id).first()
    if dv is None:
        raise HTTPException(status_code=404, detail="Player not found in dynasty values")

    drafted_ids: list[int] = json.loads(session.drafted_ids)
    total_picks = session.num_teams * session.num_rounds
    if len(drafted_ids) >= total_picks:
        raise HTTPException(status_code=400, detail="Draft is complete — all picks have been made")

    if body.dynasty_value_id in drafted_ids:
        raise HTTPException(status_code=409, detail=f"{dv.player_name} has already been drafted")

    drafted_ids.append(body.dynasty_value_id)
    session.drafted_ids = json.dumps(drafted_ids)

    # Auto-remove from queue if present
    queued_ids: list[int] = json.loads(session.queued_ids)
    if body.dynasty_value_id in queued_ids:
        queued_ids.remove(body.dynasty_value_id)
        session.queued_ids = json.dumps(queued_ids)

    db.commit()
    db.refresh(session)
    return _session_to_dict(session, db)


@app.delete("/draft/sessions/{session_id}/picks")
def undo_last_pick(session_id: str, db: Session = Depends(get_db)):
    """Undo the most recent pick."""
    session = db.query(DraftSession).filter(DraftSession.id == session_id).first()
    if session is None:
        raise HTTPException(status_code=404, detail="Draft session not found")

    drafted_ids: list[int] = json.loads(session.drafted_ids)
    if not drafted_ids:
        raise HTTPException(status_code=400, detail="No picks to undo")

    drafted_ids.pop()
    session.drafted_ids = json.dumps(drafted_ids)
    db.commit()
    db.refresh(session)
    return _session_to_dict(session, db)


@app.post("/draft/sessions/{session_id}/queue")
def add_to_queue(session_id: str, body: QueueRequest, db: Session = Depends(get_db)):
    """Add a player to the user's draft queue."""
    session = db.query(DraftSession).filter(DraftSession.id == session_id).first()
    if session is None:
        raise HTTPException(status_code=404, detail="Draft session not found")

    dv = db.query(DynastyValue).filter(DynastyValue.id == body.dynasty_value_id).first()
    if dv is None:
        raise HTTPException(status_code=404, detail="Player not found in dynasty values")

    queued_ids: list[int] = json.loads(session.queued_ids)
    if body.dynasty_value_id not in queued_ids:
        queued_ids.append(body.dynasty_value_id)
        session.queued_ids = json.dumps(queued_ids)
        db.commit()

    db.refresh(session)
    return _session_to_dict(session, db)


@app.delete("/draft/sessions/{session_id}/queue/{dynasty_value_id}")
def remove_from_queue(session_id: str, dynasty_value_id: int, db: Session = Depends(get_db)):
    """Remove a player from the user's draft queue."""
    session = db.query(DraftSession).filter(DraftSession.id == session_id).first()
    if session is None:
        raise HTTPException(status_code=404, detail="Draft session not found")

    queued_ids: list[int] = json.loads(session.queued_ids)
    if dynasty_value_id in queued_ids:
        queued_ids.remove(dynasty_value_id)
        session.queued_ids = json.dumps(queued_ids)
        db.commit()

    db.refresh(session)
    return _session_to_dict(session, db)


@app.get("/draft/available")
def get_available_players(
    session_id: Optional[str] = None,
    position: str = "ALL",
    q: str = "",
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """Return available (un-drafted) players sorted by dynasty rank."""
    drafted_ids: list[int] = []
    if session_id:
        session = db.query(DraftSession).filter(DraftSession.id == session_id).first()
        if session:
            drafted_ids = json.loads(session.drafted_ids)

    query = db.query(DynastyValue).filter(DynastyValue.is_pick == False)  # noqa: E712
    if drafted_ids:
        query = query.filter(DynastyValue.id.notin_(drafted_ids))
    if position != "ALL":
        query = query.filter(DynastyValue.position == position)
    if q:
        query = query.filter(DynastyValue.player_name.ilike(f"%{q}%"))

    rows = query.order_by(DynastyValue.overall_rank).limit(limit).all()
    return [_dynasty_item_full(r) for r in rows]
