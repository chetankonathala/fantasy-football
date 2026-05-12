"""FastAPI application — /search, /player/{id}, /compare, /dynasty/*, /draft/*, /leagues/*, /offseason/* routes."""
import json
import os
import time
import uuid
from typing import List, Optional

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.fantasy.db.base import get_session_factory
from src.fantasy.db.models import (
    DraftSession, DynastyProjection, DynastyValue, GameLine, HistoricalRookieComp,
    KeeperCost, Matchup, NFLDraftPick, OffseasonMove, Player, RookiePick,
    ScheduleStrength, TeamDepthChart, UserLeague, UserRosterPlayer,
)
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
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Clerk JWT auth
# ---------------------------------------------------------------------------

_JWKS_CACHE: dict = {"keys": [], "fetched_at": 0.0}
_JWKS_TTL = 3600  # re-fetch public keys at most once per hour


def _fetch_jwks(issuer: str) -> list:
    now = time.time()
    if _JWKS_CACHE["keys"] and (now - _JWKS_CACHE["fetched_at"]) < _JWKS_TTL:
        return _JWKS_CACHE["keys"]
    url = f"{issuer}/.well-known/jwks.json"
    resp = httpx.get(url, timeout=10)
    resp.raise_for_status()
    keys = resp.json()["keys"]
    _JWKS_CACHE.update({"keys": keys, "fetched_at": now})
    return keys


def _verify_clerk_token(token: str) -> str:
    """Verify a Clerk-issued JWT and return the user_id (sub claim)."""
    try:
        header = jwt.get_unverified_header(token)
        claims = jwt.get_unverified_claims(token)
        issuer = claims.get("iss", "")
        if not issuer:
            raise HTTPException(status_code=401, detail="Invalid token: missing issuer")
        keys = _fetch_jwks(issuer)
        kid = header.get("kid")
        key = next((k for k in keys if k.get("kid") == kid), None)
        if key is None:
            # Key not found — bust cache and retry once
            _JWKS_CACHE["fetched_at"] = 0.0
            keys = _fetch_jwks(issuer)
            key = next((k for k in keys if k.get("kid") == kid), None)
        if key is None:
            raise HTTPException(status_code=401, detail="Invalid token: signing key not found")
        payload = jwt.decode(token, key, algorithms=["RS256"], options={"verify_aud": False})
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing sub")
        return user_id
    except JWTError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}")


