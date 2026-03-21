# Phase 1: Data Foundation - Research

**Researched:** 2026-03-21
**Domain:** Python data pipeline — Sleeper API, nflreadpy/nflverse, SQLite, SQLAlchemy, Alembic, cron scheduling
**Confidence:** HIGH (stack is locked in CONTEXT.md; verified versions against PyPI and official docs)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Language: Python (nflreadpy/nflverse are Python-native — no bridging layer needed)
- Web framework: FastAPI (async, auto-generates OpenAPI docs, standard pairing for Phase 3)
- Dependency management: uv + pyproject.toml
- Frontend (for Phase 3 planning alignment): Next.js (React)
- Database: SQLite (`/data/fantasy.db`) — zero-ops, single file, sufficient for ~2000 active NFL players
- ORM: SQLAlchemy ORM
- Migrations: Alembic (versioned schema changes across phases)
- Refresh strategy: Upsert by canonical player ID (INSERT OR REPLACE / ON CONFLICT DO UPDATE) — never full wipe
- History: Current snapshot only — no historical row retention (historical tracking is v2 scope per HIST-01/HIST-02)
- DB file lives in a separate `/data/` directory, gitignored
- Mechanism: System cron job calling a standalone Python script (`scripts/refresh.py`)
- Failure handling: Log error, retain last good data — next scheduled run retries automatically
- Off-season behavior: Cron always fires; fetch logic checks if NFL season is active and returns early with a "season not active" flag
- Logging: `logs/refresh.log` with rotation (7-day retention)
- Player table stores both `nflverse_id` (canonical) and `sleeper_id` — crosswalk run once at setup, both IDs available for lookups
- Usage stats (snap %, target share, carry share) stored as 4 explicit week columns per stat: `week1_snap_pct`, `week2_snap_pct`, `week3_snap_pct`, `week4_snap_pct` (and equivalents for target/carry share)
- Matchup data (DVP grade, opponent rank by position) lives in a separate `matchup` table: `(week, team, position, opponent_rank, dvp_score)` — player table holds a foreign key to current week matchup; avoids duplicating matchup data per player
- Off-season state: app-level check via date logic against NFL season schedule — no DB flag
- Player ID joins MUST use nflverse ff_playerids crosswalk — never join on player name strings
- DVP matchup grades computed from nflreadpy play-by-play (points allowed by position, last 4 weeks) — not scraped from FantasyPros or another external grade source
- nflreadpy must be pinned to v0.1.5 (experimental package — pre-condition from STATE.md)

### Claude's Discretion
- Exact table column names and types beyond the patterns above
- Precise DVP score computation formula (points allowed vs. position, last 4 weeks from nflreadpy)
- nflreadpy version pinning and schema validation approach (pre-condition: pin to v0.1.5, validate play-by-play schema before committing)
- Exact cron schedule expression
- Log rotation implementation details

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DATA-01 | Injury / practice status refreshes automatically throughout the week (not just once on Monday) | Sleeper API `/v1/players/nfl` endpoint returns `injury_status`, `practice_participation`, `status`, `injury_start_date`; no auth required; cron + refresh script architecture delivers this |
| DATA-03 | App shows a clear "season not active" state during the NFL off-season rather than stale data | nflreadpy `get_current_season()` and `get_current_week()` utilities detect off-season; early-return pattern in `scripts/refresh.py` with a logged flag covers this |
</phase_requirements>

---

## Summary

Phase 1 establishes the entire data layer from scratch: two external data sources (Sleeper API for player/injury metadata, nflreadpy for stats/usage/matchup data), a SQLite database with two tables (player and matchup), and a cron-driven refresh script. The stack is entirely pre-decided in CONTEXT.md — research focuses on the exact APIs, column names, patterns, and pitfalls within those choices.

The Sleeper API is a free, auth-free REST API. Its player endpoint returns ~5MB of JSON and must be cached locally rather than called on every read. Key injury fields are `injury_status`, `practice_participation`, `status`, and `injury_start_date`. nflreadpy v0.1.5 (the latest stable release, confirmed on PyPI as of 2026-03-21) provides `load_player_stats()` for weekly target_share and carries, `load_snap_counts()` for offense snap percentage, `load_pbp()` for DVP calculations, and `load_ff_playerids()` for the canonical crosswalk that bridges nflverse IDs to Sleeper IDs. nflreadpy uses Polars DataFrames by default; conversion to pandas is optional. The package carries an "experimental" lifecycle badge and is itself noted to have been largely written by Claude — the precaution to pin to v0.1.5 and validate schema before committing is well-founded.

