# Feature Research

**Domain:** Fantasy football start/sit analytics (weekly lineup decisions)
**Researched:** 2026-03-19
**Confidence:** MEDIUM-HIGH (competitor analysis via WebSearch + WebFetch; no direct user interviews)

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete or untrustworthy.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Player search by name | Entry point — users think "should I start Davante Adams?" | LOW | ESPN API player lookup; autocomplete helpful but not required for v1 |
| Clear START or SIT verdict | Users want a decision, not a pile of data | LOW | Single recommendation label per player (Start / Sit / Flex) |
| Visible reasoning behind recommendation | Trust requires transparency — users distrust black-box scores | MEDIUM | Must surface the top 2-3 factors driving the call (see sub-bullets below) |
| — Matchup grade | Every serious platform shows opponent rank vs. position (e.g. "faces #31 defense vs WR") | MEDIUM | Requires per-position defensive rankings, updated weekly |
| — Injury/practice status | Questionable tag affects entire recommendation | LOW | ESPN API surfaces injury designations (Q/D/Out); must be current |
| — Recent usage trends (snap %, target share, carry share) | Opportunity predicts production — every data-driven tool shows this | MEDIUM | Requires 3-4 week rolling average; ESPN or Sleeper API provides game logs |
| Coverage of all fantasy positions | QB, RB, WR, TE, K, DST — gaps feel like a broken product | MEDIUM | K and DST have different signal inputs than skill positions |
| Weekly updates throughout NFL season | Data must reflect current week's matchup, not last week's | MEDIUM | Requires scheduled data refresh pipeline (at minimum daily during the week) |
| Player projection (projected points) | FantasyPros, DraftSharks, FTN — all show projected fantasy score | MEDIUM | Can source from ESPN API or compute from usage + opponent data; scoring format matters (PPR vs standard) |
| Scoring format awareness | Half-PPR vs PPR vs Standard changes target-share weight significantly | LOW | Must be configurable or at minimum match ESPN's default (PPR most common) |

### Differentiators (Competitive Advantage)

Features that set the product apart. Aligned with core value: "clear recommendation with transparent reasoning."

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Transparent multi-factor reasoning narrative | Competitors show data tables; this product explains the logic in plain English (e.g. "Start — WR24 on the season, faces #31 CB unit, 28% target share last 3 weeks, no injury flag") | MEDIUM | Templated text generation from structured signals; does not require LLM for v1 |
| Floor / ceiling range alongside projected points | Users need both the safe floor (for when leading in points) and the upside ceiling (when trailing); DraftSharks strategy slider models this | MEDIUM | Percentile-based projection range; requires historical variance per position type |
| Matchup grade as a visual signal (color/letter) | Quick scannable verdict — green A-grade matchup vs. red D-grade — reduces cognitive load | LOW | Defensive rank bucketed into A/B/C/D/F; purely display logic once data exists |
| Snap count and target share trend display | Shows whether a player's role is growing or shrinking, not just their current stat line | MEDIUM | 4-week rolling trend visualization; more actionable than season averages alone |
| Vegas game total and implied team points | Correlated with fantasy scoring — high-total games produce more fantasy points; several platforms integrate this | MEDIUM | Requires Vegas odds API (free tiers available: the-odds-api.com); adds credibility |
| Weather flag for outdoor games | Wind > 15 mph or rain suppresses passing game; a single warning flag is enough | LOW | Weather API is straightforward; only matters for outdoor stadiums; flag rather than block |
| Position-specific signal weighting | QB signals differ from TE signals — volume matters less for QB, matchup matters more for TE | MEDIUM | Configuration layer on recommendation engine, not a new data source |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem like natural additions but would derail v1 scope.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| ESPN OAuth roster sync | "Show me my whole lineup" — saves manual player lookups | Auth flow, token refresh, OAuth compliance, ESPN ToS risk; doubles scope for marginal benefit | Manual player search per lookup; v1 is a personal tool so roster is already memorized |
| AI chatbot / natural language interface | "Just ask it 'should I start X or Y'" — feels modern | Adds LLM infrastructure, prompt engineering, cost per query, latency; reasoning already shown in structured form | Structured reasoning narrative achieves same goal without chat UI complexity |
| Trade analyzer | Logical extension — "is this trade good for me?" | Different data problem (dynasty value, rest-of-season rankings); not start/sit; doubles scope | Out of scope; refer to KTC or FantasyPros trade tool |
| Waiver wire recommendations | "Who should I pick up?" | Requires roster-level context (what you already have), FAAB strategy, league size; fundamentally different from start/sit | Out of scope for v1; different product surface |
| Historical accuracy tracking / backtesting display | "How accurate were your picks last season?" | Requires storing recommendation history, actual NFL outcomes, retroactive matching; significant data pipeline and storage work | Defer to v2 after at least one full season of data |
| League management (standings, scores, transactions) | Makes the tool "complete" | Not an analytics tool anymore — becomes a platform replacement; ESPN already does this | Stick to analytics; link to ESPN for league management |
| Social/community features (polls, forums, comments) | Crowdsourced wisdom is valuable (KeepTradeCut does this) | Community requires moderation, user accounts, retention mechanics; fundamentally changes product type | Single authoritative recommendation with visible reasoning is more actionable than crowd polls |
| News feed / beat reporter integration | "All my info in one place" | Requires parsing unstructured news, NLP, source aggregation; maintenance overhead without direct analytics value | Surface injury designation (Q/D/Out) from API instead of linking to articles |
| DFS (daily fantasy) optimization | Power users want DFS lineups | DFS has different scoring, salary constraints, and ownership % concerns; a separate product surface | Out of scope; FTN and 4for4 own this vertical |
| Mobile app | "I want this on my phone during Sunday" | Web-responsive design delivers mobile utility; native app doubles dev surface for v1 | Responsive web layout handles Sunday couch use without a separate codebase |

