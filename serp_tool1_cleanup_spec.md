# Cleanup Specification: Tool 1 Outstanding Items

**Spec ID prefix:** C (for Cleanup)
**Predecessor specs:** `serp_tools_upgrade_spec_v2.md`, `serp_tool1_completion_spec.md`
**Date:** 2026-05-01

## What this spec is

After three implementation passes, three items from prior specs remain
outstanding or have drifted from spec language. This spec closes them and
establishes a clean baseline going forward.

## What this spec is NOT

This is not a re-litigation of completed work. The data layer, handoff
file, xlsx rendering, mixed-intent detection, intent mapping YAML, and
markdown Section 5b are all done well. This spec touches only what
remains.

## Workflow expectations

Per `~/.claude/CLAUDE.md`:

- Plan first (`docs/implementation_plan_<date>.md`), wait for approval,
  then execute.
- Status report on completion at `docs/c_status_<date>.md`. Evidence
  cells must include explicit file paths.
- Spec coverage matrix at `docs/spec_coverage.md` — see C.3.

---

# Fix C.1 — Section 5b prefix mismatch

## Problem

The completion spec required the markdown header `## 5b. Per-Keyword
SERP Intent`. The implementation renders `## Per-Keyword SERP Intent`
(no `5b.` prefix). The position is correct (between Sections 5 and 6);
only the heading text differs.

## Required change

In `generate_insight_report.py`, the `_render_serp_intent_section()`
function emits a header that matches the spec exactly:

```
## 5b. Per-Keyword SERP Intent
```

No other content in the section changes. The keyword sub-blocks stay as
they are.

## Acceptance criteria

- **C.1.1** The string `## 5b. Per-Keyword SERP Intent` appears exactly
  once in the rendered content_opportunities markdown for the
  `couples_therapy` fixture.
  Verified by: `tests/test_markdown_rendering.py::test_c11_section_5b_prefix_present`
- **C.1.2** The string `## Per-Keyword SERP Intent` (without prefix)
  does NOT appear in the rendered output.
  Verified by: `tests/test_markdown_rendering.py::test_c12_no_unprefixed_section_5b`

## Implementation notes

This is a one-line change in the renderer. Update the header literal,
update or add the two tests, run the suite, done. No other logic moves.

---

# Fix C.2 — SERP Intent Context line in Section 6 pattern blocks

## Background