SQLAlchemy 2.0 (latest: 2.0.48) with SQLite supports upsert via `from sqlalchemy.dialects.sqlite import insert` with `.on_conflict_do_update()`. Alembic 1.18.4 handles versioned migrations and requires `render_as_batch=True` in env.py for SQLite ALTER TABLE operations. Python's built-in `TimedRotatingFileHandler` with `when='midnight'` and `backupCount=7` delivers the required 7-day log rotation without additional dependencies.

**Primary recommendation:** Build the data pipeline as three clearly separated concerns — (1) fetch layer (Sleeper API client, nflreadpy wrapper), (2) normalization layer (Polars → Python dicts → SQLAlchemy models), (3) persistence layer (SQLAlchemy upsert). The `scripts/refresh.py` script orchestrates these three concerns and is the only entry point called by cron.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| nflreadpy | 0.1.5 (pin) | Load player stats, snap counts, play-by-play, ff_playerids crosswalk | Official nflverse Python port; successor to deprecated nfl_data_py |
| sqlalchemy | 2.0.48 | ORM, SQLite upsert, session management | Industry standard; 2.0 API required for async-compatible code Phase 3 will use |
| alembic | 1.18.4 | Versioned schema migrations | Required companion to SQLAlchemy for schema changes across phases |
| fastapi | 0.135.1 | Web framework (Phase 3 entry point, install now per CONTEXT.md) | Async, OpenAPI auto-docs, locked decision |
| polars | latest (transitive via nflreadpy) | nflreadpy returns Polars DataFrames | Used indirectly; convert to dicts before SQLAlchemy |
| requests | 2.x | Sleeper API HTTP calls | Standard; no async needed for cron script |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| aiosqlite | latest | Async SQLite driver | Needed in Phase 3 when FastAPI routes query DB asynchronously |
| pytest | latest | Unit and integration tests | Validation architecture (nyquist_validation enabled) |
| pytest-anyio | latest | Async test support | Phase 3 (not Phase 1, which is sync) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| nflreadpy | nfl_data_py | nfl_data_py archived September 2025 — do not use |
| SQLite + Alembic | Pure SQLite without ORM | Loses typed models and migration versioning Phase 2/3 depend on |
| cron + script | APScheduler in-process | In-process scheduler requires a running FastAPI server; cron is simpler and crash-safe |
| TimedRotatingFileHandler | logrotate (OS-level) | Both work; built-in Python handler requires no OS config, appropriate for personal tool |

**Installation:**
```bash
uv add nflreadpy==0.1.5 sqlalchemy==2.0.48 alembic==1.18.4 fastapi==0.135.1 requests
uv add --dev pytest
```

**Version verification (confirmed against PyPI 2026-03-21):**
- nflreadpy: 0.1.5 (latest stable; dev version exists but is unpinned)
- sqlalchemy: 2.0.48
- alembic: 1.18.4
- fastapi: 0.135.1

---

## Architecture Patterns

### Recommended Project Structure
```
fantasy-football/
├── data/                    # gitignored — SQLite DB lives here
│   └── fantasy.db
├── logs/                    # gitignored — log rotation target
│   └── refresh.log
├── scripts/
│   └── refresh.py           # standalone script invoked by cron
├── src/
│   └── fantasy/
│       ├── db/
│       │   ├── base.py      # SQLAlchemy Base, engine, session factory
│       │   ├── models.py    # Player, Matchup ORM models
│       │   └── upsert.py    # upsert helpers using sqlite insert()
│       ├── fetch/
│       │   ├── sleeper.py   # Sleeper API client
│       │   └── nflverse.py  # nflreadpy wrappers
│       └── normalize.py     # transform Polars DFs → SQLAlchemy model dicts
├── alembic/
│   ├── env.py               # must set render_as_batch=True
│   └── versions/
├── alembic.ini
├── pyproject.toml
└── uv.lock
```

### Pattern 1: Sleeper API Player Fetch and Cache
**What:** Fetch the entire player payload (~5MB) once, persist to DB; never call per-lookup
**When to use:** Every refresh cycle — always fetch all players, upsert changed records

