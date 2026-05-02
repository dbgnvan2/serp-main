# Improvements Specification: Tool 1 Code Review Findings

**Spec ID prefix:** I (for Improvements)
**Predecessor specs:** v2, fix, completion, cleanup
**Date:** 2026-05-02
**Source:** Code review of `generate_content_brief.py`, `generate_insight_report.py`, `intent_classifier.py`, `serp_audit.py`, `classifiers.py`, `intent_verdict.py`, `intent_mapping.yml`, `strategic_patterns.yml`

## What this spec is

Changes recommended after reading the codebase as it stands. None of these are bug fixes against an existing acceptance criterion. All are improvements that would make the tool more reviewable, more accurate, and more honest about what it's doing.

## What this spec is NOT

- Not a refactor of working code for stylistic reasons.
- Not a feature addition.
- Not a re-litigation of completed work.

## How this spec is structured

The spec contains seven fixes (I.1 through I.7) grouped into two phases.

**Phase A — Externalisation and accuracy improvements** (I.1 through I.4). Small, low-risk, high-value. These should land first.

**Phase B — File breakups** (I.5 and I.6). Medium-risk structural changes. The user will have a separate plan made for these and the agent will work through them carefully. These are scoped here but explicitly flagged as "do not start until Phase A is complete and reviewed."

**Phase C — Documentation and process** (I.7). One-time additions that prevent recurrence of the patterns this spec addresses.

The agent works Phase A in order (I.1, I.2, I.3, I.4), produces the status report, gets user approval, then waits for the user's instruction before starting Phase B.

## Workflow expectations

Per `~/.claude/CLAUDE.md`:

- Plan first (`docs/implementation_plan_<date>.md`), wait for approval, then execute.
- Status report at `docs/i_phaseA_status_<date>.md` after Phase A. Separate status report `docs/i_phaseB_status_<date>.md` after Phase B (if Phase B is approved).
- Spec coverage matrix updated to include all I.* criteria.
- Evidence cells include explicit file paths.
- Honest failure: if a fix produces unexpected behaviour change downstream (e.g. a brief renders different content because PAA themes route differently), the agent reports it before merging.

---

# PHASE A — Externalisation and accuracy improvements

These four fixes can land independently. The agent may work them in parallel or sequentially. None depend on the others.

# Fix I.1 — Externalise PAA theme routing from `generate_content_brief.py`

## Problem

`generate_content_brief.py` contains four Python dictionaries that encode editorial decisions about how Bowen patterns route to People Also Ask questions and source keywords:

- `BRIEF_PAA_THEMES` — words that mark a PAA question as relevant to each pattern
- `BRIEF_PAA_CATEGORIES` — PAA category tags relevant to each pattern
- `BRIEF_KEYWORD_HINTS` — substrings in source keywords that mark relevance
- `_BRIEF_INTENT_SLOTS` — text descriptions for each SERP intent bucket

These are editorial knobs. Their location inside a 2,643-line Python file makes them invisible to anyone reviewing the tool's behaviour, and changing them requires editing Python.

## Required change

Create `brief_pattern_routing.yml` at the repo root. Schema:

