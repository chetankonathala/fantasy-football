---
phase: 3
slug: full-stack-core
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-25
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x (already installed) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (exists) |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_api.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 3-01-01 | 01 | 0 | SRCH-01 | unit | `uv run pytest tests/test_api.py::test_search_returns_autocomplete -x` | ❌ Wave 0 | ⬜ pending |
| 3-01-02 | 01 | 0 | SRCH-01 | unit | `uv run pytest tests/test_api.py::test_search_min_chars -x` | ❌ Wave 0 | ⬜ pending |
| 3-01-03 | 01 | 0 | SRCH-01 | unit | `uv run pytest tests/test_api.py::test_search_no_results -x` | ❌ Wave 0 | ⬜ pending |
| 3-02-01 | 02 | 0 | SRCH-02 | integration | `uv run pytest tests/test_api.py::test_player_detail_returns_recommendation -x` | ❌ Wave 0 | ⬜ pending |
| 3-02-02 | 02 | 0 | RECD-04 | unit | `uv run pytest tests/test_api.py::test_player_detail_injury_fields -x` | ❌ Wave 0 | ⬜ pending |
| 3-02-03 | 02 | 0 | RECD-05 | unit | `uv run pytest tests/test_api.py::test_player_detail_usage_fields -x` | ❌ Wave 0 | ⬜ pending |
| 3-02-04 | 02 | 0 | DATA-02 | unit | `uv run pytest tests/test_api.py::test_player_detail_updated_at -x` | ❌ Wave 0 | ⬜ pending |
| 3-02-05 | 02 | 0 | SRCH-02 | unit | `uv run pytest tests/test_api.py::test_player_format_selector -x` | ❌ Wave 0 | ⬜ pending |
| 3-03-01 | 03 | 0 | SRCH-02 | unit | `uv run pytest tests/test_sleeper.py::test_fetch_projected_points_fallback -x` | ❌ Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_api.py` — FastAPI TestClient tests for `/search` and `/player/{id}`; covers SRCH-01, SRCH-02, RECD-04, RECD-05, DATA-02
- [ ] `tests/test_sleeper.py` — extend existing file with `test_fetch_projected_points_fallback` (mock requests.get to raise HTTPError, assert None returned)
- [ ] FastAPI `TestClient` is available via `from fastapi.testclient import TestClient` — no extra install needed (bundled with FastAPI)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Search autocomplete renders in UI with player name, position, team | SRCH-01 | Frontend rendering | Type 3+ chars in search field, confirm dropdown appears with correct data |
| Recommendation card displays verdict, reasoning, injury status, usage trends | SRCH-02, RECD-04, RECD-05 | Frontend rendering | Select a player, verify all signals visible on page |
| Data freshness timestamp displayed and readable | DATA-02 | Frontend rendering | Verify timestamp is shown in human-readable relative format |
| Scoring format selector changes verdict/projected points without page reload | RECD-05 | Frontend interactivity | Click PPR/half-PPR/standard, verify verdict updates without full navigation |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
