# Phase 4: Reliability & Enhancement - Research

**Researched:** 2026-03-30
**Domain:** NFL odds enrichment, weather data, player comparison API, macOS scheduling
**Confidence:** HIGH (APIs verified via official docs; schema decisions based on existing codebase analysis)

---

## Summary

Phase 4 adds three features to the existing FastAPI + Next.js app: Vegas implied team totals (ENRI-01), weather flags for outdoor games (ENRI-02), and a side-by-side player comparison endpoint (COMP-01). All three are additive — no existing routes or models need to change, only extended. The scheduled refresh (scripts/refresh.py) is already production-quality; it needs only a crontab entry, not code changes.

The core data architecture decision is: Vegas and weather data belong in a new `GameLine` table keyed by `(week, home_team, away_team)`, not as columns on `Matchup`. `Matchup` is position-scoped (one row per week/team/position), while game-level data (totals, weather) is team-game-scoped. Storing game data on `Matchup` would force 12+ duplicate rows per game.

**Primary recommendation:** New `GameLine` table for ENRI-01/ENRI-02 data; new `/compare` FastAPI route for COMP-01; crontab for scheduling.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ENRI-01 | Vegas implied team total overlay alongside recommendation | GameLine table + The Odds API free tier; implied total derivation formula documented below |
| ENRI-02 | Weather flag for outdoor games (pass game suppression signal) | Open-Meteo free API; dome stadium list; per-game lat/lon lookup at refresh time |
| COMP-01 | Side-by-side A vs. B comparison view | New `/compare` FastAPI route; reuses existing score_player() and DB query logic |
</phase_requirements>

---

## Q1: Vegas Implied Totals (ENRI-01)

### Recommendation: The Odds API free tier

**Source:** https://the-odds-api.com (verified)
**Free tier:** 500 requests/month. At one call per refresh (every 2 hours, 8 slots/day, ~18 weeks of season) = ~1,008 calls/season. **This exceeds the free tier.** Mitigation: call only during the Wed–Sat window when lines are set and meaningful (Tuesday lines are early and volatile). That is ~4 days x 4 calls/day x 18 weeks = 288 calls/season. Stay well under 500.

### Endpoint

```
GET https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds/
    ?apiKey={KEY}
    &regions=us
    &markets=totals,spreads
    &oddsFormat=american
```

Each market counts as 1 against the quota per region. Requesting `totals` + `spreads` = 2 quota units per call. The response contains a list of games, each with bookmakers and their markets.

### Deriving Implied Team Total

The API returns a game total (over/under line) via the `totals` market and a spread via the `spreads` market. Implied team totals are not a direct field — they must be calculated:

```
implied_home_total = (game_total / 2) - (spread / 2)
implied_away_total = (game_total / 2) + (spread / 2)
```

Where `spread` is the home team's spread (negative = home favored). Example: total = 47.5, home spread = -3.5:
- Home implied = 23.75 + 1.75 = 25.5
- Away implied = 23.75 - 1.75 = 22.0

Use the consensus line from the first bookmaker returned (typically DraftKings or FanDuel). Averaging across all bookmakers is more accurate but costs no additional quota calls since all bookmakers are in the same response.

### Refresh frequency

Refresh game lines **once per refresh cycle** but only when `datetime.now().weekday() in (2, 3, 4, 5)` (Wed–Sat). Lines before Wednesday are too early. Sunday lines are locked at kickoff and irrelevant for start/sit decisions.

### DB Schema: New `GameLine` table (not a column on `Matchup`)

**Why not a column on `Matchup`:** `Matchup` has a unique constraint on `(week, team, position)` — one row per week/team/position combination means 6 rows per team per week (QB, RB, WR, TE, K, DST). Storing game total and implied total on `Matchup` would duplicate that data 6 times per team and force joins on two axes. Game-level data belongs in a game-level table.

**Proposed `GameLine` model:**

```python
class GameLine(Base):
    __tablename__ = "game_line"

    id = Column(Integer, primary_key=True, autoincrement=True)
    week = Column(Integer, nullable=False)
    home_team = Column(String(5), nullable=False)
    away_team = Column(String(5), nullable=False)

    # Vegas lines
    game_total = Column(Float, nullable=True)          # over/under line
    home_spread = Column(Float, nullable=True)         # home team spread (neg = favored)
    home_implied_total = Column(Float, nullable=True)  # derived: (total/2) - (spread/2)
    away_implied_total = Column(Float, nullable=True)  # derived: (total/2) + (spread/2)

    # Weather (ENRI-02 co-located here since it is game-scoped)
    is_dome = Column(Boolean, nullable=False, default=False)
    wind_mph = Column(Float, nullable=True)
    precip_probability = Column(Integer, nullable=True)  # 0-100
    weather_flag = Column(Boolean, nullable=False, default=False)  # true = meaningful weather

    updated_at = Column(DateTime, ...)

    __table_args__ = (
        UniqueConstraint("week", "home_team", "away_team", name="uq_gameline_week_home_away"),
    )
```