```yaml
# brief_pattern_routing.yml
#
# Editorial routing rules: how each Bowen pattern in strategic_patterns.yml
# selects relevant PAA questions, categories, and source keywords for its
# content brief. Edit this file when a brief pulls in irrelevant questions
# or misses ones it should include — do not push exceptions into Python.
#
# Schema per pattern:
#   pattern_name:        must match a Pattern_Name in strategic_patterns.yml
#   paa_themes:          phrases (whole or partial) found in PAA question text
#   paa_categories:      category tags from intent classifier output
#   keyword_hints:       substrings found in the source keyword
#
# Scoring (defined in get_relevant_paa, do not change):
#   theme_score    weight 3  (matches in question text)
#   category_score weight 2  (matches in PAA category)
#   keyword_score  weight 1  (matches in source keyword)
#
# A separate top-level intent_slot_descriptions block maps SERP intent
# bucket names to human-readable text used in brief subsections.

version: 1

patterns:
  - pattern_name: The Medical Model Trap
    paa_themes:
      - therapy
      - therapist
      - counselling
      - counselor
      - session
      - diagnosis
      - mental health
      - treatment
      - professional
      - psychologist
    paa_categories:
      - External Locus
    keyword_hints:
      - therapy
      - counselling
      - counseling
      - mental health

  - pattern_name: The Fusion Trap
    paa_themes:
      - reach out
      - reconnect
      - contact
      - close
      - relationship
      - communicate
      - talking
      - stop reaching
      - go no contact
    paa_categories: []
    keyword_hints:
      - estrangement
      - adult child
      - reach out
      - contact

  - pattern_name: The Resource Trap
    paa_themes:
      - cost
      - free
      - afford
      - pay
      - price
      - insurance
      - covered
      - sliding scale
      - low cost
      - how much
    paa_categories: []
    keyword_hints:
      - grief
      - counselling
      - therapy
      - bc

  - pattern_name: The Blame/Reactivity Trap
    paa_themes: []  # extracted from current Python value
    paa_categories: []
    keyword_hints:
      - estrangement
      - toxic
      - no-contact
      - family member

intent_slot_descriptions:
  informational: informational/educational
  commercial_investigation: research/comparison
  transactional: service/booking
  navigational: brand-search
  local: local-service
  mixed: mixed (see Section 5b for components)
```

The agent extracts the actual current values from `generate_content_brief.py` for `BRIEF_PAA_THEMES`, `BRIEF_PAA_CATEGORIES`, `BRIEF_KEYWORD_HINTS`, and `_BRIEF_INTENT_SLOTS` and copies them verbatim into the YAML file. No editorial changes; this is a pure relocation.

In `generate_content_brief.py`:

- Remove the four dictionary literals.
- Add a loader function `load_brief_pattern_routing(path: str = "brief_pattern_routing.yml") -> dict` that reads the YAML, validates the schema, and returns a dict of the same shape the old constants provided. Validation includes: every pattern_name in the YAML must match a pattern in `strategic_patterns.yml`; every key required by `get_relevant_paa` must be present; `intent_slot_descriptions` must contain entries for every value of `_BRIEF_INTENT_SLOTS`.
- Cache the loaded routing at module level so it loads once per process.
- All call sites (`get_relevant_paa`, the brief 1a renderer) read from the loaded structure, not from removed constants.

## Acceptance criteria

- **I.1.1** `brief_pattern_routing.yml` exists at the repo root.
  Verified by: file existence at `brief_pattern_routing.yml`.

- **I.1.2** The YAML contains all four pattern entries with values matching the previous Python constants exactly.
  Verified by: `tests/test_brief_routing.py::test_i12_yaml_matches_previous_constants` — fixture compares loaded YAML to the values that were in the Python source as of the commit before this change.

- **I.1.3** No `BRIEF_PAA_THEMES`, `BRIEF_PAA_CATEGORIES`, `BRIEF_KEYWORD_HINTS`, or `_BRIEF_INTENT_SLOTS` literal definitions remain in `generate_content_brief.py`.
  Verified by: `tests/test_brief_routing.py::test_i13_no_hardcoded_routing_in_python` — greps the file for these names as definitions.

- **I.1.4** Loading a malformed `brief_pattern_routing.yml` (missing required key, pattern_name not in `strategic_patterns.yml`) raises a clear `ValueError` at startup.
  Verified by: `tests/test_brief_routing.py::test_i14_malformed_yaml_raises`.

- **I.1.5** Re-running the pipeline against the `couples_therapy` fixture produces a content brief identical to the previous run (same PAA questions selected per brief, same intent slot descriptions).
  Verified by: `tests/test_brief_routing.py::test_i15_pipeline_output_unchanged_after_externalisation` — diffs new output against pinned baseline.

## Out of scope for I.1

