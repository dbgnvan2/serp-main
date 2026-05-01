# v2 Definition of Done — Post-Fix Status Report

**Date:** 2026-05-01  
**Auditor:** Claude Sonnet 4.6  
**Branch:** `main` (pending commit)  
**Baseline:** `docs/v2_dod_status_20260501.md` @ commit `8fac920`  
**Tests:** 340 passed, 5 skipped

This document confirms all `PARTIAL` and `NOT DONE` items from the pre-fix status report have been resolved by Fixes 1–8 in `serp_tool1_fix_spec.md`.

---

## DoD Item 1 — Every gap section's acceptance criteria are met

**Status: DONE**

### Gap 1 — SERP intent verdict

| Criterion | Status | Fix | Evidence |
|-----------|--------|-----|---------|
| `intent_mapping.yml` rationale doc | ✅ DONE | Fix 6 | `docs/intent_mapping_rationale.md` — full rule-by-rule rationale with 3 required edge cases |
| `intent_distribution` values are integers | ✅ DONE | Fix 2 | `intent_verdict.py` — distribution stores raw counts |
| `confidence` correctly set (count-based, top-10 denominator) | ✅ DONE | Fix 1 | `generate_content_brief.py` passes `kw_rows[:10]`; `_bucket_confidence` uses count thresholds (≥8 = high, ≥5 = medium) |
| `primary_intent: null` when fewer than 5 classified | ✅ DONE | Fix 1 | `intent_verdict.py` returns `None` when `classified_total < 5` |
| Evidence field names match spec | ✅ DONE | Fix 1 | `organic_url_count`, `classified_organic_url_count`, `uncategorised_organic_url_count`; `intent_counts` removed |
| `local_pack_member_count` in evidence | ✅ DONE | Fix 1 | `compute_serp_intent()` accepts and surfaces `local_pack_member_count` |
| Unit tests for denominator = top-10 only | ✅ DONE | Fix 1 | `test_intent_verdict.py` — `test_denominator_is_organic_rows_only`, `test_null_primary_when_fewer_than_5_classified` |
| `dominant_pattern` contradiction is HARD-FAIL | ✅ DONE | Fix 7 | `partition_validation_issues` routes title_patterns issues to `blocking`; `has_hard_validation_failures` detects them |
| `confidence` contradiction validator (SOFT-FAIL) | ✅ DONE | Fix 7 | `validate_llm_report` detects upgrade phrases; routes via `partition_validation_issues` to `notes` |

### Gap 2 — Title pattern extraction

| Criterion | Status | Evidence |
|-----------|--------|---------|
| All criteria previously DONE | ✅ DONE | No regressions |
| `dominant_pattern` contradiction now HARD-FAIL | ✅ DONE | See Gap 1 Fix 7 row above |

### Gap 3 — Competitor handoff

| Criterion | Status | Fix | Evidence |
|-----------|--------|-----|---------|
| `docs/handoff_contract.md` exists | ✅ DONE | Fix 3 | Full field-by-field schema contract with selection logic and Tool 2 consumption notes |
| Empty organic → `build_competitor_handoff` returns `None` | ✅ DONE | Fix 3 | `serp_audit.py` — returns `None` instead of invalid empty handoff |
| Tests: invalid handoff fails, no organic → None, all-client → empty targets | ✅ DONE | Fix 3 | `test_handoff_schema.py` — 3 new tests added |

### Gap 4 — Mixed-intent advisory framing

| Criterion | Status | Evidence |
|-----------|--------|---------|
| Report surfaces "Per-Keyword SERP Intent" section | ✅ DONE | Fix 4 — `generate_serp_intent_section()` in `generate_content_brief.py`; prepended to output |
| Mixed-intent strategic notes block in report | ✅ DONE | Fix 4 — mixed-intent notes appended to SERP intent section |
| xlsx `Primary_Intent` + `Intent_Confidence` + `SERP_Intent_Detail` sheet | ✅ DONE | Fix 4 — columns injected into `all_metrics`; `SERP_Intent_Detail` sheet added |
| All other Gap 4 criteria previously DONE | ✅ | No regressions |

### Gap 5 — Validation rule consistency check

| Criterion | Status | Evidence |
|-----------|--------|---------|
| All criteria previously DONE | ✅ DONE | No regressions |

---

## DoD Item 2 — pytest passes with new tests

**Status: DONE**

340 passed, 5 skipped. (Up from 332 at baseline.)

New tests added:

| Test file | Tests added |
|-----------|------------|
| `test_intent_verdict.py` | `test_null_primary_when_fewer_than_5_classified`, `test_confidence_high_exactly_8_classified`, `test_denominator_is_organic_rows_only`, `test_evidence_new_field_names`, `test_local_pack_member_count_passed_through` |
| `test_generate_content_brief.py` | `test_validate_llm_report_flags_dominant_pattern_contradiction_hard`, `test_validate_llm_report_flags_confidence_upgrade_soft` |
| `test_handoff_schema.py` | `test_no_organic_returns_none`, `test_all_client_urls_produces_empty_targets`, `test_invalid_handoff_fails_validation` |
| `test_serp_audit.py` | Evidence field name assertions (new/removed names) |

---

## DoD Item 3 — End-to-end run produces JSON with all new fields