The `Player` table already has `matchup_id`. The API layer joins `Player -> Matchup -> GameLine` by matching `Matchup.team` against `GameLine.home_team OR away_team` for the same week.

**Confidence:** HIGH for API structure (verified via official docs). MEDIUM for quota math (assumes 2-hour refresh cadence from Q4 research).

---

## Q2: Weather Data (ENRI-02)

### Recommendation: Open-Meteo

**Source:** https://open-meteo.com/en/docs (verified)
**Cost:** Free, no API key required for non-commercial use.
**Endpoint:**

```
GET https://api.open-meteo.com/v1/forecast
    ?latitude={lat}
    &longitude={lon}
    &hourly=wind_speed_10m,precipitation_probability
    &wind_speed_unit=mph
    &timezone=America/Chicago
    &forecast_days=7
```

`wind_speed_unit=mph` converts from the default km/h. Response is an hourly array; match the game kickoff hour to pull the right slot.

### Dome Stadiums — Weather Immune (skip API call for these)

The following NFL venues are fully enclosed domes or retractable roofs that are reliably closed for regular season games:

| Team | Stadium | Status |
|------|---------|--------|
| ARI Cardinals | State Farm Stadium | Retractable roof (treat as dome) |
| ATL Falcons | Mercedes-Benz Stadium | Fixed dome |
| DAL Cowboys | AT&T Stadium | Retractable roof (treat as dome) |
| DET Lions | Ford Field | Fixed dome |
| HOU Texans | NRG Stadium | Retractable roof (treat as dome) |
| IND Colts | Lucas Oil Stadium | Retractable roof (treat as dome) |
| JAX Jaguars | EverBank Stadium | Open-air — NOT a dome |
| LV Raiders | Allegiant Stadium | Fixed dome |
| LAR / LAC | SoFi Stadium | Roof, open sides — treat as dome for rain, NOT for wind |
| MIN Vikings | U.S. Bank Stadium | Fixed dome |
| NO Saints | Caesars Superdome | Fixed dome |
| NYG / NYJ | MetLife Stadium | Open-air — NOT a dome |

**Implementation:** hardcode a `DOME_TEAMS` set in the fetch module. If `home_team in DOME_TEAMS`, set `is_dome=True`, skip API call, set `weather_flag=False`.

For SoFi (LAR/LAC), treat as dome (roof provides full rain coverage; open sides allow some wind but it is heavily mitigated). Set `is_dome=True` for simplicity — the error rate from occasional SoFi wind events is acceptable.

### Stadium Coordinates

Hardcode a `STADIUM_COORDS` dict keyed by home team abbreviation. A full 32-team dict is a one-time lookup — Open-Meteo's coordinate precision requirement is ~2 decimal places, so these do not need to be exact:

```python
STADIUM_COORDS = {
    "BUF": (42.77, -78.79),   # Highmark Stadium
    "NE":  (42.09, -71.26),   # Gillette Stadium
    "MIA": (25.96, -80.24),   # Hard Rock Stadium
    "NYJ": (40.81, -74.07),   # MetLife Stadium
    "NYG": (40.81, -74.07),   # MetLife Stadium (same venue)
    "BAL": (39.28, -76.62),   # M&T Bank Stadium
    "CIN": (39.10, -84.52),   # Paycor Stadium
    "CLE": (41.50, -81.70),   # Huntington Bank Field
    "PIT": (40.45, -80.02),   # Acrisure Stadium
    "HOU": (29.68, -95.41),   # NRG Stadium
    "IND": (39.76, -86.16),   # Lucas Oil Stadium
    "JAX": (30.32, -81.64),   # EverBank Stadium
    "TEN": (36.17, -86.77),   # Nissan Stadium
    "DEN": (39.74, -105.02),  # Empower Field
    "KC":  (39.05, -94.48),   # Arrowhead Stadium
    "LV":  (36.09, -115.18),  # Allegiant Stadium
    "LAC": (33.95, -118.34),  # SoFi Stadium
    "LAR": (33.95, -118.34),  # SoFi Stadium
    "DAL": (32.75, -97.09),   # AT&T Stadium
    "NYG": (40.81, -74.07),
    "PHI": (39.90, -75.17),   # Lincoln Financial Field
    "WAS": (38.91, -76.86),   # Northwest Stadium
    "CHI": (41.86, -87.62),   # Soldier Field
    "DET": (42.34, -83.04),   # Ford Field
    "GB":  (44.50, -88.06),   # Lambeau Field
    "MIN": (44.97, -93.26),   # U.S. Bank Stadium
    "ATL": (33.75, -84.40),   # Mercedes-Benz Stadium
    "CAR": (35.23, -80.85),   # Bank of America Stadium
    "NO":  (29.95, -90.08),   # Caesars Superdome
    "TB":  (27.98, -82.50),   # Raymond James Stadium
    "ARI": (33.53, -112.26),  # State Farm Stadium
    "SF":  (37.40, -121.97),  # Levi's Stadium
    "SEA": (47.60, -122.33),  # Lumen Field
}
```