- Editing the routing values themselves. The point of this fix is relocation, not refinement. Any editorial changes happen in a separate pass after review.
- Externalising other hardcoded content in `generate_content_brief.py`. Other constants stay where they are.

## Implementation notes

- Use the existing `yaml.safe_load` pattern from `intent_mapping.yml`.
- The loader should be idempotent and safe to call multiple times.
- A failed load should be a fatal error at module import / first use, not a silent fallback to defaults.

---

# Fix I.2 — Externalise `intent_classifier.py` trigger lists

## Problem

`intent_classifier.py` defines `DEFAULT_MEDICAL_TRIGGERS` and `DEFAULT_SYSTEMIC_TRIGGERS` as `frozenset` constants at the top of the file. The class accepts override sets at construction time but the override hook is unused — production callers always get the hardcoded defaults.

The Bowen patterns moved to `strategic_patterns.yml` recently. The medical-vocabulary and systemic-vocabulary lists are the same kind of editorial content and should make the same move.

## Required change

Create `intent_classifier_triggers.yml` at the repo root:

```yaml
# intent_classifier_triggers.yml
#
# Trigger vocabularies used by intent_classifier.py to tag PAA questions and
# keyword phrases as "External Locus" (medical model framing) or "Systemic"
# (Bowen Family Systems Theory framing). General = neither.
#
# Multi-word phrases are matched first (longest-first) to avoid partial-word
# false positives. Single-word triggers use word-boundary matching.
#
# Editing this file changes which questions get tagged for the Bowen Reframe
# FAQ section of the content brief. Do not push trigger changes into Python.

version: 1

medical_triggers:
  multi_word:
    - mental illness
    - mental health condition
    - evidence-based treatment
    - evidence based treatment
    - cognitive behavioral
    - cognitive behavioural
  single_word:
    - diagnosis
    - diagnose
    - treatment
    - patient
    - symptoms
    - symptom
    - disorder
    - medication
    - medicate
    - medicated
    - prescription
    - fix
    - heal
    - cure
    - condition
    - clinical
    - clinician
    - psychiatrist
    - psychiatry
    - pathology
    - pathological
    - dysfunction
    - dysfunctional
    - illness
    - disease
    - recovery
    - rehabilitation
    - intervention
    - borderline
    - narcissist
    - narcissistic
    - toxic

systemic_triggers:
  multi_word:
    - family system
    - family systems
    - emotional system
    - emotional process
    - emotional cutoff
    - differentiation of self
    - level of differentiation
    - multigenerational transmission
    - nuclear family
    - sibling position
    - societal emotional process
  single_word:
    - differentiation
    - differentiated
    - triangulation
    - triangle
    - triangles
    - reactivity
    - reactive
    - cutoff
    - functioning
    - multigenerational
    - intergenerational
    - bowen
    - togetherness
    - individuality
    - chronic anxiety
    - anxiety
    - fusion
    - fused
    - projection
    - undifferentiated
```

The split into `multi_word` and `single_word` mirrors how the Python code currently uses the triggers (multi-word phrases checked first via longest-first sort). The agent extracts the actual current values verbatim — this is a pure relocation.

In `intent_classifier.py`:

- Add `load_triggers(path: str = "intent_classifier_triggers.yml") -> tuple[frozenset, frozenset]` returning `(medical_set, systemic_set)`.
- Validation: both blocks must exist; both must contain at least `multi_word` and `single_word` lists; lists may be empty but must be present; trigger strings must be 4+ characters (per the same rule documented in `strategic_patterns.yml`).
- The `IntentClassifier.__init__` now defaults to `medical_triggers=None` and `systemic_triggers=None` and, if both are None, calls `load_triggers()` to populate them.
- The Python `frozenset` constants `DEFAULT_MEDICAL_TRIGGERS` and `DEFAULT_SYSTEMIC_TRIGGERS` are removed from the file.

The constructor argument override path is preserved — tests can still pass custom trigger sets.

## Acceptance criteria

