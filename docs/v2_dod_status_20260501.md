# v2 Definition of Done — Status Report

**Date:** 2026-05-01  
**Auditor:** Claude Sonnet 4.6  
**Baseline file:** `output/market_analysis_couples_therapy_20260501_0717.json`  
**Branch:** `main` @ `8fac920`

This report is the mandatory first deliverable required by `serp_tool1_fix_spec.md` (cross-cutting requirement). It assesses every DoD item from `serp_tools_upgrade_spec_v2.md` as `done`, `partial`, or `not done`, with evidence. Tool 2 items are marked `n/a (Tool 2)`.

---

## DoD Item 1 — Every gap section's acceptance criteria are met

**Status: PARTIAL**

### Gap 1 — SERP intent verdict

| Criterion | Status | Evidence |
|-----------|--------|---------|
| `intent_mapping.yml` draft submitted as separate PR with rationale doc | **NOT DONE** | No `docs/intent_mapping_rationale.md`; mapping committed to `main` directly without PR for review. User approved mapping verbally but no rationale doc exists. |
| `keyword_profiles[kw]["serp_intent"]` populated for every keyword | DONE | Confirmed in JSON output: 6/6 keywords have `serp_intent`. |
| `intent_mapping.yml` loaded at startup; no hard-coded mapping | DONE | `generate_content_brief.py:592` loads via `load_intent_mapping()`. |
| Every `intent_distribution` value is a non-negative integer | **NOT DONE** | Output shows fractions: `"informational": 0.888...`. Fix 2 addresses this. |
| `confidence` correctly set per denominator rules | **NOT DONE** | All 6 keywords show `confidence: low`. Denominator is 25–30 (all modules), not top-10 organic. Fix 1 addresses this. |
| Unit tests for all 6 required SERP scenarios | PARTIAL | Tests exist but don't cover the "8 organic + many other modules → denominator stays 10" scenario. |
| `system.md` updated to reference `serp_intent` fields | DONE | `prompts/main_report/system.md:44–55` references `primary_intent`, `is_mixed`, `intent_distribution`, `mixed_intent_strategy`. |
| Validation rules (HARD-FAIL) for `primary_intent` and `is_mixed` | DONE | `generate_content_brief.py:1693,1769`. |
| Test crafts bad LLM output and confirms validator catches it | DONE | `test_generate_content_brief.py` — `test_validate_llm_report_flags_intent_contradiction_hard`. |

### Gap 2 — Title pattern extraction

| Criterion | Status | Evidence |
|-----------|--------|---------|
| `title_patterns` populated for every keyword with ≥1 organic result | DONE | All 6 keywords have `title_patterns` in output. |
| Pattern detection case-insensitive | DONE | Regexes use `re.IGNORECASE` in `title_patterns.py`. |
| Priority ordering: "How To Compare X vs Y" → `vs_comparison` | DONE | `title_patterns.py` priority order in `PATTERNS` list. |
| Unit tests per pattern (positive + negative) | DONE | `test_title_patterns.py` covers each pattern. |
| `dominant_pattern` is `null` when no pattern reaches threshold | DONE | Output shows `dominant_pattern: null` for all 6 keywords (no pattern dominates). |
| `system.md` mentions `title_patterns.dominant_pattern` | DONE | `prompts/main_report/system.md:67,260,293`. |
| Validator catches LLM contradicting non-null `dominant_pattern` | PARTIAL — **WRONG SEVERITY** | Code at `generate_content_brief.py:1404` classifies `dominant_pattern` contradiction as **SOFT-FAIL**. Fix 7 spec requires **HARD-FAIL**. |

### Gap 3 — Competitor handoff

| Criterion | Status | Evidence |
|-----------|--------|---------|
| `handoff_schema.json` at repo root (and copy at `serp-compete`) | DONE | `handoff_schema.json` exists at repo root. |
| `competitor_handoff_*.json` produced on every full pipeline run | DONE | `output/competitor_handoff_couples_therapy_20260501_0721.json` produced. |
| Output validates against schema before write | DONE | `serp_audit.py:2190` — validates before write. |
| Omit list and N configurable | DONE | `config.yml` → `audit_targets.n` and `audit_targets.omit_from_audit`. |
| Client URLs excluded; counted in `exclusions` | DONE | Confirmed in handoff output: `exclusions.client_urls_excluded`. |
| README section on handoff | DONE | `README.md:215`. |
| `docs/handoff_contract.md` exists | **NOT DONE** | File not created. Fix 3 addresses this. |
| Tests for: invalid handoff fails, no organic → no file, all-client → empty targets | **NOT DONE** | No handoff-specific pipeline tests. Fix 3 addresses this. |

### Gap 4 — Mixed-intent advisory framing