### Thresholds for "meaningful weather"

- **Wind:** > 15 mph (`wind_mph > 15`). This is the broadly accepted threshold in fantasy analysis where passing game efficiency begins to decline. Above 20 mph is severe; 15 is the conservative/safe flag point.
- **Precipitation:** > 30% probability (`precip_probability > 30`). This flags games where rain/snow is likely enough to matter. This matches the "likely" threshold used in NWS forecasts.
- **Combined flag:** `weather_flag = (not is_dome) and (wind_mph > 15 or precip_probability > 30)`

### When to fetch

Fetch weather **only for current week's games** at each refresh cycle. Do not fetch historical weather (no value) or future weeks (too far out to be accurate). Use the game date stored alongside `GameLine` to determine which games are "this week." The 7-day forecast window from Open-Meteo covers any game within the current NFL week (games run Thu–Mon).

**Confidence:** HIGH for API (official docs verified). HIGH for dome list (common knowledge, stable year-to-year). MEDIUM for coordinates (hardcoded — acceptable since stadium locations do not change).

---

## Q3: Player Comparison (COMP-01)

### Recommendation: New `/compare` FastAPI route

**Approach:** Add a single `/compare` endpoint to `main.py` that accepts two player IDs and returns both full recommendation payloads in a single response object.

```python
@app.get("/compare")
def compare_players(
    a: int,
    b: int,
    format: str = "ppr",
    db: Session = Depends(get_db),
):
    rec_a = _build_recommendation(a, format, db)  # extracted from get_player_recommendation
    rec_b = _build_recommendation(b, format, db)
    return {"player_a": rec_a, "player_b": rec_b}
```

The existing `get_player_recommendation` logic needs to be refactored into a `_build_recommendation(player_id, format, db)` helper that both the existing `/player/{id}` route and the new `/compare` route call. This is a pure refactor — the `/player/{id}` response shape does not change.

**Why server-side over two client-side fetches:**

| Criterion | `/compare` server route | Two `/player/{id}` client fetches |
|-----------|------------------------|-----------------------------------|
| Network round trips | 1 | 2 (sequential or parallel) |
| Single loading state | Yes — one spinner | No — must manage two independent states |
| Shareable URL | `/compare?a=123&b=456&format=ppr` | Requires client state serialization |
| Error handling | One catch | Two separate error paths |
| Backend cost | Negligible (same DB queries) | Same |

The server route is strictly better for the comparison use case. Two separate client fetches are fine for the basic player page but create awkward UX for a "both or nothing" comparison view.

**Frontend route:** Next.js `/compare` page at `src/app/compare/page.tsx`, reading `a`, `b`, and `format` from URL search params. Use `useSearchParams()` (requires `"use client"`) or pass as server component props. Single fetch to `/compare?a={a}&b={b}&format={format}`. Render two `PlayerCard` columns side by side.

**No new DB tables needed.** All data already exists in `Player` and `Matchup` tables.

**Confidence:** HIGH. This is a pure FastAPI/Next.js routing question with no external dependencies.

---

## Q4: Scheduled Refresh — macOS

### Recommendation: crontab (not launchd)

**Reason:** launchd plist files require creating an XML file at `~/Library/LaunchAgents/com.yourapp.refresh.plist`, loading it with `launchctl load`, and debugging with `launchctl list` and Console.app. For a personal dev machine, this overhead is unjustified. `crontab -e` is three keystrokes and is universally understood. The only meaningful advantage of launchd (run after sleep/wake) does not matter here — a missed 2-hour refresh is harmless since the data source is resilient and `refresh.py` already logs failures gracefully.

### Exact crontab entry

```cron
0 6,8,10,12,14,16,18,20 * * * cd /Users/chetankonathala/Desktop/fantasy-football && /usr/bin/python3 scripts/refresh.py >> logs/cron.log 2>&1
```

This fires at the top of each even hour from 6am to 8pm (8 executions per day). The `>>` appends to `logs/cron.log`; stderr is merged with stdout via `2>&1`. The `cd` first ensures `__file__`-based path resolution in `refresh.py` works correctly (the script uses `Path(__file__).resolve().parent.parent` which is absolute and does not depend on cwd, but the cd provides a safety net for any relative path assumptions in dependencies).