- **I.2.1** `intent_classifier_triggers.yml` exists at the repo root.
  Verified by: file existence at `intent_classifier_triggers.yml`.

- **I.2.2** YAML values match the previous `DEFAULT_*` constants exactly (set equality).
  Verified by: `tests/test_intent_classifier_triggers.py::test_i22_yaml_matches_previous_constants`.

- **I.2.3** No `DEFAULT_MEDICAL_TRIGGERS` or `DEFAULT_SYSTEMIC_TRIGGERS` constant exists in `intent_classifier.py`.
  Verified by: `tests/test_intent_classifier_triggers.py::test_i23_no_hardcoded_triggers_in_python`.

- **I.2.4** Trigger string shorter than 4 characters in YAML raises a clear `ValueError` at load.
  Verified by: `tests/test_intent_classifier_triggers.py::test_i24_short_trigger_raises`.

- **I.2.5** Constructor override hook still works: passing `medical_triggers=frozenset({"foo"})` overrides the YAML.
  Verified by: `tests/test_intent_classifier_triggers.py::test_i25_constructor_override_still_works`.

- **I.2.6** Re-running the pipeline against the `couples_therapy` fixture produces PAA intent tags identical to the previous run.
  Verified by: `tests/test_intent_classifier_triggers.py::test_i26_pipeline_output_unchanged`.

## Out of scope for I.2

- Editing the trigger vocabulary itself. The point is relocation, not refinement.
- Splitting "External Locus" further (e.g. into "diagnostic," "pharmacological," "professional"). The single bucket stays for now.

---

# Fix I.3 — Improve most-relevant-keyword selection in Section 4 pattern blocks

## Problem

`_get_most_relevant_keyword()` in `generate_insight_report.py` selects the keyword for each Section 4 pattern's intent context line by counting how many of the pattern's trigger words appear in the Title+Snippet text of organic results, grouped by source keyword.

This is a noisy signal. Trigger words appearing in competitor-page titles tell you what the SERP authors wrote, not what searchers are asking about. The May 1 15:17 output shows the consequence: the Medical Model Trap (triggers "clinical, registered, treatment, diagnosis...") got matched to "How much is couples therapy in Vancouver?" — a cost-anxiety query — because the cost-related pages happened to use clinical-sounding language in their titles.

A better signal already exists in the data: PAA questions tagged as `External Locus` by `intent_classifier.py`. PAA questions reveal what searchers are framing, not what page authors wrote.

## Required change

Rewrite `_get_most_relevant_keyword()` in `generate_insight_report.py` to score keywords using a combined signal:

```
score(keyword, pattern) =
    (count of PAA questions for this keyword tagged with pattern's relevant intent class) * 3
  + (count of pattern's keyword_hints matching this keyword's source text) * 2
  + (count of pattern's trigger words appearing in Title+Snippet of this keyword's organic results) * 1
```

Where:

- "Pattern's relevant intent class" is a new YAML field added to `strategic_patterns.yml` (see schema below).
- "PAA questions for this keyword" come from `paa_questions` rows where `Source_Keyword` matches and `Intent_Tag` matches the pattern's relevant intent class.
- "Pattern's keyword_hints" come from `brief_pattern_routing.yml` (added in I.1).
- "Pattern's trigger words" come from `strategic_patterns.yml` (existing).

The current trigger-text scoring is preserved as the third (lowest-weighted) term, so behaviour doesn't change in cases where PAA evidence is absent.

### Schema addition to `strategic_patterns.yml`

Each pattern entry gains an optional `Relevant_Intent_Class` field:

```yaml
- Pattern_Name: The Medical Model Trap
  Relevant_Intent_Class: External Locus  # NEW: which intent_classifier tag PAA must match
  Triggers: [...]  # existing
  Status_Quo_Message: ...  # existing
  ...
```

Mapping for the four current patterns (proposed; agent confirms with user before merging):

