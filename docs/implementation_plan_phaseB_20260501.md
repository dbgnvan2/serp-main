# Implementation Plan — Phase B (I.5 + I.6)

**Spec:** `serp_tool1_improvements_spec.md`
**Date:** 2026-05-01
**Status:** Awaiting user approval before any code changes.
**Prerequisite:** Phase A complete (commit 901f85d).

---

## I.5 — Split `generate_content_brief.py`

Current: 2,664 lines, 49 top-level functions. Target: entry-point file under 400 lines.

### Proposed function assignment

All functions move as-is (pure relocation, no body changes). The spec's listed split is confirmed below. One ambiguity is resolved and one unassigned function is placed.

**`brief_data_extraction.py`** — data extraction and helper utilities

`extract_analysis_data_from_json`, `_extract_domain`, `_safe_int`, `_top_sources_for_keyword`, `_normalize_text`, `_classify_entity_distribution`, `_entity_label_reason_text`, `_client_match_patterns`, `_contains_phrase`, `_extract_excerpt`, `_parse_trigger_words`, `_count_terms_in_texts`, `_compute_strategic_flags`, `_classify_paa_intent`, `_build_feasibility_summary`

Constants moving with this file: `DEFAULT_CLIENT_CONTEXT` (used by `extract_analysis_data_from_json`).

**`brief_validation.py`** — LLM output validation

`validate_llm_report`, `validate_extraction`, `validate_advisory_briefing`, `_mixed_keyword_dominance_profiles`, `_label_requires_mixed`, `_label_requires_plurality`, `has_hard_validation_failures`, `partition_validation_issues`

**`brief_prompts.py`** — prompt loading and construction

`_extract_code_block_after_heading`, `_read_prompt_file`, `load_prompt_blocks`, `load_single_prompt`, `build_user_prompt`, `build_main_report_payload`, `build_correction_message`, `append_interpretation_notes`

Constants moving with this file: `MAIN_REPORT_PROMPT_DEFAULT`, `ADVISORY_PROMPT_DEFAULT`, `CORRECTION_PROMPT_DEFAULT`.

**`brief_llm.py`** — Anthropic API call

`run_llm_report`

Constants/imports moving with this file: `anthropic` import guard (`try/except ImportError`), `ANTHROPIC_AVAILABLE`, `MAIN_REPORT_DEFAULT_MODEL`, `ADVISORY_DEFAULT_MODEL`, `SUPPORTED_REPORT_MODELS`.

**`brief_rendering.py`** — report and brief rendering

`generate_brief`, `generate_local_report`, `list_recommendations`, `generate_serp_intent_section`, `score_paa_for_brief`, `get_relevant_paa`, `get_relevant_competitors`, `_dedupe_question_records`, `_infer_intent_text`, `_score_keyword_opportunity`, `write_validation_artifact`

Also moves: `load_brief_pattern_routing` (added I.1; used exclusively by `get_relevant_paa` and `get_relevant_competitors`), and its module-level cache variables `_BRIEF_ROUTING_PATH`, `_BRIEF_ROUTING_CACHE`, `_ROUTING_PATTERN_KEYS`.

**`generate_content_brief.py`** (entry point, remains)

`main`, `progress`, `load_yaml_config`, `load_client_context_from_config`, `load_data`

### Resolution of one ambiguity

`write_validation_artifact` writes a `.validation.md` file when LLM validation fails. The spec places it in `brief_rendering.py`. It is also called in the validation flow (from `main()`). Keeping it in `brief_rendering.py` is correct — it writes output artifacts, not validation logic.

### Import graph (no circular imports)

```
generate_content_brief.py (entry)
    ├── brief_data_extraction  ← classifiers, intent_verdict, title_patterns, yaml
    ├── brief_validation       ← brief_data_extraction
    ├── brief_prompts          ← standard lib, yaml
    ├── brief_llm              ← brief_prompts, anthropic
    └── brief_rendering        ← brief_data_extraction, brief_prompts, yaml
```

`generate_content_brief.py` re-exports any symbols that external callers currently import directly (e.g. `generate_brief`, `list_recommendations`, `extract_analysis_data_from_json`). Re-export stubs are added in step 2 and removed in step 6 of the process (see below). External callers after step 6: `serp_audit.py`, `test_generate_content_brief.py`, `test_markdown_rendering.py`, `test_validation_consistency.py`, `tests/test_brief_routing.py`.

### Process (binding — one commit per step)

1. Create each new file with moved functions and required imports.
2. In `generate_content_brief.py`, replace each moved function body with `from <new_file> import <fn>` re-exports.
3. Update internal calls within `generate_content_brief.py` to use new module names.
4. Run full suite. Must pass.
5. Update external callers (direct imports of moved functions from `generate_content_brief`).
6. Remove re-export stubs from `generate_content_brief.py`.
7. Run full suite again.

### Acceptance criteria

| Criterion | Evidence |
|---|---|
| I.5.1 Five new files with listed functions | `tests/test_module_split.py::test_i51_files_exist_with_functions` |
| I.5.2 `generate_content_brief.py` < 400 lines | `tests/test_module_split.py::test_i52_main_module_size` |
| I.5.3 Zero failures | test suite output |
| I.5.4 Pipeline output unchanged | `tests/test_module_split.py::test_i54_pipeline_output_unchanged` |
| I.5.5 Status report lists every function moved with commit hashes | `docs/i_phaseB_status_<date>.md` |

---

## I.6 — Split `serp_audit.py`

Current: 2,332 lines. Target: under 500 lines. See `docs/serp_audit_split_plan_20260501.md` for the detailed function-assignment table, import graph, and flag on the `main()` size issue.

### Acceptance criteria

| Criterion | Evidence |
|---|---|
| I.6.1 `docs/serp_audit_split_plan_20260501.md` exists with user approval | file existence + approval annotation |
| I.6.2 New files with approved functions | `tests/test_serp_audit_split.py::test_i62_files_exist_with_functions` |
| I.6.3 `serp_audit.py` < 500 lines | `tests/test_serp_audit_split.py::test_i63_main_module_size` |
| I.6.4 Zero failures | test suite output |
| I.6.5 Pipeline output structurally identical | `tests/test_serp_audit_split.py::test_i65_pipeline_output_unchanged` |

---

## Phase B execution order

```
User approves I.5 plan (this document)
    └─► Execute I.5 (7 commits)
        └─► Run full suite, confirm pass
            └─► User approves I.6 split plan (serp_audit_split_plan_20260501.md)
                └─► Execute I.6 (7 commits)
                    └─► Run full suite, confirm pass
                        └─► Write i_phaseB_status_<date>.md
                            └─► Push + report to user
```

I.5 and I.6 are sequential (I.5 first) because `serp_audit.py` imports `generate_content_brief` and the callers update in I.5 step 5.