The original M1.C requirement was a `## 1a. SERP Intent Context`
subsection inside each "Brief N: Pattern" section. The report has been
restructured: the four Bowen patterns now appear inside Section 6 ("Tool
Recommendation Assessment"), not as separate Brief sections. M1.C as
written no longer maps onto the new structure.

The intent behind M1.C still applies: each pattern recommendation should
be anchored to the SERP intent context of the keyword most associated
with that pattern. The new Section 6 already provides rich data
references but does not explicitly cite the per-keyword SERP intent
verdict.

## Required change

For each pattern block in Section 6 ("The Medical Model Trap", "The
Fusion Trap", "The Resource Trap", "The Blame/Reactivity Trap"), insert
a one-line "SERP Intent Context" italic line immediately after the
pattern subheading and before the existing paragraph content.

Format:

```
### "The Medical Model Trap"

*SERP intent context (most relevant keyword: <keyword>): <primary_intent>, confidence <confidence><, mixed: <components>>.*

<existing paragraph content...>
```

Rendering rules:

- **Most relevant keyword selection:** the keyword with the highest
  trigger count for this pattern, taken from
  `tool_recommendations_verified.verdict_inputs[<pattern>].triggers_found`
  or the equivalent existing data structure. If counts tie, use the
  keyword that appears first alphabetically. Document the choice in the
  function docstring.
- **Mixed component segment:** rendered only when `is_mixed: true` for
  the selected keyword, formatted as `, mixed: <comp1> + <comp2>`.
  Otherwise omitted.
- **Null primary_intent:** rendered as
  `primary intent insufficient data` (no confidence/mixed segments).
- **No relevant keyword found:** if no keyword has triggers for the
  pattern, render: `*SERP intent context: no keyword in this run has
  triggers for this pattern.*`

## Acceptance criteria

- **C.2.1** Each of the four pattern blocks in Section 6 contains
  exactly one line beginning with `*SERP intent context`.
  Verified by: `tests/test_markdown_rendering.py::test_c21_all_four_patterns_have_intent_context`
- **C.2.2** The Medical Model Trap's intent context line names a
  specific keyword (not literal `<keyword>`).
  Verified by: `tests/test_markdown_rendering.py::test_c22_medical_model_intent_context_has_real_keyword`
- **C.2.3** The intent context line for any pattern whose most-relevant
  keyword is "couples counselling" includes `mixed: informational + local`.
  Verified by: `tests/test_markdown_rendering.py::test_c23_mixed_intent_segment_when_applicable`
- **C.2.4** No pattern's intent context line renders the literal string
  `None`, `null`, `<keyword>`, or `<primary_intent>`.
  Verified by: `tests/test_markdown_rendering.py::test_c24_no_template_placeholders_leak`

## Implementation notes

The most-relevant-keyword selection logic should reuse whatever existing
function in `generate_content_brief.py` or `generate_insight_report.py`
already maps patterns to triggers. If no such function exists, add one
with a clear docstring; do not duplicate selection logic across multiple
sites.

If the new line breaks the existing paragraph rendering visually
(double blank lines, header crowding), adjust whitespace once after
adding the line. Do not redesign the surrounding section.

---

# Fix C.3 — Spec coverage matrix backfill

## Problem

`~/.claude/CLAUDE.md` Rule 6 requires `docs/spec_coverage.md` mapping
every spec criterion to its implementation and test. This file does not
exist. The work spans three prior specs and ~50+ criteria.

## Required change

Create `docs/spec_coverage.md` containing a single table that covers
every acceptance criterion from:

1. `serp_tools_upgrade_spec_v2.md` (Tool 1 Gaps 1, 2, 3, 4, 5; cross-cutting items)
2. `serp_tool1_fix_spec.md` (Fixes 1 through 8)
3. `serp_tool1_completion_spec.md` (Fix M1, M2, M3)
4. This spec (`serp_tool1_cleanup_spec.md`, IDs C.1 through C.3)

The table has six columns:

| Spec ID | Spec File | Description | Implementation | Test | Status |

Where:

- **Spec ID** is the criterion's hierarchical ID, verbatim from the spec.
- **Spec File** is the filename of the spec where the criterion appears
  (short form: `v2`, `fix`, `completion`, `cleanup`).
- **Description** is a one-line paraphrase of the criterion.
- **Implementation** is the file path (and function/method if applicable)
  where the criterion is satisfied. If the criterion is "file exists,"
  this is the file path. If satisfied in multiple files, list all.
- **Test** is the test name (`test_file.py::test_name`) that asserts
  the criterion. For criteria not covered by automated tests, write
  `manual` and add a row to a separate "Manual Verification" subsection
  below the main table.
- **Status** is one of: `done`, `partial`, `not done`, `superseded`.
  - `superseded` is used for criteria from earlier specs that are
    explicitly replaced by later specs (e.g. M1.C is superseded by C.2).

## Implementation notes

This is a documentation task, not a code task. The agent reads each
spec, extracts every numbered or bulleted acceptance criterion, and
populates the table by inspecting the codebase to find where each is
satisfied.

If a criterion cannot be located in the codebase, the agent marks it
`not done` rather than `done` — even if a previous status report
claimed it was done. The spec coverage matrix is the new source of
truth; previous status reports are historical artifacts.

For criteria where multiple acceptable implementations exist (e.g.
"file exists at repo root or in `config/`"), record the actual location.

## Acceptance criteria

- **C.3.1** `docs/spec_coverage.md` exists with a table containing one
  row per criterion from all four specs.
  Verified by: file existence at exact path `docs/spec_coverage.md`
- **C.3.2** The table contains at least 50 rows (rough lower bound on
  total criteria across the four specs; agent may have more).
  Verified by: `tests/test_spec_coverage.py::test_c32_minimum_row_count`
- **C.3.3** Every row has all six columns populated; no empty cells
  except where the Test column is `manual` (in which case the Manual
  Verification section below the table has a corresponding entry).
  Verified by: `tests/test_spec_coverage.py::test_c33_no_empty_cells`
- **C.3.4** Every Implementation cell that names a file path refers to
  a file that exists in the repo (or a path the agent has explicitly
  flagged as missing in the Status column).
  Verified by: `tests/test_spec_coverage.py::test_c34_implementation_paths_exist`
- **C.3.5** Every Test cell that names a test refers to a test that
  exists in the test suite. Run `pytest --collect-only` and grep for
  each named test.
  Verified by: `tests/test_spec_coverage.py::test_c35_named_tests_exist`
- **C.3.6** The Manual Verification subsection lists every criterion
  whose Test cell is `manual`, with a one-line description of how a
  human reviewer would check it.
  Verified by: `tests/test_spec_coverage.py::test_c36_manual_section_complete`

## Note on M1.C and the new Section 6 structure

When the agent encounters M1.C ("`## 1a. SERP Intent Context` in each
content brief") during the backfill, it marks the row:

- Status: `superseded`
- Implementation: `superseded by C.2 — see new spec`
- Test: `n/a — superseded`

This is the explicit way to honour the structural change rather than
silently dropping the criterion.

---

# Fix C.4 — Status report file location convention

## Problem

The May 1 status report (`v2_dod_status_20260501_final.md`) was placed
in the project root. The CLAUDE.md rule says status reports go in
`docs/`. Going forward, every status report lives in `docs/`. The
existing file should be moved.

## Required change

- Move `v2_dod_status_20260501_final.md` to
  `docs/v2_dod_status_20260501_final.md`.
- All future status reports go in `docs/`.

## Acceptance criteria

- **C.4.1** `docs/v2_dod_status_20260501_final.md` exists.
  Verified by: file existence check.
- **C.4.2** No file named `v2_dod_status_*.md` exists at the repo root
  (i.e., the move was a move, not a copy).
  Verified by: shell command `ls *.md | grep -c v2_dod_status` returns 0.
- **C.4.3** This cleanup spec's own status report is named
  `docs/c_status_<date>.md`.
  Verified by: file existence at the named path.

---

# Definition of done

The cleanup work is complete when ALL of these are true:

1. `docs/c_status_<date>.md` exists with every C-prefix criterion
   marked `done` and an explicit file path or test name as evidence.
2. `docs/spec_coverage.md` exists per C.3 with all rows populated.
3. The two markdown rendering tests (C.1) pass.
4. The four pattern intent context tests (C.2) pass.
5. The five spec coverage tests (C.3.2 through C.3.6) pass.
6. `pytest -q` reports zero failures, zero errors. Skipped tests are
   acceptable if they were already skipped before this work.
7. The legacy status report has been moved to `docs/`.

## Out of scope

- Re-evaluating any work marked `done` in the existing
  `v2_dod_status_20260501_final.md`. The cleanup spec assumes prior
  done work is correctly done unless C.3 surfaces a missing
  implementation file.
- Any new feature work. This is purely a cleanup pass.
- Editing the intent_mapping.yml file beyond what's needed to support
  C.2's keyword-selection logic.

## Caveats the agent should not paper over

- If C.3 surfaces criteria that were claimed done but cannot be
  located in the codebase, the agent reports them with status
  `not done` and stops to surface this to the user before continuing.
  Do not silently re-implement.
- If the most-relevant-keyword selection in C.2 cannot find a clear
  winner (e.g. all keywords have zero triggers for a pattern), the
  agent uses the "no keyword in this run has triggers" rendering and
  documents which patterns hit this case in the status report.
- The CLAUDE.md path-evidence rule applies. Every "file exists"
  evidence cell in the status report must include the full path.