- The Medical Model Trap → `External Locus`
- The Fusion Trap → no PAA intent class is reliably correlated; field is omitted, score component is 0
- The Resource Trap → no PAA intent class is reliably correlated; field is omitted, score component is 0
- The Blame/Reactivity Trap → `External Locus` (the framing of "narcissist," "toxic," "abusive" is medical-model-adjacent)

Patterns without `Relevant_Intent_Class` simply skip the PAA component and score on the other two. The PAA term contributes 0 in their case; this is the "still works without the new signal" property.

### Tiebreaker

When multiple keywords score equally, the existing alphabetical tiebreaker is preserved.

## Acceptance criteria

- **I.3.1** `_get_most_relevant_keyword()` uses the three-component scoring described above.
  Verified by: `tests/test_most_relevant_keyword.py::test_i31_three_component_scoring`.

- **I.3.2** When a pattern has `Relevant_Intent_Class` set, the PAA score component contributes per the formula.
  Verified by: `tests/test_most_relevant_keyword.py::test_i32_paa_intent_class_contributes`.

- **I.3.3** When a pattern lacks `Relevant_Intent_Class`, the PAA score component is 0 and only keyword_hints + trigger_text contribute.
  Verified by: `tests/test_most_relevant_keyword.py::test_i33_no_intent_class_falls_back`.

- **I.3.4** Re-running against the `couples_therapy` fixture, the Medical Model Trap is matched to a keyword whose PAA questions contain at least one `External Locus` tag — not the previous "How much is couples therapy in Vancouver?" mismatch.
  Verified by: `tests/test_most_relevant_keyword.py::test_i34_medical_model_picks_external_locus_keyword`.

- **I.3.5** When all keywords score 0 across all three components, the function returns `None` and the existing fallback message renders ("no keyword in this run has triggers for this pattern").
  Verified by: `tests/test_most_relevant_keyword.py::test_i35_all_zero_returns_none`.

- **I.3.6** Updated `_get_most_relevant_keyword()` docstring per `~/.claude/CLAUDE.md` Rule 6 includes Spec/Tests references for I.3.
  Verified by: visual inspection of docstring.

## Implementation notes

- Loading PAA tags requires reading `Intent_Tag` field from `paa_questions` rows (already populated by `intent_classifier.py` in `serp_audit.py`).
- The function signature gains a `paa_questions: list` parameter alongside the existing `rec`, `organic_results`, `keyword_profiles`. All call sites updated in the same change.
- Document the change in `docs/methodology.md` Part 2 in the same commit (the file already references the previous logic).

## Out of scope for I.3

- Inventing new intent classes beyond the existing External Locus / Systemic / General. Stays at three.
- Changing the PAA classifier itself (covered by I.2 and unrelated).
- Changing the score weights. The 3:2:1 ratio is a starting point; the user reviews and may adjust later.

---

# Fix I.4 — Document the agent-vs-hardcoded asymmetry

## Problem

The agent has been disciplined about externalising new editorial content (intent_mapping.yml, strategic_patterns.yml, url_pattern_rules.yml) but has not externalised existing hardcoded editorial content in files it didn't initially write. The result is a codebase where similar editorial content lives in different places — some in YAML, some in Python literals — without any rule explaining which is which.

## Required change

Add a section to the project-level `CLAUDE.md` (in the repo root, not the user-level) titled "Editorial content lives in config files":

