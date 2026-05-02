# Fix Specification: Tool 1 (`serp-discover`) — v2 Implementation Gaps

## Status of this document

This is a follow-up to `serp_tools_upgrade_spec_v2.md`. The agent has made a partial implementation pass on Tool 1. This document specifies the gaps that remain between the May 1 output (`market_analysis_couples_therapy_20260501_0717.json`) and what v2 required.

This document does NOT supersede v2. It supplements v2 by being more explicit about the parts where the implementation went off-track or stopped short. Where this document and v2 disagree, this document wins.

The agent should treat **Acceptance criteria** subsections as binding. **Implementation notes** are guidance.

## Reading before changing

Before writing any code:

1. Re-read v2 sections "Definition of Done," "Design Principles," and Tool 1 Gaps 1–5.
2. Open `market_analysis_couples_therapy_20260501_0717.json` and inspect `keyword_profiles` — confirm that the issues described below match the observed output. If something in this document does not match the file, stop and report; do not work around.
3. Read the current `serp_audit.py`, `generate_content_brief.py`, and the prompt files. Identify where intent classification is computed and where reports are assembled.

## Mandatory first deliverable

Before any code changes are merged, the agent produces a **status report against v2's Definition of Done**, item by item (1 through 8), with file paths and commit hashes for each item that is claimed to be complete, and explicit "not done" markers for the rest. The status report is committed as `docs/v2_dod_status_<date>.md`.

This is non-negotiable. The user has already been told the work was done once when material parts of it were not. The status report establishes a baseline of what has actually shipped.

---

# Fix 1 — Confidence denominator

## Problem

In the May 1 output, every keyword has `serp_intent.confidence: low`. The cause is the denominator: `evidence.classified_url_count / evidence.total_url_count` is being computed across *all URLs returned anywhere in the SERP*, including local pack entries, discussions/forums, related results, knowledge panels, and so on.

For "couples counselling," the output shows `classified: 6/27 (21 uncategorised)`. The 27 includes 14 counselling-domain URLs plus directories plus media plus local pack entries. The intent verdict is being computed against this whole pool.

The v2 spec said classification operates on "the top 10 URLs" of the SERP — meaning the top organic results. With the wrong denominator, no SERP can ever score above `low` confidence, which makes the field useless.

## Required change

`serp_intent.evidence` is computed strictly over the organic-results list, capped at the top 10. The denominator is `min(10, len(organic_results_for_keyword))`.

**URLs that count:**
- Top 10 (or fewer, if fewer were returned) entries from the standard organic results module.

**URLs that do NOT count toward the denominator or distribution:**
- Local pack / map pack entries (these are surfaced separately and have their own intent signal — see below)
- Discussions/forums module
- People Also Ask URLs
- Related searches
- AI Overview citations
- Featured snippet (the source URL is already in organic, do not double-count)
- News carousel entries unless they are also in the organic top 10

**Local pack as an intent signal, not a denominator member:**
- The presence of a local pack module already shifts intent in the v2 mapping rules (`service` + `counselling` entity + local pack present → `local`).
- Local pack member URLs are not added to `intent_distribution` directly. Their effect on the verdict is via the boost rule, not via counting.

## Schema after this fix

```json
"serp_intent": {
  "primary_intent": <string>|null,
  "intent_distribution": {
    "informational": <int>,
    "commercial_investigation": <int>,
    "transactional": <int>,
    "navigational": <int>,
    "local": <int>
  },
  "is_mixed": <bool>,
  "mixed_components": [<string>, ...],
  "confidence": "high"|"medium"|"low",
  "evidence": {
    "organic_url_count": <int>,
    "classified_organic_url_count": <int>,
    "uncategorised_organic_url_count": <int>,
    "intent_counts": {
      "informational": <int>,
      "commercial_investigation": <int>,
      "transactional": <int>,
      "navigational": <int>,
      "local": <int>,
      "uncategorised": <int>
    },
    "local_pack_present": <bool>,
    "local_pack_member_count": <int>
  }
}
```

