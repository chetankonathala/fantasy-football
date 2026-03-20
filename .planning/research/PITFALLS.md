# Pitfalls Research

**Domain:** Fantasy football analytics — start/sit recommendation engine
**Researched:** 2026-03-19
**Confidence:** MEDIUM (ESPN API behavior from community reports; recommendation accuracy from published studies; architecture patterns from domain knowledge)

---

## Critical Pitfalls

### Pitfall 1: Treating the ESPN Unofficial API as Stable Infrastructure

**What goes wrong:**
The ESPN fantasy API is entirely undocumented and has broken without notice multiple times. In February 2019, ESPN migrated v2 to v3 silently. In August 2025, ESPN restricted access to historical data previously available via public endpoints, now requiring authenticated cookie sessions. Projects that build directly against ESPN endpoints with no abstraction layer or fallback wake up mid-season with a completely broken product.

**Why it happens:**
The ESPN hidden API "works" immediately with no signup or key. Developers treat this as a green light and skip the abstraction layer, building the entire data pipeline directly against ESPN URLs. When the endpoint structure shifts, every data-fetching layer breaks simultaneously.

**How to avoid:**
- Wrap all ESPN API calls behind a single data adapter interface. The rest of the app should never call ESPN URLs directly.
- Cache fetched data aggressively (Redis or in-memory) so the app continues showing last-known data if the API goes down.
- Build a health-check endpoint that validates the ESPN response shape on startup and alerts when schema changes.
- Treat authentication cookies (espn_s2, SWID) as ephemeral secrets that must be rotated; never hardcode them.
- Consider Sleeper API or nfl_data_py (now nflreadpy) as a fallback data source for player/stats data that doesn't require ESPN authentication.

**Warning signs:**
- You reference ESPN endpoint URLs in more than one file.
- There is no error handling or fallback when ESPN returns a non-200 or unexpected schema.
- The app crashes entirely when the ESPN call fails instead of serving cached data.

**Phase to address:**
Data infrastructure phase (earliest phase). The adapter pattern must be established before any feature is built on top of it.

---

### Pitfall 2: Start/Sit Recommendation Presented Without Reasoning Loses User Trust

**What goes wrong:**
A numeric score or bare "START" / "SIT" label creates a black-box problem. Users cannot tell whether the recommendation accounts for the injury update from Thursday morning, the dome weather override, or the favorable matchup grade. When the recommendation is wrong — and it will be wrong roughly 35-46% of the time by industry benchmarks — users have no way to evaluate why and no reason to return.

**Why it happens:**
Showing a score is easier to build. Displaying reasoning requires structured data about each contributing signal (injury status, matchup grade, usage rate, weather). Developers defer the reasoning layer as "phase 2" and it never ships.

**How to avoid:**
- Design the data model around structured signals from day one: each recommendation record must carry `injury_status`, `matchup_grade`, `snap_pct_trend`, `target_share`, and `weather_flag` as first-class fields, not derived on the fly.
- The UI must render these signals alongside the recommendation — not separately and not later.
- Set the expectation in the product that the tool shows reasoning, not just outcomes. Frame accuracy as "helping you understand the situation" rather than "always being right."

**Warning signs:**
- The recommendation is stored as a single string or score with no supporting signal fields.
- Reasoning is computed on the frontend from raw stats on page load (fragile, inconsistent).
- The design shows a score with a "learn more" link instead of inline reasoning.

**Phase to address:**
Recommendation engine phase. The signal schema must be locked before building the recommendation logic.

---

### Pitfall 3: Ignoring Off-Season vs. In-Season Data Availability

**What goes wrong:**
The entire product premise depends on weekly data updates during Weeks 1-18 of the NFL season. During the off-season (February through August), many data endpoints return stale, incomplete, or absent data. Projects that don't account for this lifecycle either break during the off-season or display misleading stats from the prior season as if current.

