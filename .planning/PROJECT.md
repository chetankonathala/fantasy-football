# Fantasy Football Analytics

## What This Is

A fantasy football analytics website that surfaces clear, reasoned start/sit recommendations each week of the NFL season. It consolidates injury reports, matchup data, usage trends, and player stats into actionable advice — built first for personal use, with the potential to open up to other fantasy players. Targets ESPN Fantasy players pulling data from existing NFL/sports data APIs.

## Core Value

Give a clear start/sit recommendation with transparent reasoning (matchup grade, injury status, recent usage) so the user can stop second-guessing and win more weeks without spending hours on research.

## Requirements

### Validated

- [x] Player data is sourced from an existing NFL data API (Sleeper + nflreadpy/nflverse) — Validated in Phase 1: Data Foundation
- [x] Recommendations update throughout the week as new info comes in (2-hour cron refresh) — Validated in Phase 1: Data Foundation

### Active

- [ ] User can look up any NFL player and see a start/sit recommendation for the current week
- [ ] Each recommendation shows reasoning (matchup grade, injury status, recent target/snap usage)
- [ ] Site covers all fantasy-relevant positions (QB, RB, WR, TE, K, DST)

### Out of Scope

- ESPN roster sync / OAuth login — manual player lookup is sufficient for v1
- Full league management — this is an analytics tool, not a platform replacement
- Mobile app — web-first

## Context

- User currently tabs between ESPN, beat reporters, FantasyPros, weather sites, and stats trackers to form their own start/sit decisions each week
- The core frustration is time spent aggregating fragmented information — the site replaces that with a single interface
- Trust in recommendations comes from visible reasoning, not just a ranking — users want to understand WHY a player should start or sit
- Data will come from an existing NFL data API (ESPN unofficial API, Sleeper API, or a paid provider like SportRadar / MySportsFeeds)
- Plays on ESPN Fantasy — ESPN player IDs and roster structure are relevant

## Constraints

- **Data**: Must use an existing NFL data API — no manual data entry
- **Timing**: Recommendations must be relevant week-to-week during the NFL season (Week 1–18 + playoffs)
- **Scope**: v1 is a personal tool — no multi-user auth, no subscription infrastructure

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| ESPN Fantasy as primary platform | User plays on ESPN; ESPN player IDs provide alignment | — Pending |
| Show reasoning alongside recommendation | Trust comes from transparency, not just a score | — Pending |
| Web app (not mobile) | Web-first, keep scope tight for v1 | — Pending |

## Current State

Phase 1 complete — data pipeline operational. SQLite DB with Player (28 cols) + Matchup tables, Sleeper API client, nflreadpy wrappers (stats/snaps/DVP), normalization layer, refresh orchestrator with off-season guard. 30 tests passing. Ready for Phase 2: Recommendation Engine.

---
*Last updated: 2026-03-22 after Phase 1: Data Foundation*