```python
# Source: https://docs.sleeper.com/
import requests

SLEEPER_PLAYERS_URL = "https://api.sleeper.app/v1/players/nfl"

def fetch_sleeper_players() -> dict:
    """Returns dict keyed by sleeper_player_id with player objects."""
    resp = requests.get(SLEEPER_PLAYERS_URL, timeout=30)
    resp.raise_for_status()
    return resp.json()

# Key injury fields on each player object:
# player["injury_status"]         -> "Out", "Questionable", "Doubtful", "Probable", None
# player["practice_participation"] -> "Did Not Participate", "Limited", "Full", None
# player["status"]                 -> "Active", "Injured Reserve", "Practice Squad", etc.
# player["injury_start_date"]      -> "2025-12-01" or None
```

### Pattern 2: nflreadpy Data Loading (Polars → dict)
**What:** Load weekly stats, snap counts, ff_playerids via nflreadpy; convert Polars to Python dicts before persisting
**When to use:** During refresh; filter to last 4 weeks before normalizing

```python
# Source: https://nflreadpy.nflverse.com/api/load_functions/
import nflreadpy as nfl

# Weekly player stats — includes target_share, carries (carry_share must be computed)
stats_df = nfl.load_player_stats(seasons=[2025])  # returns polars.DataFrame

# Snap counts — includes offense_pct (snap %)
snaps_df = nfl.load_snap_counts(seasons=[2025])   # returns polars.DataFrame

# Play-by-play — used for DVP computation
pbp_df = nfl.load_pbp(seasons=[2025])             # returns polars.DataFrame

# Player ID crosswalk — includes gsis_id (nflverse canonical) and sleeper_id
ids_df = nfl.load_ff_playerids()                  # returns polars.DataFrame
# Key columns: gsis_id, sleeper_id (sleeper_id is ~4-digit integer as string)
```

### Pattern 3: SQLAlchemy SQLite Upsert
**What:** Use SQLite-specific `insert().on_conflict_do_update()` to upsert by canonical player ID
**When to use:** Every write to `player` or `matchup` table

```python
# Source: https://docs.sqlalchemy.org/en/20/dialects/sqlite.html
from sqlalchemy.dialects.sqlite import insert

def upsert_players(session, player_dicts: list[dict]):
    stmt = insert(Player).values(player_dicts)
    stmt = stmt.on_conflict_do_update(
        index_elements=["nflverse_id"],  # unique constraint column
        set_={
            "injury_status": stmt.excluded.injury_status,
            "practice_participation": stmt.excluded.practice_participation,
            "updated_at": stmt.excluded.updated_at,
            # include all columns that should update
        }
    )
    session.execute(stmt)
    session.commit()
```

### Pattern 4: DVP Score Computation from play-by-play
**What:** Compute "points allowed to position" per team over last 4 weeks from PBP data
**When to use:** During matchup table refresh; this is a custom groupby, not a built-in nflreadpy function

```python
# Source: nflverse PBP data; DVP is not a built-in function — must compute
# Approach: filter PBP to last 4 weeks, group by (defteam, posteam_position),
# sum fantasy_points_allowed, rank teams per position ascending (lower rank = tougher)

import polars as pl

def compute_dvp(pbp_df: pl.DataFrame, current_week: int, season: int) -> pl.DataFrame:
    """
    DVP = points allowed by defense to each offensive position over last 4 weeks.
    Uses fantasy_points columns in PBP if available, otherwise derive from
    passing_yards, receiving_yards, rushing_yards, touchdown indicators.
    Returns DataFrame with columns: (team, position, week_range, dvp_score, opponent_rank)
    """
    last_4_weeks = range(max(1, current_week - 4), current_week)
    filtered = pbp_df.filter(
        (pl.col("season") == season) &
        (pl.col("week").is_in(list(last_4_weeks)))
    )
    # Group by defteam + position of ball-carrier/receiver
    # Sum fantasy points conceded, rank ascending within each position
    # CAUTION: Validate exact PBP column names before implementing (schema validation pre-condition)
```

### Pattern 5: Off-season Detection
**What:** Use nflreadpy utility to detect off-season; return early flag from refresh script
**When to use:** Top of `scripts/refresh.py` — called every cron run

