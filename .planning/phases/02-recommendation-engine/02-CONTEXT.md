# Phase 2: Recommendation Engine - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning

<domain>
## Phase Boundary

A pure scoring function that converts typed player signals into a deterministic START/SIT/FLEX verdict plus a structured 3-5 factor reasoning array. Covers all six fantasy positions. No UI, no API routes, no data fetching — the engine is isolated from all I/O. API routes and rendering are Phase 3.

</domain>

<decisions>
## Implementation Decisions

### Scoring Thresholds
- Fixed numeric cutoffs: score 0–100, where ≥70 = START, 45–69 = FLEX, <45 = SIT
- Fixed weights per signal type (not position-relative): matchup grade, usage trend, injury penalty, projected points, confidence
- Injury status is a **hard veto**: `Out` always = SIT regardless of score; `Doubtful` forces SIT; `Questionable` applies a score penalty
- Low-confidence threshold: players with fewer than 4 weeks of usage data receive a `low_confidence` flag (per RECD-08)

### Projected Points (RECD-06)
- `projected_points` is a **pass-through input** — the engine accepts it as a typed signal, does not fetch or compute it
- If `projected_points` is `None` (off-season, new player, missing data), it is excluded from scoring — its weight redistributes to remaining signals
- Projected points **directly affect the composite score** (not just reasoning)
- Scoring format (PPR / half-PPR / standard) adjusts **both** projected points value AND signal weights (e.g., PPR increases target share weight and bumps projected points for pass-catchers)

### Reasoning Narrative Format (RECD-02)
- **Structured template strings** — fixed per-signal templates, not free-form sentences
  - Example: `"Favorable matchup: #3 defense vs WR"`, `"Strong usage: 82% snap share (L4W)"`, `"Injury risk: Questionable (hamstring)"`
- **Always 3–5 factors** — if fewer signals are available (K, DST), pad with low-confidence or context notes to reach minimum 3
- **Priority order** — most impactful signal leads: hard veto reasons first (injury Out), then matchup, then usage, then projection, then confidence flag
- **Lead with a summary reason** — first factor states the primary reason for the verdict: `"Strong START: elite matchup + high usage"`

### K and DST Signal Sets (POS-02, POS-03)
- **K (Kicker):** `matchup_rank` (opponent rank vs kickers from DVP) + `vegas_implied_team_total` as signals
  - `vegas_implied_team_total` is an optional pass-through input — treated as `None` in Phase 2 (Vegas data is Phase 4 scope, ENRI-01)
- **DST:** `opponent_offense_rank` (opponent rank vs DST from DVP) + `opponent_implied_points` (Vegas implied points opponent is expected to score)
  - `opponent_implied_points` is an optional pass-through input — treated as `None` in Phase 2
- **No low-confidence flag for K/DST** — these positions have no snap/target/carry usage data; RECD-08 only applies to skill positions (QB, RB, WR, TE)

### Claude's Discretion
- Exact numeric weight values for each signal (e.g., matchup = 40%, usage = 30%) — pick sensible defaults
- How weight redistribution works when optional signals are None
- Internal score normalization approach
- Test fixture design for representative per-position inputs

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — Full v1 requirements; Phase 2 covers RECD-01, RECD-02, RECD-03, RECD-06, RECD-07, RECD-08, POS-01, POS-02, POS-03

### Data models (integration points)
- `src/fantasy/db/models.py` — Player and Matchup ORM models; engine inputs are derived from these columns
- `src/fantasy/normalize.py` — Normalization layer output; defines what data is guaranteed to be available as signals

### Roadmap
- `.planning/ROADMAP.md` §Phase 2 — Success criteria and signal contract for this phase

No external ADRs or design specs — requirements fully captured in decisions above and REQUIREMENTS.md.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/fantasy/db/models.py` `Player` — injury_status, practice_participation, week1-4 snap/target/carry stats, matchup_id (all available as engine inputs)
- `src/fantasy/db/models.py` `Matchup` — opponent_rank (1–32), dvp_score (raw pts allowed); rank 1 = most points allowed = easiest matchup
- `src/fantasy/db/base.py` — SQLAlchemy Base; no reuse needed in engine (engine is pure, no DB access)

### Established Patterns
- Pure function contract (PlayerSignals → Recommendation) was decided pre-build — engine has no I/O, no DB access, no API calls
- Reasoning stored as structured fields at scoring time, not computed at render time
- `week1` = most recent week, `week4` = oldest (4 weeks ago) — maintain this convention in signal naming

### Integration Points
- Engine output schema becomes the contract for Phase 3 API routes — define `Recommendation` dataclass/TypedDict carefully; Phase 3 builds against it
- `scripts/refresh.py` populates the Player/Matchup tables the engine reads from — engine is downstream of this

</code_context>

<specifics>
## Specific Ideas

- No specific product references or "I want it like X" moments — open to standard approaches for scoring implementation
- Scoring format selector (PPR/half-PPR/standard) must propagate through cleanly — this is the user-facing knob in RECD-07

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-recommendation-engine*
*Context gathered: 2026-03-25*
