# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-19)

**Core value:** Give a clear start/sit recommendation with transparent reasoning (matchup grade, injury status, recent usage) so the user can stop second-guessing and win more weeks without spending hours on research.
**Current focus:** Phase 1 — Data Foundation

## Current Position

Phase: 1 of 4 (Data Foundation)
Plan: 0 of TBD in current phase
Status: Ready to plan
Last activity: 2026-03-19 — Roadmap created, requirements mapped, ready to begin Phase 1 planning

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: -
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: -
- Trend: -

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Pre-build]: Primary data source is Sleeper API (injury/metadata) + nflreadpy/nflverse (stats, snap counts, matchup data); ESPN unofficial API is a fallback only, wrapped behind a single adapter
- [Pre-build]: Canonical player ID system uses nflverse ff_playerids crosswalk; never join on player name strings
- [Pre-build]: DVP matchup grades computed from nflreadpy play-by-play (points allowed by position, last 4 weeks) rather than scraped from FantasyPros
- [Pre-build]: Recommendation engine is a pure function (PlayerSignals -> Recommendation); reasoning stored as structured fields, not computed at render time

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 1 pre-condition]: nflreadpy is marked "experimental" by nflverse; pin to v0.1.5 and validate play-by-play schema against DVP computation approach before committing in Phase 1
- [Phase 1 pre-condition]: ESPN espn_s2 cookie is ephemeral; acceptable for personal use but must be documented as a manual refresh step

## Session Continuity

Last session: 2026-03-19
Stopped at: Roadmap created — Phase 1 ready to plan
Resume file: None