def get_current_user(authorization: Optional[str] = Header(default=None)) -> str:
    """FastAPI dependency — extract and verify Clerk JWT, return user_id."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header required")
    return _verify_clerk_token(authorization.split(" ", 1)[1])

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


# ---------------------------------------------------------------------------
# User Leagues & Custom Roster
# ---------------------------------------------------------------------------

class LeagueCreateRequest(BaseModel):
    name: str
    scoring_format: str = "ppr"
    num_teams: int = 12


class RosterAddRequest(BaseModel):
    player_id: int
    position_slot: str = "roster"


def _league_to_dict(league: UserLeague, roster_count: int = 0) -> dict:
    return {
        "id": league.id,
        "name": league.name,
        "scoring_format": league.scoring_format,
        "num_teams": league.num_teams,
        "draft_session_id": league.draft_session_id,
        "roster_count": roster_count,
        "created_at": league.created_at.isoformat() if league.created_at else None,
    }


@app.post("/leagues", status_code=201)
def create_league(
    body: LeagueCreateRequest,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.scoring_format not in ("ppr", "half_ppr", "standard"):
        raise HTTPException(status_code=422, detail="scoring_format must be ppr, half_ppr, or standard")
    if not (2 <= body.num_teams <= 20):
        raise HTTPException(status_code=422, detail="num_teams must be 2–20")
    league = UserLeague(
        user_id=user_id,
        name=body.name,
        scoring_format=body.scoring_format,
        num_teams=body.num_teams,
    )
    db.add(league)
    db.commit()
    db.refresh(league)
    return _league_to_dict(league)


@app.get("/leagues")
def list_leagues(
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    leagues = (
        db.query(UserLeague)
        .filter(UserLeague.user_id == user_id)
        .order_by(UserLeague.created_at.desc())
        .all()
    )
    result = []
    for league in leagues:
        count = db.query(UserRosterPlayer).filter(UserRosterPlayer.league_id == league.id).count()
        result.append(_league_to_dict(league, roster_count=count))
    return result


@app.get("/leagues/{league_id}")
def get_league(
    league_id: int,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    league = db.query(UserLeague).filter(
        UserLeague.id == league_id, UserLeague.user_id == user_id
    ).first()
    if not league:
        raise HTTPException(status_code=404, detail="League not found")

    entries = db.query(UserRosterPlayer).filter(UserRosterPlayer.league_id == league_id).all()
    _SLOT_ORDER = {"QB": 0, "RB": 1, "WR": 2, "TE": 3, "K": 4, "DST": 5}
    roster = []
    for entry in entries:
        try:
            rec = _build_recommendation(entry.player_id, league.scoring_format, db)
            rec["position_slot"] = entry.position_slot
            rec["roster_player_id"] = entry.id
            roster.append(rec)
        except HTTPException:
            pass
    roster.sort(key=lambda x: (_SLOT_ORDER.get(x.get("position", ""), 99), x.get("full_name", "")))

    return {**_league_to_dict(league, roster_count=len(roster)), "roster": roster}


@app.delete("/leagues/{league_id}", status_code=204)
def delete_league(
    league_id: int,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    league = db.query(UserLeague).filter(
        UserLeague.id == league_id, UserLeague.user_id == user_id
    ).first()
    if not league:
        raise HTTPException(status_code=404, detail="League not found")
    db.delete(league)
    db.commit()


@app.post("/leagues/{league_id}/roster", status_code=201)
def add_to_roster(
    league_id: int,
    body: RosterAddRequest,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    league = db.query(UserLeague).filter(
        UserLeague.id == league_id, UserLeague.user_id == user_id
    ).first()
    if not league:
        raise HTTPException(status_code=404, detail="League not found")
    player = db.query(Player).filter(Player.id == body.player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    existing = db.query(UserRosterPlayer).filter(
        UserRosterPlayer.league_id == league_id,
        UserRosterPlayer.player_id == body.player_id,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"{player.full_name} is already on this roster")
    entry = UserRosterPlayer(
        league_id=league_id,
        player_id=body.player_id,
        position_slot=body.position_slot,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {"id": entry.id, "player_id": entry.player_id, "position_slot": entry.position_slot}


@app.delete("/leagues/{league_id}/roster/{roster_player_id}", status_code=204)
def remove_from_roster(
    league_id: int,
    roster_player_id: int,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    league = db.query(UserLeague).filter(
        UserLeague.id == league_id, UserLeague.user_id == user_id
    ).first()
    if not league:
        raise HTTPException(status_code=404, detail="League not found")
    entry = db.query(UserRosterPlayer).filter(
        UserRosterPlayer.id == roster_player_id,
        UserRosterPlayer.league_id == league_id,
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Roster entry not found")
    db.delete(entry)
    db.commit()


@app.post("/leagues/{league_id}/roster/from-draft/{session_id}", status_code=201)
def import_roster_from_draft(
    league_id: int,
    session_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Import the user's picks from a dynasty draft session into their league roster."""
    league = db.query(UserLeague).filter(
        UserLeague.id == league_id, UserLeague.user_id == user_id
    ).first()
    if not league:
        raise HTTPException(status_code=404, detail="League not found")
    draft = db.query(DraftSession).filter(DraftSession.id == session_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft session not found")

    # Identify the user's picks by team slot
    drafted_ids: list[int] = json.loads(draft.drafted_ids)
    pick_order = _snake_pick_order(draft.num_teams, draft.num_rounds)
    user_pick_indices = {
        p["pick"] - 1 for p in pick_order if p["team_slot"] == draft.user_team_slot
    }
    user_dv_ids = [drafted_ids[i] for i in sorted(user_pick_indices) if i < len(drafted_ids)]

    added, skipped = [], []
    for dv_id in user_dv_ids:
        dv = db.query(DynastyValue).filter(DynastyValue.id == dv_id).first()
        if not dv or dv.is_pick:
            continue

        # Match dynasty name → Player table (exact → ilike → first+last)
        player = db.query(Player).filter(Player.full_name == dv.player_name).first()
        if not player:
            player = db.query(Player).filter(Player.full_name.ilike(dv.player_name)).first()
        if not player:
            parts = dv.player_name.split()
            if len(parts) >= 2:
                player = db.query(Player).filter(
                    Player.last_name.ilike(parts[-1]),
                    Player.first_name.ilike(parts[0]),
                ).first()
        if not player:
            skipped.append(dv.player_name)
            continue

        already = db.query(UserRosterPlayer).filter(
            UserRosterPlayer.league_id == league_id,
            UserRosterPlayer.player_id == player.id,
        ).first()
        if not already:
            db.add(UserRosterPlayer(league_id=league_id, player_id=player.id))
            added.append(player.full_name)

    league.draft_session_id = session_id
    db.commit()
    return {"added": added, "skipped": skipped, "added_count": len(added), "skipped_count": len(skipped)}


# ---------------------------------------------------------------------------
# My Team — ESPN Fantasy Integration
# ---------------------------------------------------------------------------

# Config: league + team identity (personal use — override via env vars)
_ESPN_LEAGUE_ID = int(os.environ.get("ESPN_LEAGUE_ID", "1805449289"))
_ESPN_TEAM_ID   = int(os.environ.get("ESPN_TEAM_ID",   "9"))
_ESPN_SEASON    = int(os.environ.get("ESPN_SEASON",    "2025"))

# Lineup slot ordering for display
_SLOT_ORDER = {"QB": 0, "RB": 1, "WR": 2, "TE": 3, "FLEX": 4, "K": 5, "D/ST": 6, "BE": 7, "IR": 8}


def _match_player_in_db(full_name: str, db: Session) -> Optional[Player]:
    """Find a DB player by exact name, then normalized ilike, then first+last name split."""
    p = db.query(Player).filter(Player.full_name == full_name).first()
    if p:
        return p
    normalized = full_name.replace("\u2019", "'").replace("\u2018", "'")
    p = db.query(Player).filter(Player.full_name.ilike(normalized)).first()
    if p:
        return p
    parts = full_name.split()
    if len(parts) >= 2:
        p = (
            db.query(Player)
            .filter(Player.last_name.ilike(parts[-1]), Player.first_name.ilike(parts[0]))
            .first()
        )
    return p


@app.get("/my-team")
def get_my_team(format: str = "ppr", db: Session = Depends(get_db)):
    """Return Chetan's DFK roster with start/sit recommendations per player."""
    from src.fantasy.fetch.espn import fetch_my_roster

    try:
        espn_data = fetch_my_roster(
            league_id=_ESPN_LEAGUE_ID,
            team_id=_ESPN_TEAM_ID,
            season=_ESPN_SEASON,
        )
    except EnvironmentError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"ESPN API error: {e}")

    roster = []
    for esp_player in espn_data["players"]:
        entry: dict = {
            "full_name": esp_player["full_name"],
            "position": esp_player["position"],
            "lineup_slot": esp_player["lineup_slot"],
            "is_bench": esp_player["is_bench"],
            "on_ir": esp_player["on_ir"],
            "espn_injury_status": esp_player["espn_injury_status"],
            "recommendation": None,
        }

        db_player = _match_player_in_db(esp_player["full_name"], db)
        if db_player is not None:
            try:
                rec = _build_recommendation(db_player.id, format, db)
                entry["recommendation"] = rec
            except HTTPException:
                pass

        roster.append(entry)

    roster.sort(key=lambda x: (_SLOT_ORDER.get(x["lineup_slot"], 99), x["full_name"]))

    return {
        "team_id": espn_data["team_id"],
        "record": f"{espn_data['wins']}-{espn_data['losses']}",
        "points_for": espn_data["points_for"],
        "league_id": _ESPN_LEAGUE_ID,
        "season": _ESPN_SEASON,
        "roster": roster,
    }