```markdown
## Editorial content lives in config files

Trigger words, classification rules, mapping tables, vocabulary lists,
brief routing rules, and any other content that requires editorial judgment
to refine belongs in YAML or JSON, not in Python source.

When adding a new editorial knob (a new trigger list, a new mapping table,
a new routing rule), check whether similar editorial content already exists
elsewhere in the codebase. If so, externalise the older content in the same
change. Do not leave old hardcoded content in place while new content moves
to YAML — this produces a codebase where similar things live in different
places and reviewers can't find the editorial surface.

Test for "is this editorial content?": if a non-developer reading the file
might reasonably want to change a value (a trigger word, a category label,
a routing rule), it's editorial. If only a developer would touch it (a
class structure, a function signature, an algorithm), it's code.

Editorial content currently lives in:
- `intent_mapping.yml` — SERP intent rule table
- `strategic_patterns.yml` — Bowen patterns (triggers, status quo, reframes)
- `url_pattern_rules.yml` — URL pattern fallbacks for content classifier
- `domain_overrides.yml` — manual entity-type overrides
- `classification_rules.json` — content type and entity type pattern lists
- `clinical_dictionary.json` — Bowen vs medical vocabulary tiers
- `brief_pattern_routing.yml` — brief PAA / keyword / intent-slot routing (added I.1)
- `intent_classifier_triggers.yml` — PAA External Locus / Systemic vocabularies (added I.2)
- `config.yml` — operational settings

When in doubt, ask the user before adding new editorial content to a `.py` file.
```

## Acceptance criteria

- **I.4.1** The "Editorial content lives in config files" section exists in the project-level `CLAUDE.md`.
  Verified by: file path and section heading match.

- **I.4.2** The section lists all current editorial config files including the two added by I.1 and I.2.
  Verified by: visual inspection.

- **I.4.3** The new section appears before the "Reference documentation" section so it is among the first things read.
  Verified by: section order check in `CLAUDE.md`.

## Out of scope for I.4

- Auditing the entire codebase for additional hardcoded editorial content beyond what I.1 and I.2 address. The user prefers to discover further externalisation candidates organically rather than do a sweep.

---

# PHASE B — File breakups

**The agent does not start Phase B until:**
1. Phase A is complete and merged.
2. The user has explicitly approved starting Phase B.
3. A separate implementation plan has been produced for each Phase B fix.

# Fix I.5 — Split `generate_content_brief.py`

## Problem

`generate_content_brief.py` is 2,643 lines with 48 top-level functions covering data extraction, validation, prompt construction, LLM calls, retry handling, brief rendering, recommendation listing, and CLI orchestration. Files this size become hard to test, hard to review, and the place where silent regressions accumulate. The `validate_llm_report` function alone is 327 lines.

## Required change

Split into the following files. Each split is a pure relocation: function bodies do not change, only their location and imports. Public function signatures stay the same so existing call sites continue to work after import path updates.

| New file | Functions to move |
|---|---|
| `brief_data_extraction.py` | `extract_analysis_data_from_json`, `_extract_domain`, `_safe_int`, `_top_sources_for_keyword`, `_normalize_text`, `_classify_entity_distribution`, `_entity_label_reason_text`, `_client_match_patterns`, `_contains_phrase`, `_extract_excerpt`, `_parse_trigger_words`, `_count_terms_in_texts`, `_compute_strategic_flags`, `_classify_paa_intent`, `_build_feasibility_summary` |
| `brief_validation.py` | `validate_llm_report`, `validate_extraction`, `validate_advisory_briefing`, `_mixed_keyword_dominance_profiles`, `_label_requires_mixed`, `_label_requires_plurality`, `has_hard_validation_failures`, `partition_validation_issues` |
| `brief_prompts.py` | `_extract_code_block_after_heading`, `_read_prompt_file`, `load_prompt_blocks`, `load_single_prompt`, `build_user_prompt`, `build_main_report_payload`, `build_correction_message`, `append_interpretation_notes` |
| `brief_llm.py` | `run_llm_report` |
| `brief_rendering.py` | `generate_brief`, `generate_local_report`, `list_recommendations`, `generate_serp_intent_section`, `score_paa_for_brief`, `get_relevant_paa`, `get_relevant_competitors`, `_dedupe_question_records`, `_infer_intent_text`, `_score_keyword_opportunity`, `write_validation_artifact` |
| `generate_content_brief.py` | `main`, `progress`, `load_yaml_config`, `load_client_context_from_config`, `load_data` — the entry point and CLI shell |

The agent confirms this split with the user before moving anything. Some functions may be shared dependencies that need a different home; the agent flags any ambiguity rather than guessing.