```python
# Source: https://nflreadpy.nflverse.com/api/utils/
import nflreadpy as nfl

def is_nfl_season_active() -> bool:
    """
    get_current_season(roster=False) returns current year after the
    Thursday following Labor Day. During off-season, it returns prior year.
    Cross-check: if get_current_week() returns week > 22, season is over.
    """
    current_week = nfl.get_current_week(use_date=True)
    return 1 <= current_week <= 22
```

### Pattern 6: Alembic with SQLite (batch mode required)
**What:** SQLite cannot ALTER TABLE (add/drop columns) without batch mode; Alembic's batch ops handle this
**When to use:** Always — set in env.py once

```python
# alembic/env.py — critical SQLite-specific configuration
# Source: https://alembic.sqlalchemy.org/en/latest/batch.html
with connectable.connect() as connection:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,  # REQUIRED for SQLite ALTER TABLE support
    )
```

### Pattern 7: Log rotation for cron script
**What:** Python's built-in TimedRotatingFileHandler for 7-day rolling log retention
**When to use:** In `scripts/refresh.py` logger setup

```python
# Source: https://docs.python.org/3/library/logging.handlers.html
import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

LOG_PATH = Path(__file__).parent.parent / "logs" / "refresh.log"

handler = TimedRotatingFileHandler(
    filename=str(LOG_PATH),
    when="midnight",
    interval=1,
    backupCount=7,
    encoding="utf-8",
)
logging.basicConfig(handlers=[handler], level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
```

### Anti-Patterns to Avoid
- **Joining on player name strings:** Names have inconsistent formatting across sources. Always join via `nflverse_id` (gsis_id) or `sleeper_id` from the ff_playerids crosswalk.
- **Calling Sleeper players endpoint per lookup:** The payload is ~5MB. Call once per refresh cycle, cache in DB.
- **Using nfl_data_py:** It was archived September 2025. Use nflreadpy exclusively.
- **Pinning nflreadpy above v0.1.5:** The experimental package may introduce breaking schema changes. Pin to v0.1.5 until schema validated.
- **Alembic without render_as_batch=True:** SQLite will fail on any ALTER TABLE migration without this flag.
- **Full-wipe refresh:** Deleting all rows before re-inserting risks stale data during a partial failure. Use upsert exclusively.
- **Running Polars DataFrames directly into SQLAlchemy:** Convert Polars to Python dicts/list first; SQLAlchemy does not natively consume Polars.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Schema migrations | Custom SQL migration scripts | Alembic autogenerate | Tracks applied migrations, supports rollback, batch mode for SQLite |
| Player ID crosswalk | Manual scraping of ID mappings | `nfl.load_ff_playerids()` | Maintained by nflverse/dynastyprocess; covers 31 ID systems including `gsis_id` and `sleeper_id` |
| NFL schedule / current week detection | Custom date logic | `nfl.get_current_week()`, `nfl.get_current_season()` | Handles bye weeks, playoffs, off-season edge cases correctly |
| Upsert logic | Custom INSERT-then-UPDATE | `insert().on_conflict_do_update()` | Atomic; no race conditions; SQLAlchemy 2.0 native |
| Log rotation | Manual file renaming in cron | `TimedRotatingFileHandler` | Thread-safe, handles midnight rotation correctly |

**Key insight:** The nflverse ecosystem provides player ID resolution, schedule context, and all statistical data — any custom scraping is both unnecessary and fragile.

---

## Common Pitfalls

### Pitfall 1: nflreadpy Returns Polars, Not Pandas
**What goes wrong:** Code calls `.to_dict()` on a Polars DataFrame (pandas method) and gets AttributeError.
**Why it happens:** nflreadpy defaults to Polars DataFrames; developers familiar with nfl_data_py (which used pandas) assume pandas.
**How to avoid:** Use `df.to_dicts()` (Polars method returning list of dicts) or `df.to_pandas()` then `.to_dict('records')`.
**Warning signs:** `AttributeError: 'DataFrame' object has no attribute 'to_dict'` — that is the pandas API being called on Polars.

