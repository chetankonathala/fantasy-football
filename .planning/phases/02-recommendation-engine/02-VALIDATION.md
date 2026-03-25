---
phase: 2
slug: recommendation-engine
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-25
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=9.0.2 |
| **Config file** | `pyproject.toml` [tool.pytest.ini_options] — testpaths=["tests"], addopts="-x -q" |
| **Quick run command** | `uv run pytest tests/test_engine.py -x -q` |
| **Full suite command** | `uv run pytest -x -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_engine.py -x -q`
- **After every plan wave:** Run `uv run pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 0 | RECD-01, RECD-02, RECD-03, RECD-06, RECD-07, RECD-08, POS-01, POS-02, POS-03 | unit stubs | `uv run pytest tests/test_engine.py -x -q` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | RECD-01 | unit | `uv run pytest tests/test_engine.py::test_verdict_enum tests/test_engine.py::test_threshold_boundaries -x` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 1 | RECD-01 | unit | `uv run pytest tests/test_engine.py::test_out_always_sit tests/test_engine.py::test_doubtful_always_sit tests/test_engine.py::test_score_clamped -x` | ❌ W0 | ⬜ pending |
| 02-01-04 | 01 | 1 | RECD-02 | unit | `uv run pytest tests/test_engine.py::test_reasons_count tests/test_engine.py::test_reasons_order -x` | ❌ W0 | ⬜ pending |
| 02-01-05 | 01 | 1 | RECD-03, RECD-06, RECD-07, RECD-08 | unit | `uv run pytest tests/test_engine.py::test_matchup_signal_effect tests/test_engine.py::test_projected_points_none tests/test_engine.py::test_ppr_boosts_pass_catcher tests/test_engine.py::test_ppr_no_effect_qb tests/test_engine.py::test_low_confidence_flag tests/test_engine.py::test_k_dst_no_low_confidence -x` | ❌ W0 | ⬜ pending |
| 02-01-06 | 01 | 1 | POS-01, POS-02, POS-03 | unit | `uv run pytest tests/test_engine.py::test_all_skill_positions tests/test_engine.py::test_kicker_position tests/test_engine.py::test_dst_position -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_engine.py` — all engine unit tests covering all phase requirements; file does not exist yet
- [ ] `src/fantasy/engine.py` — the engine module itself; file does not exist yet (Wave 0 creates stubs)

*conftest.py and pytest config exist from Phase 1 — no new framework setup needed.*

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