---

## Feature Dependencies

```
[Player Search]
    └──requires──> [ESPN API Player Data]
                       └──requires──> [Data Refresh Pipeline]

[START/SIT Recommendation]
    └──requires──> [Player Search]
    └──requires──> [Matchup Grade]
                       └──requires──> [Defensive Position Rankings]
                                          └──requires──> [Data Refresh Pipeline]
    └──requires──> [Injury Status]
                       └──requires──> [Data Refresh Pipeline]
    └──requires──> [Usage Trends (snap%, target share)]
                       └──requires──> [Game Log Data]
                                          └──requires──> [Data Refresh Pipeline]

[Reasoning Narrative]
    └──requires──> [START/SIT Recommendation] (all signals must exist to narrate)

[Floor/Ceiling Range]
    └──enhances──> [Projected Points]
    └──requires──> [Historical variance data by position]

[Vegas Implied Points]
    └──enhances──> [Matchup Grade] (adds game-script context)
    └──requires──> [Vegas Odds API integration]

[Weather Flag]
    └──enhances──> [START/SIT Recommendation] (modifies confidence for outdoor games)
    └──requires──> [Stadium location data + Weather API]

[Scoring Format Config]
    └──modifies──> [Projected Points] (target share weight changes by format)
    └──modifies──> [Usage Trends] (targets matter more in PPR)
```

### Dependency Notes

- **Data Refresh Pipeline is the foundation:** Every user-facing feature depends on data being current. The pipeline must land in Phase 1 or everything else is blocked.
- **Matchup Grade requires Defensive Position Rankings:** Weekly opponent strength per position must be computed or sourced before any recommendation can be generated.
- **Reasoning Narrative requires all signals:** The narrative is downstream of matchup + injury + usage data all being available for a player. Partial data produces a degraded or incomplete explanation.
- **Vegas and Weather are enhancements:** These are additive overlays on an already-functioning recommendation. They do not block v1 launch.
- **Floor/Ceiling requires historical variance data:** This is a nice differentiator but requires a secondary data pass (historical game logs to compute range). Can be approximated with position-based variance heuristics in v1.

---

## MVP Definition

### Launch With (v1)

Minimum viable product — what's needed for the core use case: "look up a player, get a clear start/sit call with visible reasoning."

- [ ] Player search by name — entry point to the tool
- [ ] ESPN API integration for player stats, injury status, and game logs — foundation for all signals
- [ ] Weekly matchup grade per position (opponent rank vs. position) — most critical single signal
- [ ] Injury/practice status display (Q/D/Out) — must be current, updated daily during the week
- [ ] Usage trends display (snap %, target share / carry share, last 3-4 weeks) — shows role stability or growth
- [ ] Projected points output (computed or sourced) — gives users a numeric anchor
- [ ] Clear START / SIT / FLEX verdict label — the actual decision the tool exists to make
- [ ] Structured reasoning summary (3-5 bullet factors behind the call) — the transparency that builds trust
- [ ] Covers all positions: QB, RB, WR, TE, K, DST

### Add After Validation (v1.x)

Features to add once core recommendation loop is working and validated.

- [ ] Floor / ceiling range alongside projected points — add when projection accuracy is trusted
- [ ] Vegas implied team total overlay — add when core matchup data pipeline is stable
- [ ] Weather flag for outdoor games — low-effort add-on once other data is flowing
- [ ] Matchup grade visual (letter grade + color coding) — polish layer after logic is proven
- [ ] Player comparison view (A vs. B side-by-side) — most common real-world use case after individual lookup

### Future Consideration (v2+)