### Pitfall 2: carry_share is Not a Pre-computed Column in nflreadpy
**What goes wrong:** Code tries to read `df["carry_share"]` from `load_player_stats()` and gets KeyError.
**Why it happens:** `target_share` is pre-computed in nflverse stats but `carry_share` is not — it must be derived by dividing player carries by team total carries, then grouping by week and team.
**How to avoid:** After loading player_stats, compute: `carry_share = player_carries / team_total_carries` where team totals require a `.group_by(["game_id", "recent_team"]).agg(pl.col("carries").sum().alias("team_carries"))` join.
**Warning signs:** KeyError on `carry_share` column at normalization time.

### Pitfall 3: DVP Requires PBP Schema Validation (Experimental Package Risk)
**What goes wrong:** PBP column names used in DVP computation differ between nflreadpy patch versions; the script silently produces wrong DVP scores or raises KeyError.
**Why it happens:** nflreadpy is labeled "experimental" and was largely written by Claude; column naming may not be stable across patches.
**How to avoid:** In Wave 0 / setup task, write a schema validation check that asserts expected PBP columns (`defteam`, `posteam`, `week`, `season`, fantasy point columns) exist before any DVP computation runs. Pin to v0.1.5 and do not bump without re-validating.
**Warning signs:** DVP scores of 0 or NaN for all teams; KeyError on PBP column access.

### Pitfall 4: Alembic WITHOUT render_as_batch Silently Skips Migrations on SQLite
**What goes wrong:** `alembic upgrade head` succeeds (no error) but the new column is not present in the SQLite table.
**Why it happens:** SQLite does not support ALTER TABLE ADD COLUMN in all versions of SQLite < 3.35. Alembic without batch mode emits unsupported DDL.
**How to avoid:** Set `render_as_batch=True` in `alembic/env.py` before running any migration. Verify the column after migration with a quick sqlite3 `.schema` check.
**Warning signs:** Migration reports success but subsequent queries for the new column fail with OperationalError.

### Pitfall 5: Sleeper Injury Status Can Be None vs. "Active"
**What goes wrong:** Logic treats `None` as "healthy" but a player listed as `status="Active"` with `injury_status=None` and a player with `injury_status="Questionable"` need different handling.
**Why it happens:** Sleeper returns `null` for `injury_status` on healthy players, not the string `"Healthy"`.
**How to avoid:** Normalize on ingest: if `injury_status` is None, store as empty string or "Active". Implement a `display_status` property on the Player model that derives the presentable status.
**Warning signs:** Injury status showing "None" in Phase 3 UI.

### Pitfall 6: cron Working Directory vs. Absolute Paths
**What goes wrong:** `scripts/refresh.py` uses relative paths (`open("logs/refresh.log")`) which resolve to `/` or the cron daemon's home directory, not the project root.
**Why it happens:** cron jobs run with a minimal environment; the working directory is not the project root.
**How to avoid:** Use `Path(__file__).parent.parent` to compute the project root inside the script. All file paths (DB path, log path) must be absolute.
**Warning signs:** Log file not found; DB file created in wrong location.

### Pitfall 7: nflreadpy Player Stats Data Lag
**What goes wrong:** Running `load_player_stats(seasons=[current_season])` on a Tuesday returns only through Sunday (or later Monday) game data; the refresh script may return stale stats for Monday Night Football games.
**Why it happens:** nflverse updates play-by-play data nightly after each game day, not in real-time. MNF data typically lands Tuesday morning.
**How to avoid:** Accept this lag as documented behavior. Log the last available week from the data and surface it as part of the data freshness timestamp (DATA-02 requirement for Phase 3). Do not retry aggressively.
**Warning signs:** Week N stats missing through Tuesday for teams that played Monday night.

---

## Code Examples

### Full Player Refresh Flow Skeleton
```python
# scripts/refresh.py
# Source: patterns verified against official docs listed in Sources section
import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
import nflreadpy as nfl
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "data" / "fantasy.db"
LOG_PATH = PROJECT_ROOT / "logs" / "refresh.log"

# --- Logging setup ---
handler = TimedRotatingFileHandler(str(LOG_PATH), when="midnight", backupCount=7)
logging.basicConfig(handlers=[handler], level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)

def main():
    # Off-season guard
    week = nfl.get_current_week(use_date=True)
    if not (1 <= week <= 22):
        log.info("season_active=false week=%s — skipping refresh", week)
        return {"season_active": False}

    season = nfl.get_current_season()
    log.info("Starting refresh season=%s week=%s", season, week)

    try:
        sleeper_players = fetch_sleeper_players()
        stats = nfl.load_player_stats(seasons=[season])
        snaps = nfl.load_snap_counts(seasons=[season])
        player_ids = nfl.load_ff_playerids()
        pbp = nfl.load_pbp(seasons=[season])
    except Exception as exc:
        log.error("Fetch failed: %s — retaining last good data", exc)
        return

    # Normalize and upsert (see normalize.py)
    with Session(engine) as session:
        upsert_players(session, normalize_players(sleeper_players, stats, snaps, player_ids))
        upsert_matchups(session, compute_dvp(pbp, week, season))

    log.info("Refresh complete")

if __name__ == "__main__":
    main()
```