# ---------------------------------------------------------------------------
# Offseason Analysis Hub — /offseason/*
# ---------------------------------------------------------------------------


def _rookie_to_dict(r: RookiePick) -> dict:
    return {
        "id": r.id,
        "player_name": r.player_name,
        "position": r.position,
        "team": r.team,
        "college": r.college,
        "nfl_round": r.nfl_round,
        "nfl_pick": r.nfl_pick,
        "age": r.age,
        "dynasty_value": r.dynasty_value,
        "dynasty_overall_rank": r.dynasty_overall_rank,
        "dynasty_position_rank": r.dynasty_position_rank,
        "opportunity_grade": r.opportunity_grade,
        "opportunity_note": r.opportunity_note,
        "year1_projection": r.year1_projection,
        "sleeper_id": r.sleeper_id,
    }


def _move_to_dict(m: OffseasonMove) -> dict:
    return {
        "id": m.id,
        "player_name": m.player_name,
        "position": m.position,
        "from_team": m.from_team,
        "to_team": m.to_team,
        "move_type": m.move_type,
        "fantasy_impact": m.fantasy_impact,
        "impact_direction": m.impact_direction,
        "impact_note": m.impact_note,
        "dynasty_value": m.dynasty_value,
        "sleeper_id": m.sleeper_id,
    }