## Process constraints (binding)

The agent uses this sequence for the move:

1. Create the new file with the moved functions and required imports.
2. Replace the function bodies in `generate_content_brief.py` with `from <new_file> import <function>` re-exports for one commit (so callers keep working).
3. Update internal call sites within `generate_content_brief.py` to use the new module names.
4. Run the full test suite. Confirm 0 failures.
5. Update external callers (anything importing from `generate_content_brief.py` directly).
6. Remove the re-export stubs from `generate_content_brief.py`.
7. Run the full test suite again.

Each numbered step is a separate commit. The agent does not combine steps. If any step's test run fails, the agent stops and reports rather than fixing forward.

## Acceptance criteria

- **I.5.1** Each of the five new files exists with the listed functions.
  Verified by: `tests/test_module_split.py::test_i51_files_exist_with_functions`.

- **I.5.2** `generate_content_brief.py` line count is under 400 lines.
  Verified by: `tests/test_module_split.py::test_i52_main_module_size`.

- **I.5.3** `pytest -q` reports zero failures and zero errors.
  Verified by: test suite output.

- **I.5.4** Re-running the pipeline against the `couples_therapy` fixture produces a content brief identical to the previous run.
  Verified by: `tests/test_module_split.py::test_i54_pipeline_output_unchanged`.

- **I.5.5** The status report explicitly lists each function moved and its new location, with both source and destination commit hashes.
  Verified by: `docs/i_phaseB_status_<date>.md` content.

## Out of scope for I.5

- Refactoring the function bodies. Pure relocation only.
- Renaming functions.
- Adding new tests beyond those listed.
- Splitting `validate_llm_report` itself into smaller functions (separate concern; tracked but not in scope).

---

# Fix I.6 — Split `serp_audit.py`

## Problem

`serp_audit.py` is 2,332 lines and combines orchestration, SerpAPI client wrapping, URL enrichment, classifier invocation, n-gram corpus building, pattern matching, intent verdict computation, output writing (JSON, XLSX, MD), competitor handoff writing, and SQLite persistence. Same structural debt as `generate_content_brief.py`.

## Required change

The agent first proposes a split plan in `docs/serp_audit_split_plan_<date>.md`. The user reviews and approves before implementation. Approximate plan to start from:

| New file | Approximate scope |
|---|---|
| `serp_api_client.py` | SerpAPI calls, retry/rate-limit handling, raw response storage |
| `url_enrichment.py` | URL fetching, HTML parsing, header inspection |
| `pattern_matching.py` | N-gram corpus building, `strategic_patterns.yml` matching |
| `report_writers.py` | JSON, XLSX, MD output generation |
| `handoff_writer.py` | Competitor handoff JSON generation and validation |
| `serp_audit.py` | Pipeline orchestration only — `main()` and the high-level run function |

The same process constraints from I.5 apply: each numbered step is a separate commit, tests pass after each, agent stops on failure.

The split plan must address: which functions are shared dependencies, which functions need to move together, what the new import graph looks like, whether any circular imports might arise.

## Acceptance criteria

- **I.6.1** `docs/serp_audit_split_plan_<date>.md` exists and has user approval before any code moves.
  Verified by: file exists with approval annotation.

- **I.6.2** Each new file exists with the approved functions.
  Verified by: `tests/test_serp_audit_split.py::test_i62_files_exist_with_functions`.

- **I.6.3** `serp_audit.py` line count is under 500 lines.
  Verified by: `tests/test_serp_audit_split.py::test_i63_main_module_size`.

- **I.6.4** `pytest -q` reports zero failures and zero errors.
  Verified by: test suite output.

- **I.6.5** Re-running the pipeline against the `couples_therapy` fixture produces JSON, XLSX, MD, and competitor handoff files byte-identical (or, where timestamps differ, structurally identical) to the previous run.
  Verified by: `tests/test_serp_audit_split.py::test_i65_pipeline_output_unchanged`.