The fields `total_url_count` and `classified_url_count` are renamed to `organic_url_count` and `classified_organic_url_count` to make the scope unambiguous. `uncategorised_count` is renamed to `uncategorised_organic_url_count` for the same reason. `intent_counts` keeps its name but its values are computed only over organic.

## Confidence rules (restated, with the corrected denominator)

Let `n = classified_organic_url_count` and `N = organic_url_count`.

- `confidence: high` if `n >= 8` AND `N >= 8`
- `confidence: medium` if `n >= 5` AND `N >= 5`
- `confidence: low` otherwise
- If `n < 5`, `primary_intent` is `null`. The `intent_distribution`, `is_mixed`, and `mixed_components` are still populated from what was classified, but the verdict is withheld.

## Acceptance criteria

- [ ] The denominator is the top-10 organic results, period. Verified by adding a test that constructs a SERP with 10 organic + 5 local pack + 8 forum URLs and asserts the denominator is 10.
- [ ] Schema field names are renamed per above. Old names do not appear in new output.
- [ ] On the May 1 fixture (`couples_therapy`), at least 3 of 6 keywords now score `medium` or `high` confidence. (If they don't, the upstream `ContentClassifier` is producing too many `other` results — escalate to Fix 5 rather than papering over.)
- [ ] When `n < 5`, `primary_intent` is exactly the JSON value `null`, not the string `"null"` or omitted.
- [ ] Unit tests cover: 10 classified organic → high; 5 classified organic + 5 unknown → medium; 4 classified organic → low + null primary; 8 organic + many other modules (denominator stays 10).

---

# Fix 2 — `intent_distribution` schema mismatch

## Problem

The May 1 output stores fractions (`0.5`, `0.166...`) in `intent_distribution`, while `evidence.intent_counts` stores integers. The v2 spec required integers. Two fields holding the same information in different shapes is a source of bugs.

## Required change

`intent_distribution` is a dict of integer counts, matching the spec exactly. `evidence.intent_counts` is removed (it duplicates `intent_distribution` after this change).

If downstream code needs proportions, it derives them from the counts at the point of use:

```python
proportions = {
    bucket: count / max(1, organic_url_count)
    for bucket, count in intent_distribution.items()
}
```

## Acceptance criteria

- [ ] `intent_distribution` values are all integers in the JSON output.
- [ ] `evidence.intent_counts` no longer appears.
- [ ] All existing call sites that read `intent_distribution` are updated. Run grep across both repos to confirm.
- [ ] Schema validation (if implemented) requires integer types for all five buckets.

---

# Fix 3 — `competitor_handoff_*.json` is missing

## Problem

The May 1 output directory contains `.json`, `.md`, and `.xlsx`. There is no `competitor_handoff_*.json`. v2 Tool 1 Gap 3 required this file. It is the contract between Tool 1 and Tool 2; without it, Tool 2 has no upgraded data source.

## Required change

The handoff file is produced as part of the standard pipeline run, not as an opt-in flag. Specifically:

1. Tool 1's main pipeline (`run_pipeline.py` or whatever currently triggers report generation) calls a new function `write_competitor_handoff(keyword_profiles, organic_results, config) -> Path` after the JSON, MD, and XLSX outputs have been written.
2. The function writes `competitor_handoff_<topic>_<run_timestamp>.json` to the same output directory as the other artefacts.
3. The function validates the output against `handoff_schema.json` before writing. Validation failure aborts the write, logs the schema violation with the specific field that failed, and prevents the run from being marked successful. The other output files are NOT deleted on handoff validation failure — the user can still see what was produced.
4. The handoff file is produced even when `keyword_profiles` is empty (writes a valid, empty `targets` list). It is NOT produced if `organic_results` is also empty (no SERP data was collected at all — there is nothing to hand off).

## File contents (restated from v2, with corrections)

```json
{
  "schema_version": "1.0",
  "source_run_id": "<id>",
  "source_run_timestamp": "<ISO 8601>",
  "client_domain": "<domain>",
  "client_brand_names": ["<name>", ...],
  "targets": [
    {
      "url": "<full URL>",
      "domain": "<host>",
      "rank": <int>,
      "entity_type": "<type>",
      "content_type": "<type>",
      "title": "<title>",
      "source_keyword": "<keyword>"
    }
  ],
  "exclusions": {
    "client_urls_excluded": <int>,
    "omit_list_excluded": <int>,
    "omit_list_used": ["<domain>", ...]
  }
}
```

## Selection logic for `targets`

For each keyword in `keyword_profiles`:

1. Take the top N organic URLs (default N=10, configurable in `config.yml` at `audit_targets.n`).
2. Exclude any URL whose domain matches the client domain.
3. Exclude any URL whose domain is in `audit_targets.omit_from_audit` list (default empty).
4. Add each remaining URL to `targets` with the source keyword recorded.

If a URL appears in the top 10 of multiple keywords, it appears in `targets` multiple times, once per `source_keyword`. This is intentional — Tool 2 uses `source_keyword` for context on why each target matters.

## Schema file location

`handoff_schema.json` is committed to the repo root of `serp` (and synced manually to `serp-main` per v2). The file uses JSON Schema draft-07. The agent writes a brief `docs/handoff_contract.md` documenting which fields are required, which are optional, and how Tool 2 is expected to consume them.

## Acceptance criteria

- [ ] `handoff_schema.json` exists at the `serp` repo root with all required fields marked required in the schema.
- [ ] Running the existing pipeline against the `couples_therapy` fixture produces `competitor_handoff_couples_therapy_<timestamp>.json` alongside the other outputs.
- [ ] The handoff file validates against the schema. Validation is asserted in a test.
- [ ] A test crafts an invalid handoff (missing required field) and confirms validation fails with a clear error.
- [ ] A test runs the pipeline with no organic results and confirms no handoff file is written.
- [ ] A test runs the pipeline with all organic URLs being client URLs and confirms a handoff file IS written, with empty `targets` and `client_urls_excluded > 0`.
- [ ] `docs/handoff_contract.md` exists.

---

# Fix 4 — Report rendering does not surface new fields

## Problem

The May 1 markdown report and xlsx are essentially identical to the previous run's. None of the new pre-computed fields appear in user-facing output:

- No SERP intent verdict per keyword
- No title pattern summary
- No mixed-intent strategy callout
- The strategic recommendations section is unchanged from before the upgrade

v2 Design Principle 3 required downstream consumers to be updated in the same change set. They were not. From the user's perspective, the upgrade is invisible.

## Required change — markdown report (`generate_content_brief.py` or equivalent)

The markdown report gains the following changes. Existing sections remain; new content is additive.

### New Section: "Per-Keyword SERP Intent" (between current Sections 5 and 6)

For each keyword, render a block:

```
### <keyword>

- **Primary intent:** <primary_intent>  *(confidence: <confidence>)*
- **Distribution:** <bucket1>: <count1>, <bucket2>: <count2>, ... (over <N> classified organic URLs)
- **Mixed-intent components:** <comp1>, <comp2>   [only if is_mixed]
- **Strategy:** <mixed_intent_strategy>             [only if mixed_intent_strategy is non-null]
- **Title patterns:** <dominant_pattern> dominant   [only if dominant_pattern is non-null]
                       OR  No dominant pattern detected   [if dominant_pattern is null]
```

Null/absent value handling:

- `primary_intent: null` → render as: `- **Primary intent:** insufficient data (only <n> of <N> URLs classified)`
- `is_mixed: false` → omit the "Mixed-intent components" line entirely
- `mixed_intent_strategy: null` → omit the "Strategy" line entirely
- `dominant_pattern: null` → render the "No dominant pattern detected" variant

### Modify Section 4 ("Strategic Recommendations") for mixed-intent keywords

For any keyword whose `mixed_intent_strategy` is not null, add a callout to Section 4 *before* the four Bowen patterns:

```
### ⚖️ Mixed-Intent Strategic Note

The keyword **<keyword>** shows mixed search intent (<comp1> + <comp2>). Recommended approach: **<mixed_intent_strategy>**.

- *compete_on_dominant*: Match the dominant intent format directly.
- *backdoor*: Produce content matching a non-dominant but client-aligned intent. Likely to outrank head-on competitors via differentiation.
- *avoid*: No good fit for the client's content capabilities.
```

(Render only the bullet matching the actual strategy value; omit the others.)

### Per-keyword content brief sections

In each "Brief N: <Pattern>" section, add a new subsection between sections 1 and 2:

```
## 1a. SERP Intent Context

For the highest-ranked relevant keyword:
- Intent: <primary_intent>
- Confidence: <confidence>
- Title patterns: <dominant_pattern or "no dominant pattern">

This brief targets the [informational | local | etc.] intent slot.
```

Logic for "highest-ranked relevant keyword": pick the keyword from `keyword_profiles` whose top organic results most overlap with this brief's "Triggers found" — agent's choice of similarity heuristic, but document the choice. If overlap is empty, render: "No directly mapped keyword for this brief."

## Required change — xlsx (`reporting.py` or wherever the xlsx is built)

Add three new columns to the `Overview` sheet:

- `Primary_Intent` — the value of `serp_intent.primary_intent`, or `null` literal text if null
- `Intent_Confidence` — the value of `serp_intent.confidence`
- `Mixed_Intent_Strategy` — the value of `mixed_intent_strategy`, blank if null

Add a new sheet `SERP_Intent_Detail` with one row per keyword and columns:

```
Root_Keyword | Run_ID | Primary_Intent | Is_Mixed | Mixed_Components |
Confidence | Organic_URL_Count | Classified_Count |
Informational_Count | Commercial_Investigation_Count |
Transactional_Count | Navigational_Count | Local_Count | Uncategorised_Count |
Local_Pack_Present | Title_Dominant_Pattern
```

## Acceptance criteria

- [ ] The markdown report contains the new "Per-Keyword SERP Intent" section.
- [ ] Mixed-intent keywords trigger the strategic note in Section 4.
- [ ] Each content brief contains the "1a. SERP Intent Context" subsection.
- [ ] Null values render correctly per the rules above (no `None` or `null` strings appearing inappropriately, no empty bullet points).
- [ ] The xlsx `Overview` sheet has the three new columns.
- [ ] The xlsx contains the new `SERP_Intent_Detail` sheet.
- [ ] Re-running against the `couples_therapy` fixture produces a markdown report where the keyword "couples counselling" shows `is_mixed: true`, `mixed_intent_strategy: backdoor`, and the strategic note callout appears.
- [ ] Visual inspection: a user reading only the markdown should be able to identify which keywords are mixed-intent and what the recommended strategy is, without ever opening the JSON.

---

# Fix 5 — Mass uncategorisation of organic URLs

## Problem

Across the May 1 fixture, 60–80% of URLs in each SERP are classified as `other` content type by the upstream `ContentClassifier` and therefore land in `uncategorised` in the intent mapper. Examples in the top-5 of "couples counselling": "Reignite Love with Couples Counselling Vancouver" → classified as `directory` (probably wrong; this is a service page). "The Relationship Clinic: Relationship Therapy in North & West..." → classified as `other` (this is clearly a service page).

This means:

1. The intent verdict is being computed from a small fraction of each SERP.
2. Even after Fix 1 corrects the denominator, confidence will often remain `low` because of upstream classification gaps.
3. The Bowen reframe content briefs are built on a partial picture of the competitive landscape.

The classifier is not the v2 spec's responsibility, but the practical impact is severe enough that ignoring it makes Fixes 1–4 less useful than they should be.

## Required change

The agent does NOT redesign `ContentClassifier`. The agent does these three things instead:

### 5a. Diagnose

Add a one-time diagnostic script `scripts/classifier_audit.py` that:

1. Loads a fixture run's organic results.
2. For each URL classified as `other`, prints the URL, title, and snippet.
3. Groups them by domain and reports which domains contribute the most `other` classifications.

This is run once against the `couples_therapy` fixture to see the actual distribution. Output is committed as `docs/classifier_audit_couples_therapy.md` for review.

### 5b. Add fallback content-type rules

After running the diagnostic, propose specific fixes to `ContentClassifier` based on what was actually misclassified. Likely suggestions (the agent decides based on the diagnostic):

- URLs containing `/service/`, `/services/`, `/therapy/`, `/counselling/`, `/our-team/` on a counselling-entity domain → `service`.
- URLs that are bare domain roots (e.g. `https://relationshipclinic.ca/`) on a counselling-entity domain → `service` (homepage of a service provider).
- URLs containing `/blog/`, `/articles/`, `/posts/` → `guide`.

These rules go in `domain_overrides.yml` or a new `url_pattern_rules.yml` — externalised, not hard-coded. The agent does NOT add them to `.py` files.

### 5c. Document the residual

After the rules are added, re-run the audit. Whatever percentage of `other` classifications remain after the new rules go in `docs/classifier_residual_<date>.md` with the agent's recommendation: "acceptable — confidence will remain `medium` for queries with X characteristics" or "requires further work."

## Acceptance criteria

- [ ] `scripts/classifier_audit.py` exists and runs against any fixture run.
- [ ] `docs/classifier_audit_couples_therapy.md` exists with the actual distribution.
- [ ] At least one new pattern-based classification rule has been added to a YAML config file.
- [ ] After Fix 5, re-running the `couples_therapy` fixture shows: at least one keyword that previously had `confidence: low` (after Fix 1) now scores `medium` or higher. If none do, the agent escalates with a written explanation rather than declaring success.
- [ ] `docs/classifier_residual_<date>.md` exists.

## Important constraint

The agent does NOT change the existing taxonomy of content types (`guide`, `service`, `directory`, `news`, `pdf`, `other`). The fix is to classify *into* the existing taxonomy more accurately, not to invent new types.

---

# Fix 6 — `intent_mapping.yml` was not submitted for review

## Problem

v2 Tool 1 Gap 1 required: "the **first deliverable for this gap is a draft `intent_mapping.yml` plus a written rationale committed as a separate PR for review**. The user (Dave) approves or amends the mapping before any code that consumes it is merged."

This step was skipped. Code consuming the mapping shipped without the user seeing the mapping. The mapping table is editorial — it encodes assumptions about what `service` URLs and `directory` entities mean for intent — and the user has the final say.

## Required change

The agent:

1. Locates the actual intent-mapping logic in the current code (it may be in YAML, in a Python dict, or hard-coded in a function).
2. Extracts it to `intent_mapping.yml` if it isn't already in YAML form.
3. Commits a separate PR titled `docs: intent_mapping for review` containing:
   - The YAML file
   - A `docs/intent_mapping_rationale.md` explaining each mapping decision and the edge cases (the v2 spec listed three edge cases that must be addressed: `service` on a directory domain, `guide` on a counselling provider with local pack present, AI Overview presence)
   - A dated note saying which date this mapping was approved (left blank pending user approval)
4. Does not merge this PR until the user approves or amends.

If code in `main` already consumes a mapping that has not been reviewed, the agent does not change behaviour — it just surfaces the existing mapping for review and notes any suggested changes.

## Acceptance criteria

- [ ] `intent_mapping.yml` exists as a separate, reviewable file.
- [ ] `docs/intent_mapping_rationale.md` exists and addresses each of the three v2 edge cases by name.
- [ ] The PR is held open pending user review (a comment on the PR confirms this).
- [ ] After user approval, the approval date is committed into the rationale doc.

---

# Fix 7 — Validation rule consistency check

## Problem

v2 Tool 1 Gap 5 required a test that fails when a new pre-computed field exists in `extracted_data` and is referenced in any prompt template, but has no corresponding rule in the validator. I cannot tell from the JSON output whether this test exists. The point of the test is to prevent silent regression — the LLM contradicting a pre-computed field while no validator catches it.

The new fields `serp_intent.primary_intent`, `serp_intent.is_mixed`, `serp_intent.confidence`, `title_patterns.dominant_pattern`, and `mixed_intent_strategy` all need validator rules per their respective v2 gap acceptance criteria.

## Required change

1. The agent confirms whether validator rules exist for each of the five fields above. If they do not, they are added.
2. The agent confirms whether the prompt-validator consistency test exists. If it does not, it is added per v2 Gap 5.
3. Each validator rule has an associated test that crafts a "bad" LLM output contradicting the pre-computed field and confirms the validator catches it.

## Severity classification (restated from v2)

- Contradicting `primary_intent`, `is_mixed`: HARD failure (no retry softening)
- Contradicting `dominant_pattern`: HARD failure
- Contradicting `mixed_intent_strategy`: SOFT failure (one retry permitted)
- Contradicting `confidence`: SOFT failure (LLM may downplay confidence; cannot upgrade it)

## Acceptance criteria

- [ ] Validator rules exist for all five fields with the severity classifications above.
- [ ] The consistency test (Gap 5) exists and passes.
- [ ] Five tests, one per field, each crafting a contradicting LLM output and asserting validator behaviour.
- [ ] A grep across `prompts/` for any of the five field names returns at least one hit per field — confirming the prompts actually use them.

---

# Fix 8 — README and documentation updates

## Problem

v2 Cross-cutting Documentation required README updates documenting the new fields, the handoff file, and the backwards-compatibility note about historical data. Cannot verify from the JSON output whether this happened.

## Required change

`serp/README.md` gains:

1. A new "What's new in this version" section listing each new field with a one-line description and an example value.
2. A new "Output files" section documenting all four files produced per run (`.json`, `.md`, `.xlsx`, `competitor_handoff_*.json`) with the contents of each.
3. A new "Backwards compatibility note" stating that runs prior to the v2 upgrade do not contain the new fields and the new fields are nullable on read.
4. A new "Tool 1 → Tool 2 handoff" subsection pointing to `docs/handoff_contract.md`.

## Acceptance criteria

- [ ] All four sections exist in `README.md`.
- [ ] The "What's new" section names every field touched in v2 Gaps 1, 2, 3, 4.
- [ ] A user reading only the README can run the pipeline and locate every output file.

---

# Cross-cutting requirement — Status report

The agent's final deliverable for this fix pass is an updated `docs/v2_dod_status_<date>.md` showing every Definition-of-Done item with a status of `done`, `not done`, or `not applicable to Tool 1` (Tool 2 work is out of scope for this pass).

The user does not accept the work as complete until this document is committed.

---

# Out of scope for this fix pass

- Tool 2 (`Serp-compete`) work — not part of this iteration.
- Centralising the schema repository.
- Replacing `ContentClassifier` with a different approach (Fix 5 is incremental, not a rewrite).
- Velocity / longitudinal tracking for the new fields.
- Multi-language support.

# Caveats the agent should not paper over

- If Fix 5's pattern rules don't materially improve classification rates, the agent reports this honestly rather than claiming success. The user prefers `confidence: low` reported accurately over `confidence: high` reported falsely.
- If the existing `intent_mapping.yml` (Fix 6) turns out to encode questionable decisions, the agent flags them in the rationale doc rather than silently fixing them.
- The user has stated a preference for accuracy over assumptions and for not being told work is done when it is partially done. The status report (mandatory first deliverable, and final deliverable) is the mechanism for honouring that preference.