**Alternative if using a virtualenv:**

```cron
0 6,8,10,12,14,16,18,20 * * * cd /Users/chetankonathala/Desktop/fantasy-football && .venv/bin/python scripts/refresh.py >> logs/cron.log 2>&1
```

Replace `.venv/bin/python` with the actual virtualenv path.

### Does refresh.py need changes?

**No.** The script is already production-ready for cron:
- Uses absolute paths via `Path(__file__).resolve()` (Pitfall 6 already solved)
- Off-season guard handles out-of-season runs gracefully
- On fetch failure: logs error, returns early, retains last good data
- `setup_logging()` adds `TimedRotatingFileHandler` with 7-day retention

The only addition needed is ensuring the `logs/` directory exists before cron first runs it: `mkdir -p /Users/chetankonathala/Desktop/fantasy-football/logs` (the script creates it automatically via `LOG_PATH.parent.mkdir(parents=True, exist_ok=True)`, so this is already handled).

**To install the crontab:**
```bash
crontab -e
# paste the line above, save and exit
crontab -l  # verify it was saved
```

**Confidence:** HIGH. crontab behavior on macOS is well-established and the script requires no modification.

---

## Standard Stack (Phase 4 additions only)

| Library | Version | Purpose |
|---------|---------|---------|
| requests | 2.31+ (already in project) | HTTP calls to The Odds API and Open-Meteo |
| alembic | already configured | New migration for `game_line` table |
| The Odds API | v4 | NFL implied totals (free tier) |
| Open-Meteo | current | Weather data (free, no key) |

No new Python packages required. Both APIs are pure HTTP GET with JSON responses, handled by `requests`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| Implied total math | Custom odds scraper | The Odds API `totals` + `spreads` markets + formula |
| Weather forecasts | Any proprietary weather source | Open-Meteo (free, accurate, no key) |
| Stadium dome detection | Dynamic lookup | Static `DOME_TEAMS` frozenset in fetch module |
| Comparison logic | New scoring engine | Refactor `_build_recommendation()` helper, reuse entirely |

---

## Common Pitfalls

### Pitfall 1: The Odds API quota exhaustion
Over-fetching during off-season or early week (Mon/Tue) wastes quota on volatile/missing lines. Guard the call: `if not (1 <= week <= 18) or datetime.now().weekday() < 2: skip`. The off-season guard in `refresh.py` already handles week range; add a day-of-week guard for odds specifically.

### Pitfall 2: Open-Meteo wind units
Default unit is km/h, not mph. Always pass `&wind_speed_unit=mph` to the query. Without it, the 15 mph threshold check will silently compare mph thresholds against km/h values (15 km/h = 9.3 mph — far too low).

### Pitfall 3: GameLine join ambiguity
A player's team may be the home OR away team in `GameLine`. The join must check both: `(GameLine.home_team == team) | (GameLine.away_team == team)`. A WHERE clause checking only `home_team` will miss half the games.

### Pitfall 4: `/compare` with invalid player IDs
Both players must exist. Return 404 with a clear message if either ID is not found, before attempting to build either recommendation. Do not return a partial `{"player_a": {...}, "player_b": null}` — the frontend has no use for a half-comparison.

### Pitfall 5: Cron environment vs. dev environment
`crontab` runs with a minimal PATH (typically `/usr/bin:/bin`). Use the full path to the Python interpreter (`/usr/bin/python3` or `/path/to/.venv/bin/python`), not `python3`. The `cd` before the script handles the working directory.

---

## Sources

### Primary (HIGH confidence)
- https://the-odds-api.com/liveapi/guides/v4/ — endpoint format, markets, quota rules (verified via WebFetch)
- https://open-meteo.com/en/docs — parameter names, no-key policy, wind_speed_unit option (verified via WebFetch)

### Secondary (MEDIUM confidence)
- Dome stadium list: stable common knowledge cross-referenced against current NFL venue information
- Weather thresholds (15 mph wind, 30% precip): standard fantasy community thresholds; consistent across major fantasy analysis sites

---

## Metadata

**Confidence breakdown:**
- ENRI-01 (Vegas): HIGH — API verified, formula is arithmetic, quota math is deterministic
- ENRI-02 (Weather): HIGH — API verified, dome list is stable, coordinates are hardcoded one-time
- COMP-01 (Compare): HIGH — pure application-layer routing, no external dependencies
- Q4 (Scheduling): HIGH — crontab on macOS is well-established, refresh.py requires no changes

**Research date:** 2026-03-30
**Valid until:** 2026-09-01 (APIs are stable; re-verify The Odds API quota limits before next season)
