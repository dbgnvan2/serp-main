# Completion Specification: Tool 1 Final Pass

## Reading order

This document supplements `serp_tool1_fix_spec.md`. Where they disagree, this document wins.

## What this document is

The agent has implemented the Tool 1 v2 upgrade across three passes. Two passes left material work undone. This document closes the remaining gaps and establishes a verification protocol that prevents another partial pass.

## Status as of the last run (`market_analysis_couples_therapy_20260501_0828`)

Verified done from output inspection:

- Confidence denominator fix (Fix 1)
- `intent_distribution` schema (Fix 2)
- Handoff file production (Fix 3)
- xlsx rendering (Fix 4 — xlsx portion)
- Mixed-intent detection logic (working in practice)
- Title pattern detection (working; thresholds correctly produce `null` dominant patterns for SERPs without clear pattern dominance)

Verified NOT done from output inspection:

- Markdown rendering (Fix 4 — markdown portion). No "Per-Keyword SERP Intent" section, no Mixed-Intent Strategic Note, no "1a. SERP Intent Context" in briefs.

Cannot verify from output (must be confirmed by repo inspection):

- Classifier audit script and documentation (Fix 5)
- `intent_mapping.yml` extraction and rationale doc (Fix 6)
- Validator rule updates (Fix 7)
- README and documentation updates (Fix 8)
- Mandatory status report against v2 Definition of Done

This document treats "cannot verify" as "not done" until the agent produces evidence.

---

## Operating rules for this pass

These rules apply to the agent for the duration of this work and are non-negotiable.

### Rule 1: The status report is the first deliverable, period.

Before any code changes, the agent commits `docs/v2_dod_status_<date>.md` containing:

- Every Definition-of-Done item from `serp_tools_upgrade_spec_v2.md` (items 1 through 8 in that document's "Definition of done" section)
- Every fix from `serp_tool1_fix_spec.md` (Fixes 1 through 8 plus the mandatory first deliverable)
- For each item: status (`done` / `not done` / `partial` / `n/a`), file path(s) of the implementation, commit hash that introduced it, and a one-line evidence statement (e.g. "field appears in keyword_profiles per JSON inspection of run 20260501_0828")
- For each `partial` item: what specifically is missing
- For each `not done` item: explanation of why it was skipped, if known

The agent does not begin further code changes until this document is committed. If the agent begins code changes before this document exists, the work is rejected on procedural grounds regardless of quality.

### Rule 2: Acceptance is gated on output, not on assertion.

For every acceptance criterion in this document, the agent provides one of:

- A specific line in a specific file (e.g. `generate_content_brief.py:347`)
- A specific test that asserts the criterion (e.g. `tests/test_brief_rendering.py::test_mixed_intent_callout`)
- A specific output artefact (e.g. "the string 'Mixed-Intent Strategic Note' appears in `market_analysis_*.md` line N")

The agent does not write "implemented" or "complete" without one of these three forms of evidence.

### Rule 3: If a required artefact does not exist, do not proceed past it.

The status report must exist before code work begins. The audit script (Fix 5) must exist before its claimed effects are accepted. The validator rules (Fix 7) must exist before LLM-facing changes are merged. Skipping a prerequisite invalidates downstream work.

### Rule 4: No silent work.

The agent does not refactor, rename, or restructure unrelated code during this pass. If a refactor is required to enable a fix, it is called out separately in the status report. The user has not authorised general code maintenance.

### Rule 5: Honest failure beats false success.

If the agent encounters a blocker — a fixture that doesn't behave as expected, an upstream module that produces unexpected types, a test that can't be made to pass — the agent reports the blocker in the status report rather than working around it silently or marking the item complete. The user has stated a preference for accuracy over completion claims.

---

# Fix M1 — Markdown rendering

## Problem

The markdown report does not surface any of the new pre-computed fields. From the user's perspective opening the `.md` file, the v2 upgrade is invisible. The xlsx received the rendering work; the markdown did not. This was already required by `serp_tool1_fix_spec.md` Fix 4 and was the most user-visible part of that fix.

## Required change

`generate_content_brief.py` (or whichever module assembles the markdown — agent identifies which) is updated to produce three new pieces of content. The report's existing structure is preserved; new content is additive.

### M1.A — New section between current Sections 5 and 6

Header: `## 5b. Per-Keyword SERP Intent`

Below the header, one block per keyword in the order they appear in `keyword_profiles`. Each block:

```
### <keyword text>

- **Primary intent:** <primary_intent> *(confidence: <confidence>)*
- **Distribution:** <bucket1>: <count1>, <bucket2>: <count2>, ... over <classified_organic_url_count> of <organic_url_count> classified URLs
- **Mixed-intent components:** <components joined by ", ">
- **Strategy:** <mixed_intent_strategy>
- **Title patterns:** <dominant_pattern> dominant
- **Local pack present:** yes
```

Rendering rules for each line:

- **Primary intent line:**
  - When `primary_intent` is a string: render as shown above.
  - When `primary_intent` is `null`: render as `- **Primary intent:** insufficient data — only <classified_organic_url_count> of <organic_url_count> URLs could be classified`.
- **Distribution line:**
  - Always rendered. Buckets with count 0 are omitted from the comma-separated list. If all counts are 0, the entire line reads `- **Distribution:** no URLs classified`.
- **Mixed-intent components line:**
  - Rendered only when `is_mixed` is `True`. Otherwise the line is omitted entirely.
- **Strategy line:**
  - Rendered only when `mixed_intent_strategy` is non-null. Otherwise omitted.
- **Title patterns line:**
  - When `dominant_pattern` is a string: rendered as shown.
  - When `dominant_pattern` is `null`: rendered as `- **Title patterns:** no dominant pattern detected`.
- **Local pack line:**
  - Rendered only when `evidence.local_pack_present` is `True`. Otherwise omitted.

### M1.B — Mixed-Intent Strategic Note in Section 4

For each keyword whose `mixed_intent_strategy` is not `null`, insert a callout block at the top of Section 4 (above the four Bowen pattern blocks):

```
### ⚖️ Mixed-Intent Strategic Note: <keyword>

This keyword shows mixed search intent (<comp1> + <comp2>). Recommended approach: **<mixed_intent_strategy>**.

<one-line description matching the strategy value>
```

Strategy descriptions (use exactly these strings):

- `compete_on_dominant`: "Match the dominant intent format directly. The client's existing content posture aligns with the most-represented intent in this SERP."
- `backdoor`: "Produce content matching a non-dominant but client-aligned intent. Likely to outrank head-on competitors via differentiation."
- `avoid`: "No good fit for the client's content capabilities. Skip this keyword."

If multiple keywords have non-null strategies, render multiple callouts, one per keyword, in the order they appear in `keyword_profiles`.

### M1.C — "1a. SERP Intent Context" in each content brief

In each `## Brief N: <Pattern>` section, immediately before `## 1. The Core Conflict`, insert:

```
## 1a. SERP Intent Context

For the most relevant keyword (<keyword>):
- Intent: <primary_intent> *(confidence: <confidence>)*
- Title pattern: <dominant_pattern or "no dominant pattern">
- Mixed: <yes/no>

This brief targets the <intent slot description> intent slot.
```

Rules:

- **Most relevant keyword selection**: the agent uses the same logic that currently selects which keyword's PAA questions appear in the brief's "User Intent & Anxiety" section. Whatever that logic is, reuse it. Do not invent a new selection heuristic.
- **Intent slot description**: derived from `primary_intent` value:
  - `informational` → "informational/educational"
  - `commercial_investigation` → "research/comparison"
  - `transactional` → "service/booking"
  - `navigational` → "brand-search"
  - `local` → "local-service"
  - `mixed` → "mixed (see Section 5b for components)"
  - `null` → "undetermined"
- If no keyword can be selected for a brief (PAA logic returns nothing), render `## 1a. SERP Intent Context\n\nNo directly mapped keyword for this brief.`

## Acceptance criteria

The criteria below are checked by running the pipeline against the existing `couples_therapy` fixture. The fixture's data is already known.

- [ ] Section `## 5b. Per-Keyword SERP Intent` exists in the rendered markdown, between Section 5 and Section 6.
- [ ] All 6 keyword blocks appear in Section 5b.
- [ ] The block for "couples counselling" contains `Mixed-intent components` and `Strategy: backdoor` lines.
- [ ] The block for "How much is couples therapy in Vancouver?" does NOT contain a `Mixed-intent components` line (this keyword has `is_mixed: false`).
- [ ] The block for "What type of therapist is best for couples therapy?" contains the `Local pack present: yes` line (this keyword has `local_pack_present: true`).
- [ ] One Mixed-Intent Strategic Note callout appears in Section 4, for the "couples counselling" keyword. The string `backdoor` appears in the rendered markdown.
- [ ] All four content briefs contain a `## 1a. SERP Intent Context` subsection.
- [ ] No content brief's 1a subsection renders the literal string `None` or `null`. Null values are mapped per the rules above.
- [ ] Running the pipeline produces a markdown file in which the regex `Section 5b\. Per-Keyword SERP Intent` appears exactly once, and the regex `1a\. SERP Intent Context` appears exactly four times (once per brief).
- [ ] A new test `tests/test_markdown_rendering.py` asserts each of the above against fixture output.

---

# Fix M2 — Provide evidence for Fixes 5–8 from the previous spec

The agent claimed (or implied via output behaviour) that some of these fixes were done. None can be verified from the output alone. This fix produces the verification artefacts.

## M2.A — Classifier audit (Fix 5 of `serp_tool1_fix_spec.md`)

The agent confirms whether `scripts/classifier_audit.py` exists. If it does, the agent runs it against the `couples_therapy` fixture and commits the output as `docs/classifier_audit_couples_therapy_<date>.md`.

If it does not exist, the agent creates it per the original Fix 5 specification and runs it.

The output document includes:

- Total URLs classified across the fixture run
- Count and percentage classified as `other` content type
- Top 10 domains contributing the most `other` classifications
- For 20 sample `other` URLs: the URL, title, and a one-sentence agent assessment of what type it likely is

If pattern-based classification rules were added (per Fix 5b), the agent commits `docs/classifier_residual_<date>.md` showing classification rates before and after the new rules.

## M2.B — Intent mapping rationale (Fix 6)

The agent commits `intent_mapping.yml` (extracted from wherever the mapping currently lives) and `docs/intent_mapping_rationale.md`. The rationale doc explicitly addresses the three v2 edge cases:

1. A `service` URL on a `directory` entity (e.g. a Psychology Today profile page)
2. A `guide` URL on a counselling provider with local pack present
3. AI Overview presence on the SERP

Each edge case gets: the mapping decision, the reasoning, and one example URL from the fixture run that exemplifies the case.

## M2.C — Validator rules (Fix 7)

The agent commits a list of validator rules now in effect, with a one-line description and severity (HARD / SOFT) for each. The list is committed as `docs/validator_rules_<date>.md`.

For each new field added in v2 (`primary_intent`, `is_mixed`, `confidence`, `dominant_pattern`, `mixed_intent_strategy`), the doc states:

- Whether a validator rule exists
- The rule's severity
- The path to the test that asserts the rule catches a contradicting LLM output
- If no rule exists for a field: explanation of why

If any of the five fields lack rules, the agent adds them per the original Fix 7 specification before declaring this work complete.

## M2.D — README and documentation (Fix 8)

The agent confirms the README contains the four sections required by Fix 8 (What's new, Output files, Backwards compatibility note, Tool 1 → Tool 2 handoff). If any are missing, they are added now.

The agent also confirms `docs/handoff_contract.md` exists and addresses the schema and consumption expectations. If missing, it is added.

## Acceptance criteria for Fix M2

- [ ] `docs/classifier_audit_couples_therapy_<date>.md` exists and contains the classifier audit output.
- [ ] `intent_mapping.yml` exists at the repo root or in `config/`.
- [ ] `docs/intent_mapping_rationale.md` exists and addresses all three edge cases by name.
- [ ] `docs/validator_rules_<date>.md` exists and explicitly addresses each of the five new fields.
- [ ] All five new fields have validator rules and tests; OR the rationale doc explains for each missing rule why it is acceptable to ship without one. The user reviews these explanations before they are accepted.
- [ ] `README.md` contains the four sections required by Fix 8.
- [ ] `docs/handoff_contract.md` exists.

---

# Fix M3 — Handoff schema clarification

## Problem

The `competitor_handoff_*.json` `targets` array contains both `source_keyword` and `primary_keyword_for_url` fields. The fix spec only required `source_keyword`. The two fields' relationship is not documented.

## Required change

The agent does one of:

- **Option A**: If the two fields hold different values for some targets, document the difference in `docs/handoff_contract.md` with at least one fixture example showing the divergence.
- **Option B**: If the two fields are always identical, remove `primary_keyword_for_url` and update the schema and handoff writer accordingly.

The agent inspects the existing handoff file (`competitor_handoff_couples_therapy_20260501_0832.json`) to determine which option applies.

## Acceptance criteria

- [ ] Either Option A or Option B is implemented. The status report says which.
- [ ] If Option B, the handoff schema and any consuming code in `serp-main` is updated. (Tool 2 currently expects `source_keyword` per the v2 spec, so removing the duplicate is the safer choice.)

---

# Definition of done — final pass

This pass is complete when ALL of the following are true:

1. `docs/v2_dod_status_<date>.md` exists and shows every v2 DoD item and every prior fix as `done` with evidence.
2. The markdown renderer produces all three new pieces of content (M1.A, M1.B, M1.C) per the acceptance criteria.
3. Re-running the pipeline against the `couples_therapy` fixture produces a markdown file that visually shows the SERP intent verdict, the mixed-intent strategic note, and the per-brief context subsections.
4. The verification artefacts for Fix 5, 6, 7, 8 (Fix M2 above) all exist.
5. The handoff schema clarification (M3) is resolved one way or the other.
6. `pytest` passes including the new markdown rendering tests.
7. The user can read only the markdown report and understand the SERP intent for every keyword without opening the JSON.

---

# Caveats

- If the agent finds a discrepancy between this spec and the v2 spec or the previous fix spec, the agent flags the discrepancy in the status report and asks before resolving it. Do not silently pick.
- If the agent encounters a fixture data issue that prevents an acceptance criterion from being met, the agent reports the blocker in the status report. The user prefers a documented blocker over an undocumented workaround.
- The agent does not interpret "the markdown should be readable" as licence to redesign the report. The existing structure is kept; new content is added in the specified locations.
- The user has noted a pattern across previous passes of data-layer work being completed while user-facing surfaces are skipped. The agent should treat the markdown rendering as the load-bearing deliverable of this pass, not as an extra.