### Player ID Crosswalk Join
```python
# Source: https://nflreadr.nflverse.com/articles/dictionary_ff_playerids.html
import nflreadpy as nfl
import polars as pl

ids = nfl.load_ff_playerids()
# Key columns in ff_playerids:
#   gsis_id    — "00-0XXXXXXX" format — nflverse canonical ID
#   sleeper_id — ~4-digit integer string — Sleeper platform ID

# Join stats to crosswalk on gsis_id
stats = nfl.load_player_stats(seasons=[2025])
# nflverse player stats use "player_id" column for gsis_id
joined = stats.join(
    ids.select(["gsis_id", "sleeper_id"]),
    left_on="player_id",
    right_on="gsis_id",
    how="left"
)
```

### Alembic env.py for SQLite (batch mode)
```python
# alembic/env.py — critical excerpt
# Source: https://alembic.sqlalchemy.org/en/latest/batch.html
from src.fantasy.db.base import Base  # import your models' metadata

target_metadata = Base.metadata

def run_migrations_online():
    connectable = engine_from_config(...)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # REQUIRED for SQLite
        )
        with context.begin_transaction():
            context.run_migrations()
```

### crontab entry for 2-hour refresh during NFL week
```bash
# Runs every 2 hours, 7 days a week
# cron always fires; off-season guard is inside the script
0 */2 * * * /path/to/project/.venv/bin/python /path/to/project/scripts/refresh.py >> /path/to/project/logs/cron.log 2>&1
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| nfl_data_py | nflreadpy | September 2025 (nfl_data_py archived) | Must use nflreadpy; nfl_data_py will not receive updates |
| pandas DataFrames from nflverse | Polars DataFrames from nflreadpy | September 2025 | Polars is faster but has different API; must use `.to_dicts()` not `.to_dict()` |
| SQLAlchemy 1.4 Query API | SQLAlchemy 2.0 Select API | 2023 | `session.query(Model)` still works but 2.0 `select(Model)` is the forward-compatible style |
| Alembic without batch mode | Alembic with render_as_batch=True | Always SQLite-specific | SQLite ALTER TABLE restrictions require batch mode for all schema migrations |

**Deprecated/outdated:**
- `nfl_data_py`: Archived September 2025. All usage must migrate to `nflreadpy`.
- `calculate_player_stats()` in nflfastR: Deprecated in favor of `calculate_stats()`. `load_player_stats()` in nflreadpy reflects the newer `calculate_stats()` output.
- SQLAlchemy 1.x `session.query()` pattern: Works but deprecated; use SQLAlchemy 2.0 `select()` style.

---

## Open Questions

1. **Exact PBP column names for DVP computation**
   - What we know: `load_pbp()` returns nflfastR play-by-play data with ~300 columns including `defteam`, `posteam`, `week`, `season`; fantasy point columns exist but exact names are not documented here
   - What's unclear: Whether columns like `fantasy_points`, `fantasy_points_ppr` are present in PBP or only in aggregated player_stats
   - Recommendation: Wave 0 task must run `nfl.load_pbp(seasons=[2024]).columns` and log all available columns; build DVP formula only after confirming available fields; alternative is to derive from `passing_yards`, `rushing_yards`, `receiving_yards`, `touchdown` columns manually

2. **carry_share derivation performance**
   - What we know: `target_share` is pre-computed; `carries` is available per player per week; team totals require a groupby
   - What's unclear: Whether `load_player_stats()` includes a team_carries column or whether a two-pass aggregation is required
   - Recommendation: During Wave 0 schema validation, inspect `load_player_stats(seasons=[2024]).columns` for any `*_share` or `team_*` columns; implement carry_share computation as `player_carries / team_carries` from a groupby if not available

3. **Sleeper practice_participation field values**
   - What we know: Field exists; can be null; example values include "Did Not Participate", "Limited", "Full"
   - What's unclear: Whether field is null vs. empty string vs. missing key during off-season or for players who haven't reported practice status
   - Recommendation: Defensive normalization — treat missing/null/empty as "Unknown"; store as nullable varchar; do not assert specific values

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (latest) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` — see Wave 0 |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-01 | Injury status fields (`injury_status`, `practice_participation`) are fetched from Sleeper and stored with correct types | unit | `pytest tests/test_sleeper.py::test_player_upsert -x` | Wave 0 |
| DATA-01 | Refresh cron fires and updates DB without manual intervention | integration | `pytest tests/test_refresh.py::test_refresh_runs -x` | Wave 0 |
| DATA-03 | Off-season check returns `season_active=False` when week > 22 or pre-season | unit | `pytest tests/test_refresh.py::test_offseason_guard -x` | Wave 0 |
| DATA-03 | In-season run does NOT early-return with season_active flag | unit | `pytest tests/test_refresh.py::test_inseason_runs -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_sleeper.py` — covers DATA-01 player upsert with correct field types
- [ ] `tests/test_nflverse.py` — validates PBP schema columns, carry_share derivation
- [ ] `tests/test_refresh.py` — covers DATA-01 scheduled refresh, DATA-03 off-season guard
- [ ] `tests/conftest.py` — shared fixtures: in-memory SQLite engine, mock Sleeper API response
- [ ] Framework install: `uv add --dev pytest` — not yet installed (greenfield project)

