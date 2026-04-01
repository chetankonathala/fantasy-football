"""FastAPI application — /search, /player/{id}, and /compare routes for fantasy football recommendations."""
import os

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from src.fantasy.db.base import get_session_factory
from src.fantasy.db.models import GameLine, Matchup, Player
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
    allow_methods=["GET"],
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