@app.get("/offseason/rookies")
def offseason_rookies(
    position: Optional[str] = None,
    grade: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """2026 rookie class with NFL draft slot, landing team, opportunity grade, and year-1 projection.

    Optional filters: position (QB/RB/WR/TE), grade (A/B/C/D).
    Sorted by dynasty_overall_rank ascending (best first), unranked last.
    """
    q = db.query(RookiePick)
    if position:
        q = q.filter(RookiePick.position == position.upper())
    if grade:
        q = q.filter(RookiePick.opportunity_grade == grade.upper())
    rows = q.order_by(
        RookiePick.dynasty_overall_rank.asc().nulls_last(),
        RookiePick.nfl_pick.asc().nulls_last(),
    ).limit(limit).all()
    return {"rookies": [_rookie_to_dict(r) for r in rows], "total": len(rows)}


@app.get("/offseason/moves")
def offseason_moves(
    position: Optional[str] = None,
    impact: Optional[str] = None,
    move_type: Optional[str] = None,
    team: Optional[str] = None,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    """Offseason transaction feed: free agent signings, trades, cuts.

    Optional filters: position, impact (high/medium/low), move_type, team (from or to).
    Sorted by dynasty_value desc (highest value players first).
    """
    q = db.query(OffseasonMove)
    if position:
        q = q.filter(OffseasonMove.position == position.upper())
    if impact:
        q = q.filter(OffseasonMove.fantasy_impact == impact.lower())
    if move_type:
        q = q.filter(OffseasonMove.move_type == move_type.lower())
    if team:
        team_upper = team.upper()
        q = q.filter(
            (OffseasonMove.from_team == team_upper) | (OffseasonMove.to_team == team_upper)
        )
    rows = q.order_by(
        OffseasonMove.dynasty_value.desc().nulls_last()
    ).limit(limit).all()
    return {"moves": [_move_to_dict(m) for m in rows], "total": len(rows)}


@app.get("/offseason/risers-fallers")
def offseason_risers_fallers(limit: int = 20, db: Session = Depends(get_db)):
    """Players whose dynasty value trended most sharply over the last 30 days.

    Returns separate risers (positive trend) and fallers (negative trend) lists,
    sorted by absolute trend magnitude. Excludes picks.
    """
    q = (
        db.query(DynastyValue)
        .filter(DynastyValue.is_pick == False, DynastyValue.trend_30day.isnot(None))  # noqa: E712
    )
    risers = (
        q.filter(DynastyValue.trend_30day > 0)
        .order_by(DynastyValue.trend_30day.desc())
        .limit(limit)
        .all()
    )
    fallers = (
        q.filter(DynastyValue.trend_30day < 0)
        .order_by(DynastyValue.trend_30day.asc())
        .limit(limit)
        .all()
    )

    def _fmt(dv: DynastyValue) -> dict:
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
            "sleeper_id": dv.sleeper_id,
        }

    return {
        "risers": [_fmt(r) for r in risers],
        "fallers": [_fmt(f) for f in fallers],
    }


@app.get("/offseason/cheat-sheet")
def offseason_cheat_sheet(
    scoring_format: str = "ppr",
    use_vbd: bool = True,
    db: Session = Depends(get_db),
):
    """Pre-draft cheat sheet with VBD (Value Based Drafting) tier breaks + scarcity scores.

    For each fantasy position, computes:
      - VBD = redraft_value − replacement_level (12-team PPR cutoffs)
      - tier (1..N) with auto-detected breaks at 2× median gap
      - is_tier_break flag for visual separators
      - position_scarcity 0-100 (how cliff-like top of position is)
    Rookies flagged with opportunity grade and year-1 projection.
    """
    from src.fantasy.vbd import VBDPlayer, compute_vbd, positional_scarcity

    players = (
        db.query(DynastyValue)
        .filter(DynastyValue.is_pick == False)  # noqa: E712
        .filter(DynastyValue.position.in_(["QB", "RB", "WR", "TE"]))
        .all()
    )

    # Build VBD inputs from redraft data
    vbd_inputs = [
        VBDPlayer(
            name=dv.player_name,
            position=dv.position,
            redraft_value=dv.redraft_value or 0,
            redraft_position_rank=dv.redraft_position_rank,
        )
        for dv in players
        if dv.redraft_value is not None
    ]
    vbd_map = compute_vbd(vbd_inputs) if use_vbd else {}
    scarcity = positional_scarcity(vbd_inputs) if use_vbd else {}

    rookie_rows = db.query(RookiePick).all()
    rookie_by_name: dict[str, RookiePick] = {r.player_name.lower(): r for r in rookie_rows}

    def _tier_label(pos_rank: Optional[int]) -> Optional[str]:
        if pos_rank is None:
            return None
        if pos_rank <= 3:
            return "elite"
        if pos_rank <= 8:
            return "tier1"
        if pos_rank <= 16:
            return "tier2"
        if pos_rank <= 24:
            return "tier3"
        return "depth"

    grouped: dict[str, list] = {}
    for dv in players:
        pos = dv.position or "Unknown"
        if pos not in grouped:
            grouped[pos] = []
        rookie = rookie_by_name.get(dv.player_name.lower())
        vbd_data = vbd_map.get(dv.player_name) or {}
        grouped[pos].append({
            "id": dv.id,
            "player_name": dv.player_name,
            "position": dv.position,
            "team": dv.team,
            "age": dv.age,
            "dynasty_value": dv.value,
            "dynasty_overall_rank": dv.overall_rank,
            "dynasty_position_rank": dv.position_rank,
            "redraft_value": dv.redraft_value,
            "redraft_overall_rank": dv.redraft_overall_rank,
            "redraft_position_rank": dv.redraft_position_rank,
            "trend_30day": dv.trend_30day,
            "vbd": vbd_data.get("vbd"),
            "tier": _tier_label(dv.redraft_position_rank or dv.position_rank),
            "vbd_tier": vbd_data.get("tier"),
            "is_tier_break": vbd_data.get("is_tier_break", False),
            "replacement_value": vbd_data.get("replacement_value"),
            "is_rookie": rookie is not None,
            "opportunity_grade": rookie.opportunity_grade if rookie else None,
            "year1_projection": rookie.year1_projection if rookie else None,
            "nfl_round": rookie.nfl_round if rookie else None,
            "nfl_pick": rookie.nfl_pick if rookie else None,
            "sleeper_id": dv.sleeper_id,
        })

    # Sort each position by VBD desc (or redraft_value if VBD disabled)
    for pos in grouped:
        grouped[pos].sort(
            key=lambda p: (-(p.get("vbd") or p.get("redraft_value") or 0))
        )

    position_order = ["QB", "RB", "WR", "TE"]
    ordered = {pos: grouped[pos] for pos in position_order if pos in grouped}
    for pos in grouped:
        if pos not in ordered:
            ordered[pos] = grouped[pos]

    return {
        "scoring_format": scoring_format,
        "use_vbd": use_vbd,
        "positions": ordered,
        "scarcity": scarcity,
    }


@app.get("/offseason/team/{team}")
def offseason_team_moves(team: str, db: Session = Depends(get_db)):
    """All offseason moves for a specific team (arrivals + departures) plus their rookies."""
    team_upper = team.upper()
    moves = (
        db.query(OffseasonMove)
        .filter(
            (OffseasonMove.from_team == team_upper) | (OffseasonMove.to_team == team_upper)
        )
        .order_by(OffseasonMove.dynasty_value.desc().nulls_last())
        .all()
    )
    rookies = (
        db.query(RookiePick)
        .filter(RookiePick.team == team_upper)
        .order_by(RookiePick.dynasty_overall_rank.asc().nulls_last())
        .all()
    )
    return {
        "team": team_upper,
        "arrivals": [_move_to_dict(m) for m in moves if m.to_team == team_upper],
        "departures": [_move_to_dict(m) for m in moves if m.from_team == team_upper],
        "draft_picks": [_rookie_to_dict(r) for r in rookies],
    }


# ---------------------------------------------------------------------------
# NFL Draft Board, Depth Charts, SOS — Phase 7 expansion endpoints
# ---------------------------------------------------------------------------


def _draft_pick_to_dict(p: NFLDraftPick) -> dict:
    return {
        "id": p.id,
        "draft_year": p.draft_year,
        "overall": p.overall,
        "round": p.round,
        "pick_in_round": p.pick_in_round,
        "player_name": p.player_name,
        "position": p.position,
        "college": p.college,
        "college_full": p.college_full,
        "nfl_team": p.nfl_team,
        "nfl_team_name": p.nfl_team_name,
        "nfl_team_logo": p.nfl_team_logo,
        "espn_athlete_id": p.espn_athlete_id,
        "traded": p.traded,
        "trade_note": p.trade_note,
        "headshot_url": p.headshot_url,
    }


@app.get("/offseason/draft-board")
def offseason_draft_board(
    year: int = 2026,
    round: Optional[int] = None,
    position: Optional[str] = None,
    team: Optional[str] = None,
    fantasy_only: bool = False,
    db: Session = Depends(get_db),
):
    """Full NFL Draft results for a year — all 257 picks chronologically.

    Filters: round (1-7), position, team (NFL abbreviation), fantasy_only (QB/RB/WR/TE).
    """
    q = db.query(NFLDraftPick).filter(NFLDraftPick.draft_year == year)
    if round is not None:
        q = q.filter(NFLDraftPick.round == round)
    if position:
        q = q.filter(NFLDraftPick.position == position.upper())
    if team:
        q = q.filter(NFLDraftPick.nfl_team == team.upper())
    if fantasy_only:
        q = q.filter(NFLDraftPick.position.in_(["QB", "RB", "WR", "TE"]))
    rows = q.order_by(NFLDraftPick.overall.asc()).all()
    return {
        "year": year,
        "total": len(rows),
        "picks": [_draft_pick_to_dict(p) for p in rows],
    }


@app.get("/offseason/draft-board/by-team/{team}")
def offseason_draft_board_by_team(team: str, year: int = 2026, db: Session = Depends(get_db)):
    """All of one team's draft picks for the year."""
    rows = (
        db.query(NFLDraftPick)
        .filter(NFLDraftPick.draft_year == year, NFLDraftPick.nfl_team == team.upper())
        .order_by(NFLDraftPick.overall.asc())
        .all()
    )
    return {
        "year": year,
        "team": team.upper(),
        "total_picks": len(rows),
        "picks": [_draft_pick_to_dict(p) for p in rows],
    }


@app.get("/offseason/depth-chart/{team}")
def offseason_depth_chart(team: str, season: int = 2026, db: Session = Depends(get_db)):
    """Team's fantasy depth chart by position (QB/RB/WR/TE), redraft-ordered."""
    rows = (
        db.query(TeamDepthChart)
        .filter(TeamDepthChart.team == team.upper(), TeamDepthChart.season == season)
        .order_by(TeamDepthChart.position, TeamDepthChart.depth_order)
        .all()
    )
    grouped: dict[str, list] = {}
    for r in rows:
        pos = r.position
        if pos not in grouped:
            grouped[pos] = []
        grouped[pos].append({
            "depth_order": r.depth_order,
            "player_name": r.player_name,
            "sleeper_id": r.sleeper_id,
            "age": r.age,
            "dynasty_value": r.dynasty_value,
            "dynasty_position_rank": r.dynasty_position_rank,
            "is_rookie": r.is_rookie,
        })
    return {"team": team.upper(), "season": season, "positions": grouped}


@app.get("/offseason/depth-chart")
def offseason_depth_chart_all(season: int = 2026, db: Session = Depends(get_db)):
    """All teams' depth charts grouped by team → position."""
    rows = (
        db.query(TeamDepthChart)
        .filter(TeamDepthChart.season == season)
        .order_by(TeamDepthChart.team, TeamDepthChart.position, TeamDepthChart.depth_order)
        .all()
    )
    out: dict[str, dict[str, list]] = {}
    for r in rows:
        out.setdefault(r.team, {}).setdefault(r.position, []).append({
            "depth_order": r.depth_order,
            "player_name": r.player_name,
            "sleeper_id": r.sleeper_id,
            "age": r.age,
            "dynasty_value": r.dynasty_value,
            "is_rookie": r.is_rookie,
        })
    return {"season": season, "teams": out}


@app.get("/offseason/sos")
def offseason_sos(season: int = 2026, position: Optional[str] = None, db: Session = Depends(get_db)):
    """Strength of Schedule by team and position.

    Score 0-100 (50=avg, higher=easier). Rank 1=easiest, 32=hardest.
    """
    q = db.query(ScheduleStrength).filter(ScheduleStrength.season == season)
    if position:
        q = q.filter(ScheduleStrength.position == position.upper())
    rows = q.order_by(ScheduleStrength.position, ScheduleStrength.sos_rank).all()
    grouped: dict[str, list] = {}
    for r in rows:
        grouped.setdefault(r.position, []).append({
            "team": r.team,
            "sos_score": round(r.sos_score, 1),
            "sos_rank": r.sos_rank,
            "avg_opp_pts_per_game": round(r.avg_opp_dvp_rank, 2) if r.avg_opp_dvp_rank else None,
            "games_counted": r.games_played,
        })
    return {"season": season, "positions": grouped}


@app.get("/offseason/projection/{player_name}")
def offseason_projection(player_name: str, base_year: int = 2026, db: Session = Depends(get_db)):
    """3-year dynasty trajectory for a player — current value + Y+1, Y+2, Y+3 projected."""
    rows = (
        db.query(DynastyProjection)
        .filter(
            DynastyProjection.player_name == player_name,
            DynastyProjection.base_year == base_year,
        )
        .order_by(DynastyProjection.projection_year)
        .all()
    )
    if not rows:
        raise HTTPException(status_code=404, detail=f"No projection for {player_name}")

    current = (
        db.query(DynastyValue)
        .filter(DynastyValue.player_name == player_name)
        .first()
    )

    return {
        "player_name": player_name,
        "position": rows[0].position,
        "current_age": current.age if current else None,
        "current_value": current.value if current else None,
        "current_overall_rank": current.overall_rank if current else None,
        "current_position_rank": current.position_rank if current else None,
        "sleeper_id": rows[0].sleeper_id,
        "base_year": base_year,
        "trajectory": [
            {
                "year_offset": r.projection_year,
                "year": base_year + r.projection_year,
                "projected_age": r.projected_age,
                "projected_value": r.projected_value,
                "decay_factor": r.decay_factor,
                "role_label": r.role_label,
            }
            for r in rows
        ],
    }


@app.get("/offseason/projections/leaderboard")
def offseason_projections_leaderboard(
    position: Optional[str] = None,
    direction: str = "ascending",
    limit: int = 25,
    db: Session = Depends(get_db),
):
    """Top players whose dynasty value is projected to GROW (ascending) or COLLAPSE (cliff).

    Direction: 'ascending' / 'cliff'. Useful for finding buy-low or sell-high targets.
    """
    if direction not in ("ascending", "cliff", "peak", "declining"):
        raise HTTPException(status_code=400, detail="direction must be ascending|cliff|peak|declining")
    q = db.query(DynastyProjection).filter(
        DynastyProjection.projection_year == 1,
        DynastyProjection.role_label == direction,
    )
    if position:
        q = q.filter(DynastyProjection.position == position.upper())
    rows = (
        q.order_by(
            DynastyProjection.projected_value.desc() if direction == "ascending"
            else DynastyProjection.projected_value.asc()
        )
        .limit(limit)
        .all()
    )
    return {
        "direction": direction,
        "position": position,
        "players": [
            {
                "player_name": r.player_name,
                "position": r.position,
                "projected_age": r.projected_age,
                "projected_value": r.projected_value,
                "decay_factor": r.decay_factor,
                "role_label": r.role_label,
            }
            for r in rows
        ],
    }


@app.get("/offseason/comps/{rookie_id}")
def offseason_rookie_comps(rookie_id: int, limit: int = 5, db: Session = Depends(get_db)):
    """Find historical rookies with similar draft profile to a current rookie.

    Match criteria: same position, draft round within ±1, pick number within ±30.
    Returns top N comps + a hit-label distribution across the full candidate pool.
    """
    rookie = db.query(RookiePick).filter_by(id=rookie_id).first()
    if not rookie:
        raise HTTPException(status_code=404, detail="Rookie not found")
    if not rookie.position:
        raise HTTPException(status_code=400, detail="Rookie has no position")

    q = db.query(HistoricalRookieComp).filter(HistoricalRookieComp.position == rookie.position)
    if rookie.nfl_round:
        q = q.filter(HistoricalRookieComp.nfl_round.between(rookie.nfl_round - 1, rookie.nfl_round + 1))
    if rookie.nfl_pick:
        q = q.filter(HistoricalRookieComp.nfl_pick.between(rookie.nfl_pick - 30, rookie.nfl_pick + 30))

    candidates = q.all()

    def _distance(c: HistoricalRookieComp) -> float:
        d = 0.0
        if rookie.nfl_pick and c.nfl_pick:
            d += abs(c.nfl_pick - rookie.nfl_pick)
        if rookie.nfl_round and c.nfl_round:
            d += abs(c.nfl_round - rookie.nfl_round) * 5
        if rookie.age and c.age_at_draft:
            d += abs(c.age_at_draft - rookie.age) * 3
        return d

    candidates.sort(key=_distance)
    top = candidates[:limit]

    hit_dist: dict[str, int] = {}
    for c in candidates:
        hit_dist[c.hit_label or "unknown"] = hit_dist.get(c.hit_label or "unknown", 0) + 1

    return {
        "rookie": {
            "id": rookie.id,
            "player_name": rookie.player_name,
            "position": rookie.position,
            "team": rookie.team,
            "nfl_round": rookie.nfl_round,
            "nfl_pick": rookie.nfl_pick,
        },
        "comps": [
            {
                "player_name": c.player_name,
                "season": c.season,
                "nfl_round": c.nfl_round,
                "nfl_pick": c.nfl_pick,
                "college": c.college,
                "nfl_team": c.nfl_team,
                "year1_ppr_points": c.year1_ppr_points,
                "year1_games": c.year1_games,
                "hit_label": c.hit_label,
                "match_distance": _distance(c),
            }
            for c in top
        ],
        "hit_distribution": hit_dist,
        "sample_size": len(candidates),
    }


@app.get("/offseason/roster-construction/{team}")
def offseason_roster_construction(team: str, season: int = 2026, db: Session = Depends(get_db)):
    """Per-team fantasy roster analysis.

    Returns:
      - target_share_allocation: WR/TE depth chart with redraft value % share
      - backfield_structure: RB depth chart classified as bellcow / committee / split
      - qb_situation: starter, age, dynasty trend
      - thin_positions: list of positions where the depth chart is shallow
      - net_offseason_moves: arrivals/departures summary
    """
    t = team.upper()
    depth_rows = (
        db.query(TeamDepthChart)
        .filter(TeamDepthChart.team == t, TeamDepthChart.season == season)
        .order_by(TeamDepthChart.position, TeamDepthChart.depth_order)
        .all()
    )
    by_pos: dict[str, list[TeamDepthChart]] = {}
    for r in depth_rows:
        by_pos.setdefault(r.position, []).append(r)

    # ── Target share allocation (WR + TE combined) ───────────────
    pass_catchers = (by_pos.get("WR") or []) + (by_pos.get("TE") or [])
    total_value = sum((p.dynasty_value or 0) for p in pass_catchers) or 1
    target_share = []
    for p in pass_catchers:
        share = round((p.dynasty_value or 0) / total_value * 100, 1)
        target_share.append({
            "player_name": p.player_name,
            "position": p.position,
            "depth_order": p.depth_order,
            "dynasty_value": p.dynasty_value,
            "is_rookie": p.is_rookie,
            "value_share_pct": share,
        })
    target_share.sort(key=lambda x: -x["value_share_pct"])

    # ── Backfield structure classification ────────────────────────
    rbs = by_pos.get("RB") or []
    backfield_label = "unknown"
    rb_top1 = rbs[0].dynasty_value if rbs else 0
    rb_top2 = rbs[1].dynasty_value if len(rbs) > 1 else 0
    if rbs:
        if rb_top1 and rb_top2 and rb_top2 / max(rb_top1, 1) >= 0.7:
            backfield_label = "split"
        elif rb_top1 and rb_top2 and rb_top2 / max(rb_top1, 1) >= 0.4:
            backfield_label = "committee"
        else:
            backfield_label = "bellcow"
    backfield = {
        "label": backfield_label,
        "lead_back": rbs[0].player_name if rbs else None,
        "lead_back_value": rb_top1,
        "rotation": [
            {
                "player_name": r.player_name,
                "depth_order": r.depth_order,
                "dynasty_value": r.dynasty_value,
                "is_rookie": r.is_rookie,
            }
            for r in rbs[:4]
        ],
    }

    # ── QB situation ──────────────────────────────────────────────
    qbs = by_pos.get("QB") or []
    qb_situation = None
    if qbs:
        starter = qbs[0]
        starter_dv = (
            db.query(DynastyValue).filter(DynastyValue.player_name == starter.player_name).first()
        )
        qb_situation = {
            "starter": starter.player_name,
            "age": starter.age,
            "dynasty_value": starter.dynasty_value,
            "trend_30day": starter_dv.trend_30day if starter_dv else None,
            "is_rookie": starter.is_rookie,
        }

    # ── Thin position detection ──────────────────────────────────
    thin = []
    if not qbs or (qbs[0].dynasty_value or 0) < 1500:
        thin.append({"position": "QB", "reason": "no high-value starter"})
    if len(rbs) < 2 or (rbs and (rbs[0].dynasty_value or 0) < 2000):
        thin.append({"position": "RB", "reason": "lacks bellcow / shallow depth"})
    wrs = by_pos.get("WR") or []
    if not wrs or (wrs[0].dynasty_value or 0) < 2500:
        thin.append({"position": "WR", "reason": "no clear WR1"})
    tes = by_pos.get("TE") or []
    if not tes or (tes[0].dynasty_value or 0) < 800:
        thin.append({"position": "TE", "reason": "no fantasy-relevant starter"})

    # ── Offseason moves summary ──────────────────────────────────
    moves = (
        db.query(OffseasonMove)
        .filter((OffseasonMove.from_team == t) | (OffseasonMove.to_team == t))
        .all()
    )
    arrivals = [m for m in moves if m.to_team == t]
    departures = [m for m in moves if m.from_team == t]
    rookies = (
        db.query(RookiePick).filter(RookiePick.team == t)
        .order_by(RookiePick.nfl_pick.asc().nulls_last())
        .all()
    )

    return {
        "team": t,
        "season": season,
        "target_share_allocation": target_share,
        "backfield_structure": backfield,
        "qb_situation": qb_situation,
        "thin_positions": thin,
        "net_offseason": {
            "arrivals_count": len(arrivals),
            "departures_count": len(departures),
            "rookies_count": len(rookies),
            "top_arrival": (
                {"player_name": arrivals[0].player_name, "position": arrivals[0].position}
                if arrivals else None
            ),
            "top_departure": (
                {"player_name": departures[0].player_name, "position": departures[0].position}
                if departures else None
            ),
            "top_rookie": (
                {"player_name": rookies[0].player_name, "position": rookies[0].position,
                 "nfl_pick": rookies[0].nfl_pick, "opportunity_grade": rookies[0].opportunity_grade}
                if rookies else None
            ),
        },
    }
