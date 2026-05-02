# Phase C Status Report — I.7

**Spec:** `serp_tool1_improvements_spec.md`
**Date:** 2026-05-02
**Suite:** 419 passed, 5 skipped, 0 errors

---

## I.7 — Add "Old code is not someone else's problem" to `~/.claude/CLAUDE.md`

Phase C is a documentation-and-process phase. I.7 was implemented during Phase A alongside I.4. Recorded here for completeness.

| Criterion | Status | Evidence |
|---|---|---|
| I.7.1 Rule exists in `~/.claude/CLAUDE.md` with adjacent-issues text | **done** | `~/.claude/CLAUDE.md` Rule 8 "Old code is not someone else's problem" |
| I.7.2 Rule's example mentions the externalisation pattern | **done** | Example reads: "when externalising a new trigger list to YAML, look for other hardcoded trigger lists in adjacent files" |

Per flag F5 resolution: the rule was appended as **Rule 8** (not Rule 7) because a different Rule 7 ("Editorial content lives in config files, not code") was already present. Criterion I.7.1 verifies by content, not rule number; the spec language "Rule 7" was treated as a label, not an ordinal.

`docs/spec_coverage.md` includes I.7.1 and I.7.2 rows (added in the Phase B status commit, `4e6e73d`).

---

## Full DoD checklist — Improvements Spec

Per `serp_tool1_improvements_spec.md` end of spec:

| # | Criterion | Status |
|---|---|---|
| 1 | Both Phase A fixes (I.1–I.4) merged | **done** — commits `158ee1a`, `ab8ad13`, `3f2270e`, `dce6424` |
| 2 | `docs/i_phaseA_status_20260501.md` exists | **done** |
| 3 | `pytest -q` reports zero failures after Phase A | **done** — 407 passed |
| 4 | PAA routing and intent triggers live in YAML with no Python constants | **done** |
| 5 | Both Phase B fixes (I.5, I.6) merged | **done** — commits `557c969`, `16ffa8d` |
| 6 | `docs/i_phaseB_status_20260502.md` exists with per-function move history | **done** |
| 7 | `pytest -q` reports zero failures after Phase B | **done** — 419 passed |
| 8 | `couples_therapy` fixture produces output structurally identical to before split | **done** — `tests/test_module_split.py::test_i54_*`, `tests/test_serp_audit_split.py::test_i65_*` |
| 9 | Rule 7 is in user-level `~/.claude/CLAUDE.md` | **done** — appended as Rule 8 per F5 resolution |
| 10 | `docs/spec_coverage.md` includes all I.7 criteria | **done** — rows I.7.1, I.7.2 present |

**All criteria satisfied. Improvements spec complete.**
