---
phase: 1
slug: data-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-21
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (latest) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` — Wave 0 installs |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 0 | DATA-01 | unit | `pytest tests/test_sleeper.py::test_player_upsert -x` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 0 | DATA-01 | integration | `pytest tests/test_refresh.py::test_refresh_runs -x` | ❌ W0 | ⬜ pending |
| 1-01-03 | 01 | 0 | DATA-03 | unit | `pytest tests/test_refresh.py::test_offseason_guard -x` | ❌ W0 | ⬜ pending |
| 1-01-04 | 01 | 0 | DATA-03 | unit | `pytest tests/test_refresh.py::test_inseason_runs -x` | ❌ W0 | ⬜ pending |
| 1-01-05 | 01 | 0 | DATA-01 | unit | `pytest tests/test_nflverse.py::test_pbp_schema -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_sleeper.py` — unit tests for DATA-01 player upsert with correct field types; mock Sleeper API response fixture
- [ ] `tests/test_nflverse.py` — validates PBP schema columns (defteam, posteam, week, season; fantasy point columns); carry_share derivation logic
- [ ] `tests/test_refresh.py` — covers DATA-01 scheduled refresh end-to-end; DATA-03 off-season guard (`season_active=False` when week > 22)
- [ ] `tests/conftest.py` — shared fixtures: in-memory SQLite engine, mock Sleeper API response, mock nflreadpy returns
- [ ] `uv add --dev pytest` — not yet installed (greenfield project)
- [ ] `pyproject.toml` `[tool.pytest.ini_options]` — testpaths, addopts configuration

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| cron job fires every 2 hours and DB updates | DATA-01 | Requires system cron environment; cannot be reliably mocked in unit tests | 1. Install crontab entry `0 */2 * * * /path/.venv/bin/python /path/scripts/refresh.py`. 2. Wait for next 2-hour boundary. 3. Check `logs/refresh.log` for "Refresh complete" entry. 4. Verify `data/fantasy.db` `updated_at` timestamps changed. |
| Off-season state returns "season not active" | DATA-03 | Requires mocking `nfl.get_current_week()` to return week 23+ | `pytest tests/test_refresh.py::test_offseason_guard -x` covers unit; manual check: run `python scripts/refresh.py` with `get_current_week` returning 23, verify log contains `season_active=false` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