**Why it happens:**
Development often starts during the off-season. The API appears to work fine against prior season data. Developers don't test what happens when `week=current` returns nothing because the season hasn't started, or when injury data is absent (as documented with nflverse's missing 2025 injury data).

**How to avoid:**
- Build an explicit season-state model: `off_season | preseason | regular_season | playoffs`. The app behaves differently in each state.
- During off-season, show a clear "season not active" state rather than attempting to render recommendations.
- Seed the database with Week 1 test data before in-season, and test the full update cycle before the season starts (September target).
- Use nflreadpy's documented data schedule — player stats update nightly after game days; plan polling accordingly.

**Warning signs:**
- No concept of "current week" or "current season" in the data model.
- The app assumes data will always be present for any player query.
- No test fixtures covering empty or partial API responses.

**Phase to address:**
Data infrastructure phase. The season-state model must exist before recommendation logic is built.

---

### Pitfall 4: Player ID Fragmentation Across Data Sources

**What goes wrong:**
ESPN assigns its own player IDs. The NFL assigns its own. Sleeper has its own. nflverse has its own. If the app uses more than one data source (e.g., ESPN for roster data and nflverse for play-by-play stats), joins fail silently — Patrick Mahomes in source A is not automatically the same record as "Patrick Mahomes" in source B. This causes mismatched stats, wrong recommendations, and data that appears correct but isn't.

**Why it happens:**
Developers start with one source, get it working, then add a second source for data not available in the first. They assume player names are a reliable join key, which breaks on name variants, Jr./Sr. suffixes, and foreign name transliterations.

**How to avoid:**
- Commit to a single canonical player ID system early (ESPN player IDs, since the project targets ESPN Fantasy).
- If pulling from a second source, use nflverse's `ff_playerids` crosswalk table, which maps ESPN, Sleeper, Yahoo, and nflverse IDs.
- Store the canonical player record with all known external IDs as a mapping table in the database from day one.
- Never join on player name. Always join on ID.

**Warning signs:**
- Player name strings are used as join keys anywhere in the codebase.
- Stats for a player look plausible but are subtly wrong for certain edge cases (same-name players, players with name changes after trades).
- Two data source integrations exist without a shared ID mapping table.

**Phase to address:**
Data infrastructure phase. ID mapping must be solved before any multi-source data is introduced.

---

### Pitfall 5: Recommendation Accuracy Collapses at Skill Positions With Small Samples

**What goes wrong:**
The model weights recent performance heavily. A running back who had two monster games after an injury to the starter looks like a strong start. A quarterback who threw for 340 yards in a dome game looks elite. These samples are too small to be predictive. The recommendation fires with high confidence and is wrong. Users lose trust quickly.

**Why it happens:**
Recency bias is the path of least resistance: recent data is easy to fetch and feels relevant. Developers don't penalize small samples or flag volatility. Tight ends and rookies are especially problematic — their role changes rapidly and their historical baseline is short or irrelevant.

**How to avoid:**
- Weight trailing performance over multiple games (minimum 4-6 game window), not just the most recent game.
- Flag recommendations for players with fewer than 4 games of data as low-confidence. Show this flag visibly in the UI.
- For tight ends and rookies, surface target share and snap percentage trends rather than point projections, which are inherently noisy.
- Do not project kicker or DST performance using player-level stats models — use matchup and defense-allowed data instead.

**Warning signs:**
- Recommendation confidence is the same for a 16-game starter and a player in their second game.
- The algorithm weights `last_week_points` as heavily as `season_avg_points`.
- No distinction between position volatility levels in the recommendation engine.

**Phase to address:**
Recommendation engine phase. Signal weighting logic must include sample size and volatility from the start.

---

### Pitfall 6: Weather Data Fetched Once Per Week and Left Stale

**What goes wrong:**
Weather is fetched Monday or Tuesday and cached. By Sunday game time, conditions have changed. A game initially forecast for mild conditions now has 20mph gusts that tank the passing game. The app recommends starting a wide receiver into a wind-affected game without knowing. The recommendation is not just wrong — it's wrong in a way the user trusted because the app claimed to account for weather.

**Why it happens:**
Weather feels like a bonus feature, so it gets a simple implementation: fetch once, store, done. The temporal dimension of weather data — that forecasts change hourly approaching game time — is not modeled.

**How to avoid:**
- Treat weather data as a separate high-churn data class distinct from player stats (which update weekly). Refresh weather data at least every 6 hours Thursday-Sunday during the season.
- Use the NWS (National Weather Service) API, which is free and provides forecast data in structured JSON, or an NFL-specific weather feed.
- Flag outdoor stadium games explicitly and note when weather data was last refreshed in the UI.
- Identify dome stadiums in the venue database and skip weather data for those games entirely — applying weather modifiers to a dome game is a correctness bug.

**Warning signs:**
- Weather data has a single weekly refresh job.
- No distinction between dome and outdoor venues in the stadium data model.
- Weather is fetched and stored as a plain text string rather than structured fields (wind_mph, precipitation_type, temperature_f).

**Phase to address:**
Data enrichment phase (after core stats, before recommendation engine consumes weather signals).

---

### Pitfall 7: Scope Creep Into League Management Features

**What goes wrong:**
The v1 scope is deliberate: player lookup, start/sit recommendation, visible reasoning. Scope creep happens when the first version feels almost done and "small additions" accumulate: trade analyzer, waiver wire suggestions, league standings, draft board. Each addition is plausible and each delays shipping the core thing that makes this tool valuable.

**Why it happens:**
When the core feature works, every adjacent feature looks achievable and impactful. The project goal shifts from "ship something I use weekly" to "build a platform." The output becomes a half-finished multi-feature tool rather than a sharp single-purpose tool.

**How to avoid:**
- The project's explicit out-of-scope list (no league management, no OAuth sync, no mobile app) is not a suggestion — treat it as a hard constraint during v1.
- When a new feature idea appears, log it in a backlog. Do not build it until the core recommendation loop is validated in-season.
- Gate v2 features on a concrete threshold: "I used the start/sit tool for at least 4 consecutive weeks and found it genuinely useful."

**Warning signs:**
- The product backlog grows faster than items are closed.
- Development effort is split between the recommendation engine and a new non-core feature.
- The phrase "while I'm in there" precedes any non-critical change.

**Phase to address:**
All phases. This is a process pitfall, not a technical one. Addressed by explicit scope gates in the roadmap.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Calling ESPN API directly without an adapter layer | Faster initial integration | Any ESPN endpoint change breaks every feature simultaneously | Never |
| Storing player ID as a string (name-based) | No mapping table needed | Silent join failures across data sources | Never |
| Single weekly weather refresh job | Simple cron setup | Stale weather at game time invalidates recommendations | Off-season testing only |
| Hardcoding current NFL week number | Skip season-state logic | Breaks at week rollover, off-season, and playoffs | Never in production |
| Deriving recommendation reasoning dynamically from raw stats | Simpler data model | Reasoning becomes inconsistent across page loads and data updates | MVP only if reasoning fields are added before launch |
| Fetching all player data on every page request | Always fresh | Hammers ESPN API, risks rate limiting or IP block | Never in production |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| ESPN unofficial API | Assuming endpoints are stable and undocumented behavior is intentional | Wrap all ESPN calls in an adapter; validate response schema; cache results aggressively |
| ESPN unofficial API | Using authentication cookies in client-side code | Keep espn_s2 and SWID server-side only; never expose in frontend |
| ESPN unofficial API | Assuming no rate limits exist because none are published | Implement exponential backoff; batch requests; cache for at least 15 minutes per player |
| nflverse / nflreadpy | Using the archived nfl_data_py package | Migrate to nflreadpy (the active Python port); check for injury data gaps (2025 injury data was absent) |
| Weather APIs | Applying weather modifiers to dome or retractable-roof stadiums | Maintain a venue database with `is_dome` flag; skip weather signals for those games |
| Cross-source player data | Joining ESPN and nflverse data on player name | Use nflverse `ff_playerids` crosswalk table; always join on numeric ID |
| NFL injury report data | Treating Wednesday injury designations as final | Injury statuses change through Saturday; refresh at minimum Thursday and Saturday for each week |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Fetching player data per request with no cache | Page load times spike; ESPN API returns 429 or blocks IP | Implement server-side cache (Redis or in-memory) with 15-minute TTL for player stats | At any real usage, immediately during development |
| No database indexes on player_id and week fields | Recommendation queries slow as data accumulates across multiple seasons | Add indexes on player_id, season, week on all stats tables from day one | Once tables exceed ~10k rows |
| Re-computing recommendation scores on every page load | Slow UI; inconsistent results if data changes mid-render | Pre-compute and store recommendations after each data refresh job | Any non-trivial calculation logic |
| Polling ESPN API in a tight loop | IP ban, rate limit, or degraded ESPN response times | Use a scheduled job with a reasonable interval (15 min for stats, 6 hr for weather) | Immediately; ESPN has undocumented but real limits |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Storing ESPN_S2 and SWID authentication cookies in environment variables exposed to the client | Cookie exposure allows impersonation of the authenticated ESPN account | Store cookies only in server-side environment; never include in API responses or client bundles |
| Using the ESPN unofficial API commercially without reviewing ESPN's Terms of Service | Cease-and-desist, API access revoked | Review ESPN ToS; for personal/non-commercial use the risk is low, but document the decision |
| No input sanitization on player name search | XSS or injection if search term is reflected back into the DOM | Sanitize all user input; use parameterized queries for any database lookups |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Showing a score or label without visible reasoning | User cannot evaluate whether the recommendation accounts for today's injury news; trust erodes after one wrong call | Surface injury status, matchup grade, and usage trend inline next to every recommendation |
| No data freshness timestamp | User cannot tell if the app has today's Thursday injury updates or last Tuesday's stale data | Show "Data updated: [timestamp]" prominently on every recommendation card |
| Identical recommendation format for high-confidence and low-confidence players | Users over-trust recommendations for volatile players (rookies, new starters) | Add a visual confidence indicator; flag low-sample players with an explicit caveat |
| Showing recommendations during the off-season with last season's data | Stale data actively misleads; users who check in February get 2024 matchup grades for 2025 | Show a clear off-season state; disable recommendations or mark data vintage prominently |
| Burying the sit recommendation | Confirmation bias — users look for validation to start their guy | Make SIT and START equally prominent; a reluctant sit recommendation is the highest-value output of the tool |

---

## "Looks Done But Isn't" Checklist

- [ ] **Recommendation engine:** Shows a score but does not surface the underlying signals (injury status, matchup grade, usage trend) — verify each signal is stored as a structured field and rendered in the UI.
- [ ] **Injury data:** Pulls Wednesday designation and never refreshes — verify that Saturday final inactives trigger a re-computation of recommendations.
- [ ] **Weather integration:** Applied to all games including domes — verify the venue table has an `is_dome` field and weather signals are skipped for dome games.
- [ ] **Player ID mapping:** Works for star players but fails for similarly named players or recent free agents — verify ID mapping via numeric IDs, not name strings.
- [ ] **ESPN API error handling:** Works in happy path but crashes silently when ESPN returns 503 — verify fallback to cached data and visible error state in the UI.
- [ ] **Off-season behavior:** No concept of "current week" — verify that the season-state model correctly gates recommendation features when no active NFL week exists.
- [ ] **Kicker and DST recommendations:** Uses the same scoring signals as skill positions — verify that K and DST use matchup/defense-allowed data, not historical point projections.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| ESPN API endpoint breaks mid-season | HIGH | Switch to alternate data source (Sleeper for player data, nflreadpy for stats); requires pre-built adapter to swap quickly |
| No reasoning signals stored in data model | HIGH | Requires data model migration, backfill of historical signals, and UI rebuild — difficult mid-season |
| Player ID fragmentation discovered after multi-source integration | MEDIUM | Build ID crosswalk table from nflverse ff_playerids; run backfill job to reconcile existing records |
| Weather data stale at game time and recommendation is wrong | LOW | Add higher-frequency weather refresh job; communicate to users that weather data is now updated every 6 hours |
| Scope creep delays core features | MEDIUM | Cut all in-progress non-core work; ship the minimal viable start/sit feature; validate before resuming backlog |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| ESPN API instability | Data infrastructure (Phase 1) | Adapter layer exists; ESPN URL referenced in exactly one file; cache is present and tested |
| No reasoning signals in data model | Recommendation engine (Phase 2) | Recommendation record schema includes injury_status, matchup_grade, snap_pct, target_share |
| Off-season / season-state gap | Data infrastructure (Phase 1) | Season-state model exists; app renders correct state when no active NFL week |
| Player ID fragmentation | Data infrastructure (Phase 1) | ID mapping table exists; all joins use numeric player IDs |
| Small sample recommendation accuracy | Recommendation engine (Phase 2) | Confidence flag shown for players with < 4 games of data; trailing window is at least 4 games |
| Stale weather at game time | Data enrichment (Phase 3) | Weather refresh job runs on 6-hour interval Thu-Sun; dome venues excluded from weather signals |
| Scope creep | All phases | Scope gate review at start of each phase; backlog additions do not enter current sprint |

---

## Sources

- ESPN unofficial API breaking changes and authentication requirements: [Zuplo ESPN Hidden API Guide](https://zuplo.com/learning-center/espn-hidden-api-guide), [GitHub cwendt94/espn-api](https://github.com/cwendt94/espn-api), [Steven Morse ESPN Fantasy v3 migration](https://stmorse.github.io/journal/espn-fantasy-v3.html)
- ESPN API commercial use and ToS concerns: [Ask HN: How to legally obtain sports data for commercial use](https://news.ycombinator.com/item?id=1791588)
- Recommendation accuracy benchmarks (54-67% range): [LinkedIn — Whose Fantasy Football Start/Sit Advice is Most Accurate](https://www.linkedin.com/pulse/whose-fantasy-football-start-em-sit-advice-most-accurate-kurt-scherf)
- Projection accuracy limitations and recency bias: [Fantasy Football Analytics — Projection Bias](https://fantasyfootballanalytics.net/2025/07/fantasy-football-projections-exploring-positional-bias-in-projections.html), [footballsiao.com — How Accurate Are Fantasy Football Projections](https://footballsiao.com/how-accurate-are-fantasy-football-projections/)
- Player ID crosswalk: [nflreadr ff_playerids data dictionary](https://nflreadr.nflverse.com/articles/dictionary_ff_playerids.html), [Sportradar NFL ID Handling](https://developer.sportradar.com/football/docs/nfl-ig-id-handling)
- nfl_data_py archival and 2025 injury data gap: [nflverse/nfl_data_py GitHub](https://github.com/nflverse/nfl_data_py), [nflreadpy](https://github.com/nflverse/nflreadpy)
- nflverse data update schedule: [nflreadr data availability schedule](https://nflreadr.nflverse.com/articles/nflverse_data_schedule.html)
- Weather integration: [NFL Operations Gameday Weather](https://operations.nfl.com/updates/football-ops/nfl-operations-gameday-weather-forecast/), [FantasyNerds NFL Weather](https://www.fantasynerds.com/nfl/weather)
- Data update frequency benchmarks: [SportsDataIO content update frequency](https://sportsdata.io/developers/content-update-frequency)
- Sleeper API reliability comparison: [Zuplo Sleeper API guide](https://zuplo.com/learning-center/sleeper-api), [SportFirst — Sleeper vs Other APIs](https://www.sportsfirst.net/post/fantasy-sports-data-apis-sleeper-api-vs-other-sports-apis-compared)
- Transparency as differentiator in start/sit tools: [Rotowire — Common Start/Sit Mistakes](https://www.rotowire.com/football/article/common-fantasy-football-start-sit-mistakes-97758)

---
*Pitfalls research for: Fantasy football analytics — start/sit recommendation engine*
*Researched: 2026-03-19*