Features to defer until there is at least one season of production data and validated user needs.

- [ ] Historical recommendation accuracy tracker — requires a full season of logged recommendations + outcomes
- [ ] Roster-level lineup optimizer — requires user accounts or roster context; platform-level feature
- [ ] Waiver wire pickup recommendations — different product surface; deferred
- [ ] Dynasty / keeper scoring overlays — niche audience; deferred
- [ ] ESPN roster sync — reduces manual lookup friction; high integration risk; defer until product value is proven

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Player search (name lookup) | HIGH | LOW | P1 |
| START/SIT verdict label | HIGH | LOW | P1 |
| Injury/practice status | HIGH | LOW | P1 |
| Matchup grade (opponent rank vs. position) | HIGH | MEDIUM | P1 |
| Usage trends (snap %, target/carry share) | HIGH | MEDIUM | P1 |
| Structured reasoning narrative | HIGH | MEDIUM | P1 |
| Projected points | MEDIUM | MEDIUM | P1 |
| All positions covered (QB/RB/WR/TE/K/DST) | HIGH | MEDIUM | P1 |
| Scoring format awareness (PPR/standard) | MEDIUM | LOW | P1 |
| Floor / ceiling range | MEDIUM | MEDIUM | P2 |
| Player comparison view (A vs. B) | HIGH | MEDIUM | P2 |
| Vegas implied team total | MEDIUM | MEDIUM | P2 |
| Weather flag | MEDIUM | LOW | P2 |
| Matchup grade visual (letter + color) | LOW | LOW | P2 |
| Historical accuracy tracking | LOW | HIGH | P3 |
| Waiver wire recommendations | MEDIUM | HIGH | P3 |
| ESPN OAuth roster sync | MEDIUM | HIGH | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

---

## Competitor Feature Analysis

| Feature | FantasyPros | DraftSharks | KeepTradeCut | StartBench | Our Approach |
|---------|------------|-------------|--------------|------------|--------------|
| START/SIT verdict | Yes (expert consensus) | Yes (algorithmic) | Yes (crowdsourced) | Yes (AI + Vegas) | Yes — algorithmic with structured reasoning |
| Reasoning shown | Partial (article links) | Partial (stat overlay) | No (crowd rank only) | Partial (data bullets) | Full — primary differentiator |
| Matchup grade | Yes | Yes | Minimal | Yes | Yes |
| Injury status | Yes | Yes | Minimal | Yes | Yes |
| Usage trends | Limited (requires nav) | Yes | No | Yes | Yes — front-and-center |
| Floor/ceiling | No (start/sit) | Yes (strategy slider) | No | No | v1.x |
| Vegas integration | No (start/sit) | No | No | Yes | v1.x |
| Weather flag | No (articles only) | No | No | No | v1.x — low-effort differentiator |
| Scoring format support | Yes (premium) | Yes | No | Yes | Yes (PPR default; configurable) |
| ESPN roster sync | Yes (premium) | Partial | No | Yes (multiple) | Out of scope v1 |
| Player comparison UI | Yes | Yes | Yes | Yes | v1.x (P2) |

**Key insight:** No competitor makes transparent reasoning the primary UI element. Most show data tables; users must synthesize the story themselves. The core differentiator for this product is surfacing the "why" directly alongside the "what."

---

## Sources

- FantasyPros start/sit tool and feature support docs: https://support.fantasypros.com/hc/en-us/articles/26339296287899-What-tools-do-you-have-for-Start-Sit-decisions
- DraftSharks start/sit tool overview: https://www.draftsharks.com/kb/fantasy-football-start-sit
- KeepTradeCut start/sit tool (crowdsourced rankings): https://keeptradecut.com/fantasy/start-sit-tool
- StartBench.com feature set: https://startbench.com/
- PFF matchup tool methodology: https://www.pff.com/tools/matchups
- Yahoo Sports: how to make start/sit decisions (signal weights): https://sports.yahoo.com/fantasy-football-advice-how-to-make-start-sit-decisions-rankings-211556515.html
- FantasyPros: how to use Vegas odds for fantasy: https://www.fantasypros.com/2025/09/how-to-use-vegas-odds-fantasy-football/
- Bleacher Nation: floor and ceiling definitions: https://www.bleachernation.com/fantasy-football/2025/08/04/ceiling-floor/
- Decision-driven analytics principle (scope discipline): https://www.gethynellis.com/2026/02/decision-driven-analytics-example.html
- Fantasy Football Analytics scope discussion: https://medium.com/@macha.anrg/from-the-field-to-the-dashboard-engineering-fantasy-football-analytics-5560ff5ddd65

---

*Feature research for: Fantasy football start/sit analytics*
*Researched: 2026-03-19*