## Out of scope for I.6

- Refactoring function bodies.
- Adding new tests beyond those listed.
- Changes to the SQLite schema or storage layer.

---

# PHASE C — Process documentation

# Fix I.7 — Add a "do not abandon old code" rule

## Problem

The pattern documented in I.4 (new content externalised, old content left hardcoded) is one instance of a broader pattern: agents tend not to refactor code they didn't write themselves, even when doing so would improve consistency. This creates a codebase where new contributions look professional and old contributions look untouched.

## Required change

Add a rule to the user-level `~/.claude/CLAUDE.md` (the workflow rules file). New rule, numbered 7:

```markdown
## 7. Old code is not someone else's problem

When adding a new feature or fixing a bug, scan the surrounding code for
similar patterns that exhibit the same problem the new work addresses. If
similar issues exist:

- Flag them in the implementation plan.
- Do not silently fix them in the same change — that produces a sweeping
  diff the user can't review.
- Do not silently leave them — that produces an inconsistent codebase
  where the same problem is solved one way in new code and another way
  in old code.
- Instead, list them at the bottom of the implementation plan as
  "Adjacent issues found, not fixed" with file paths and one-line
  descriptions, so the user can decide whether to address them as a
  follow-up.

Example: when externalising a new trigger list to YAML, look for other
hardcoded trigger lists in adjacent files. Do not externalise them all
in the same change. Do list them in the plan so the user knows.
```

## Acceptance criteria

- **I.7.1** Rule 7 exists in `~/.claude/CLAUDE.md` (the user-level file, not the project-level).
  Verified by: file path and rule text match.

- **I.7.2** The rule's example explicitly mentions the externalisation pattern this spec addresses.
  Verified by: visual inspection.

## Out of scope for I.7

- Auditing existing implementation plans for compliance with this new rule.
- Re-running prior agent work under the new rule.

---

# Definition of done — full spec

The spec is complete when:

**Phase A:**

1. All four Phase A fixes (I.1, I.2, I.3, I.4) are merged.
2. `docs/i_phaseA_status_<date>.md` exists with every Phase A criterion marked `done`, with explicit file paths.
3. `docs/spec_coverage.md` is updated to include all I.* criteria from Phase A.
4. The `couples_therapy` fixture run produces output that demonstrates I.3's improvement (the Medical Model Trap matches a keyword whose PAA questions contain at least one External Locus tag).

**Phase B (gated on user approval):**

5. Both Phase B fixes (I.5, I.6) are merged.
6. `docs/i_phaseB_status_<date>.md` exists with explicit per-function move history.
7. `pytest -q` reports zero failures.
8. The `couples_therapy` fixture produces output structurally identical to before the split.

**Phase C:**

9. Rule 7 is in the user-level `~/.claude/CLAUDE.md`.
10. `docs/spec_coverage.md` includes all I.7 criteria.

# Out of scope for this spec entirely

- Tool 2 (`Serp-compete`) work.
- Refactoring `validate_llm_report` from a 327-line function into smaller pieces.
- Changing the LLM models used.
- Replacing rules-based classifiers with ML.
- Adding new SERP intent buckets.
- Multi-language support.
- Backfilling history for runs predating any of these changes.

# Caveats the agent should not paper over

- I.1 and I.2 are pure relocations. If the agent finds itself wanting to "improve" the routing or trigger lists during the move, that is scope creep and should be deferred to a separate pass.
- I.3 is the only fix that intentionally changes behaviour. The agent should run before-and-after comparisons against the fixture to confirm the new logic produces better matches and document the diff in the status report.
- I.5 and I.6 are structural changes that historically have been the source of subtle regressions. The "one numbered step per commit" rule is binding, not advisory. If the agent combines steps and a regression appears, the status report flags this as a process violation.
- I.4 and I.7 are documentation-only. They take five minutes to do and an hour to do well. The user prefers the latter — a thoughtful one-time prevention beats a hasty rule that gets ignored.