**Status: DONE**

All pre-fix failures resolved:

| Issue | Fix | Resolution |
|-------|-----|-----------|
| `intent_distribution` values were fractions | Fix 2 | Now integer counts |
| Evidence field names were wrong | Fix 1 | Renamed to spec names; old names removed |
| `evidence.intent_counts` present (should be removed) | Fix 2 | Removed |
| `confidence: low` for all keywords | Fix 1 | Count-based thresholds on top-10 rows; all 6 keywords now medium or high |
| `primary_intent: null` not implemented | Fix 1 | Returns `None` when `classified_total < 5` |
| `evidence.local_pack_member_count` missing | Fix 1 | Added to evidence block |

Mass-uncategorisation (51% N/A, 16% `other`) addressed by Fix 5:

| Item | Resolution |
|------|-----------|
| `url_pattern_rules.yml` URL-path fallback rules | Created with service, guide, and relationship-specific patterns |
| `classifiers.py` applies URL pattern fallback | `classify_url_from_patterns()` used as fallback in `ContentClassifier.classify()` |
| `generate_content_brief.py` applies pattern fallback for N/A rows | `effective_ct` computed from patterns before passing to intent classification |
| `scripts/classifier_audit.py` diagnostic tool | Created; reports other/N/A URLs by domain with recommended rule additions |
| Residual report | `docs/classifier_residual_20260501.md` — residual N/A is Reddit (correct), unknown entity types (conservative), page 2–3 results (irrelevant) |

---

## DoD Item 4 — Validation/correction loop covers every new pre-computed field

**Status: DONE**

| Field | Validator rule | Severity | Correct? |
|-------|---------------|----------|---------|
| `primary_intent` | Yes | HARD | ✅ |
| `is_mixed` | Yes | HARD | ✅ |
| `dominant_pattern` | Yes | **HARD** | ✅ (Fix 7 — was SOFT) |
| `mixed_intent_strategy` | Yes | SOFT | ✅ |
| `confidence` | Yes | SOFT | ✅ (Fix 7 — new rule) |

Test coverage (one per field, each crafting contradicting LLM output):

| Field | Test |
|-------|------|
| `primary_intent` | `test_validate_llm_report_flags_intent_contradiction_hard` |
| `is_mixed` | `test_validate_llm_report_flags_is_mixed_contradiction` |
| `dominant_pattern` | `test_validate_llm_report_flags_dominant_pattern_contradiction_hard` |
| `mixed_intent_strategy` | `test_validate_llm_report_flags_mixed_keyword_dominance` (non-mixed keyword with backdoor language) |
| `confidence` | `test_validate_llm_report_flags_confidence_upgrade_soft` |

Prompt coverage (grep confirms all 5 fields appear in `prompts/main_report/system.md`):

- `primary_intent` — lines 44, 256, 295
- `is_mixed` — lines 48, 257
- `confidence` — lines 49–50, 255, 260
- `dominant_pattern` — lines 71, 264, 297
- `mixed_intent_strategy` — lines 58–68

---

## DoD Item 5 — Report surfaces mixed-intent strategy

**Status: DONE**

Fix 4 added `generate_serp_intent_section()` which:
- Outputs a "Per-Keyword SERP Intent" section for every run
- Shows primary intent + confidence for each keyword
- Adds a "Mixed-Intent Strategic Notes" block with strategy framing when `is_mixed = True`
- Prepended to output report before LLM-generated sections

---

## DoD Item 6 — Tool 2 strategic briefing

**Status: N/A (Tool 2)** — out of scope.

---

## DoD Item 7 — README documents new fields and handoff contract

**Status: DONE**

| Section | Status | Fix |
|---------|--------|-----|
| "What's new in this version (v2)" table | ✅ DONE | Fix 8 |
| Validator severity note (HARD/SOFT per field) | ✅ DONE | Fix 8 |
| Rule file pointers (`intent_mapping.yml`, `url_pattern_rules.yml`) | ✅ DONE | Fix 8 |
| "Tool 1 → Tool 2 handoff" subsection | ✅ DONE | Fix 8 — points to `docs/handoff_contract.md` |
| "Backwards compatibility note" | ✅ DONE | Fix 8 — pre-v2 JSONs lack new fields; all nullable on read |
| Test count updated (330 → 340) | ✅ DONE | Fix 8 |

---

## DoD Item 8 — No previously-passing test now fails

**Status: DONE**

340 passed, 5 skipped. All tests that passed at baseline (`8fac920`) continue to pass.

---

## Summary table

| DoD Item | Pre-fix | Post-fix |
|----------|---------|---------|
| 1. All gap acceptance criteria met | PARTIAL | ✅ DONE |
| 2. pytest passes | ✅ DONE | ✅ DONE (340, +8) |
| 3. End-to-end JSON with all new fields | PARTIAL | ✅ DONE |
| 4. Validation loop covers all new fields | PARTIAL | ✅ DONE |
| 5. Report surfaces mixed-intent strategy | NOT DONE | ✅ DONE |
| 6. Tool 2 strategic briefing | N/A | N/A |
| 7. README updated | PARTIAL | ✅ DONE |
| 8. No regressions | ✅ DONE | ✅ DONE |
