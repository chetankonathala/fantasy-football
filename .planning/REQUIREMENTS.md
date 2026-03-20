# Requirements: Fantasy Football Analytics

**Defined:** 2026-03-19
**Core Value:** Give a clear start/sit recommendation with transparent reasoning so the user can stop second-guessing and win more weeks without spending hours on research.

## v1 Requirements

### Search

- [ ] **SRCH-01**: User can search for any NFL player by name and see autocomplete suggestions
- [ ] **SRCH-02**: User can select a player from search results and view their recommendation page

### Recommendation

- [ ] **RECD-01**: User can see a clear START / SIT / FLEX verdict for any player for the current week
- [ ] **RECD-02**: Each recommendation includes a structured reasoning narrative (3-5 plain-English factors behind the call)
- [ ] **RECD-03**: User can see the matchup grade (opponent rank vs. position, based on DVP — points allowed to position)
- [ ] **RECD-04**: User can see the player's injury / practice status (Q/D/Out) on the recommendation page
- [ ] **RECD-05**: User can see usage trends for the player over the last 3-4 weeks (snap %, target share for WR/TE, carry share for RB)
- [ ] **RECD-06**: User can see projected fantasy points for the player for the current week
- [ ] **RECD-07**: User can select scoring format (PPR / half-PPR / standard) and have recommendation update accordingly
- [ ] **RECD-08**: Low-confidence recommendations (fewer than 4 games of data) are visibly flagged to the user

### Positions

- [ ] **POS-01**: Recommendations are available for QB, RB, WR, and TE positions (skill positions using full signal set)
- [ ] **POS-02**: Recommendations are available for K (Kicker) using matchup-based signals (defense allowed to kickers)
- [ ] **POS-03**: Recommendations are available for DST (Defense/Special Teams) using opponent offense rank

### Data Freshness

- [ ] **DATA-01**: Injury / practice status refreshes automatically throughout the week (not just once on Monday)
- [ ] **DATA-02**: Each recommendation card shows a data freshness timestamp so user knows how current the data is
- [ ] **DATA-03**: App shows a clear "season not active" state during the NFL off-season rather than stale data

### Comparison & Enrichment

- [ ] **COMP-01**: User can compare two players side-by-side (A vs. B view) to make a direct start/sit decision
- [ ] **ENRI-01**: User can see a Vegas implied team total overlay alongside the recommendation
- [ ] **ENRI-02**: User can see a weather flag for outdoor games (pass game suppression signal)

## v2 Requirements

### Historical Tracking

- **HIST-01**: App tracks recommendation accuracy over a full season and shows historical win rate
- **HIST-02**: User can view past week recommendations and compare to actual player outcomes

### Roster Integration

- **ROST-01**: User can connect ESPN Fantasy league to see their actual roster automatically
- **ROST-02**: App generates a full lineup recommendation based on connected roster

### Notifications

- **NOTF-01**: User receives alerts when a player's injury status changes during the week
- **NOTF-02**: User receives weekly summary with recommended lineup before Sunday lock

## Out of Scope

| Feature | Reason |
|---------|--------|
| League management (standings, transactions) | ESPN already handles this; not analytics |
| DFS lineup optimization | Different product surface and data problem |
| Trade analyzer | Requires dynasty/ROS values — separate product |
| Waiver wire recommendations | Requires roster context and FAAB strategy |
| AI chatbot / natural language interface | Structured reasoning narrative achieves the same goal without LLM overhead |
| Social / community features | Changes product type entirely |
| Mobile native app | Responsive web handles Sunday couch use |
| SportRadar / paid enterprise data | Overkill cost for a personal v1 tool |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 1 | Pending |
| DATA-03 | Phase 1 | Pending |
| RECD-01 | Phase 2 | Pending |
| RECD-02 | Phase 2 | Pending |
| RECD-03 | Phase 2 | Pending |
| RECD-06 | Phase 2 | Pending |
| RECD-07 | Phase 2 | Pending |
| RECD-08 | Phase 2 | Pending |
| POS-01 | Phase 2 | Pending |
| POS-02 | Phase 2 | Pending |
| POS-03 | Phase 2 | Pending |
| SRCH-01 | Phase 3 | Pending |
| SRCH-02 | Phase 3 | Pending |
| RECD-04 | Phase 3 | Pending |
| RECD-05 | Phase 3 | Pending |
| DATA-02 | Phase 3 | Pending |
| COMP-01 | Phase 4 | Pending |
| ENRI-01 | Phase 4 | Pending |
| ENRI-02 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 19 total
- Mapped to phases: 19
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-19*
*Last updated: 2026-03-19 after roadmap creation*