---

## Sources

### Primary (HIGH confidence)
- https://docs.sleeper.com/ — Player endpoint fields, injury_status values, rate limit (1000 req/min), cache guidance (~5MB)
- https://nflreadpy.nflverse.com/ — Function list, Polars default, version v0.1.5 confirmed
- https://nflreadpy.nflverse.com/CHANGELOG/ — v0.1.5 release date (2025-11-19), experimental status confirmed
- https://nflreadpy.nflverse.com/api/load_functions/ — All 23 load functions documented
- https://nflreadpy.nflverse.com/api/utils/ — `get_current_season()` and `get_current_week()` behavior for off-season detection
- https://nflreadr.nflverse.com/articles/dictionary_ff_playerids.html — `gsis_id` and `sleeper_id` column names confirmed
- https://nflreadr.nflverse.com/articles/dictionary_snap_counts.html — `offense_pct` column confirmed; no target/carry share in snap data
- https://docs.sqlalchemy.org/en/20/dialects/sqlite.html — `insert().on_conflict_do_update()` SQLite upsert API
- https://alembic.sqlalchemy.org/en/latest/batch.html — `render_as_batch=True` requirement for SQLite
- https://docs.python.org/3/library/logging.handlers.html — `TimedRotatingFileHandler` with `backupCount=7`
- PyPI version verification (2026-03-21): nflreadpy=0.1.5, sqlalchemy=2.0.48, alembic=1.18.4, fastapi=0.135.1

### Secondary (MEDIUM confidence)
- https://www.nflfastr.com/articles/stats_variables.html — `target_share` is pre-computed; `carry_share` is NOT (confirmed no column exists, must derive)
- https://nflfastr.com/reference/calculate_player_stats.html — deprecated function note confirms newer `calculate_stats()` approach
- https://github.com/nflverse/nfl_data_py — archived September 2025 (confirmed from releases page and README)

### Tertiary (LOW confidence)
- Community articles on FastAPI + SQLAlchemy + uv patterns — general structure is consistent across multiple sources; specific versions confirmed via PyPI

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified against PyPI on 2026-03-21
- Sleeper API fields: HIGH — verified against official docs.sleeper.com
- nflreadpy function API: HIGH — verified against nflreadpy.nflverse.com official docs
- DVP column names: LOW — exact PBP column names for fantasy points not confirmed; Wave 0 schema validation required
- carry_share derivation: MEDIUM — confirmed no pre-computed column; derivation approach is standard groupby pattern

**Research date:** 2026-03-21
**Valid until:** 2026-04-21 (nflreadpy is experimental; re-verify if bumping version)