| Criterion | Status | Evidence |
|-----------|--------|---------|
| `mixed_intent_strategy` field populated for mixed-intent keywords | DONE | "couples counselling" shows `mixed_intent_strategy: "backdoor"`. |
| Non-mixed keywords get `null` | DONE | Other 5 keywords show `mixed_intent_strategy: null`. |
| `client.preferred_content_types` in `config.yml` | PARTIAL — wrong key | Config uses `client.preferred_intents`; v2 spec said `preferred_content_types`. The implementation uses `preferred_intents` consistently; naming diverged from spec. No functional impact. |
| Both system prompts (`main_report` + `advisory`) updated | PARTIAL | `main_report/system.md` updated. `advisory/system.md` not verified to have mixed-intent framing. |
| Validation rules for `mixed_intent_strategy` | DONE | `generate_content_brief.py:1782–1809`. |
| Unit test per value (`compete_on_dominant`, `backdoor`, `avoid`, null) | DONE | `test_generate_content_brief.py` — 4 mixed-intent tests. |

### Gap 5 — Validation rule consistency check

| Criterion | Status | Evidence |
|-----------|--------|---------|
| Test scans prompt files for field refs, asserts each has validator rule | DONE | `test_validation_consistency.py`. |
| Test fails when new field added without matching validator | DONE | Tested via `KNOWN_UNVALIDATED` set. |
| Test passes after all Gap validator rules added | DONE | 332 tests passing. |

---

## DoD Item 2 — pytest passes with new tests

**Status: DONE**

332 passed, 5 skipped @ commit `8fac920`.

---

## DoD Item 3 — End-to-end run produces JSON with all new fields

**Status: PARTIAL**

`keyword_profiles` is present in the JSON. However:

- `intent_distribution` values are **fractions** (e.g. `0.888...`), not integers. (Fix 2)
- `evidence` field names are old: `total_url_count`, `classified_url_count`, `uncategorised_count`. Spec requires `organic_url_count`, `classified_organic_url_count`, `uncategorised_organic_url_count`. (Fix 1)
- `evidence.intent_counts` exists but spec says to remove it after Fix 2. (Fix 2)
- `confidence: low` for all 6 keywords because denominator includes all modules (27–30 rows), not top-10 organic. (Fix 1)
- `primary_intent: null` rule for `n < 5` not implemented — all keywords show a non-null primary_intent even when they shouldn't. (Fix 1)
- `evidence.local_pack_present` and `evidence.local_pack_member_count` fields missing. (Fix 1)

---

## DoD Item 4 — Validation/correction loop covers every new pre-computed field

**Status: PARTIAL**

| Field | Validator rule | Severity | Correct? |
|-------|---------------|----------|---------|
| `primary_intent` | Yes | HARD | ✅ |
| `is_mixed` | Yes | HARD | ✅ |
| `dominant_pattern` | Yes | **SOFT** | ❌ spec requires HARD (Fix 7) |
| `mixed_intent_strategy` | Yes | SOFT | ✅ |
| `confidence` | No explicit rule | — | ❌ missing per Fix 7 spec |

---

## DoD Item 5 — Advisory briefing uses `mixed_intent_strategy` on fixture

**Status: NOT DONE**

The markdown report and advisory briefing do not contain the new "Per-Keyword SERP Intent" section, mixed-intent strategic notes, or "1a. SERP Intent Context" subsections in content briefs. Fix 4 addresses this.

---

## DoD Item 6 — Tool 2 strategic briefing (Section A + B)

**Status: N/A (Tool 2)** — out of scope for this pass.

---

## DoD Item 7 — README documents new fields and handoff contract

**Status: PARTIAL**

| Section | Status |
|---------|--------|
| "What's new in this version" listing new fields | **NOT DONE** |
| "Output files" section listing all 4 output files | PARTIAL (table exists but missing v2 detail) |
| "Backwards compatibility note" for pre-v2 runs | **NOT DONE** |
| "Tool 1 → Tool 2 handoff" subsection pointing to `docs/handoff_contract.md` | **NOT DONE** |

---

## DoD Item 8 — No previously-passing test now fails

**Status: DONE**

332 passed, 5 skipped. No regressions.

---

## Summary table

| DoD Item | Status |
|----------|--------|
| 1. All gap acceptance criteria met | PARTIAL |
| 2. pytest passes | ✅ DONE |
| 3. End-to-end JSON with all new fields | PARTIAL |
| 4. Validation loop covers all new fields | PARTIAL |
| 5. Advisory briefing uses mixed_intent_strategy | NOT DONE |
| 6. Tool 2 strategic briefing | N/A |
| 7. README updated | PARTIAL |
| 8. No regressions | ✅ DONE |

## Fixes being implemented

This status report is the baseline. Fixes 1–8 in `serp_tool1_fix_spec.md` address all `PARTIAL` and `NOT DONE` items above. A second version of this document (`docs/v2_dod_status_20260501_post.md`) will be committed after all fixes land.
