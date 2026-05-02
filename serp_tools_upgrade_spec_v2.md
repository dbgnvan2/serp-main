# Upgrade Specification: `Serp-Discover` and `Serp-Compete` (v2)

## Status of this document

This is a coding-agent brief, not a marketing document. It assumes the agent has read access to both repositories and will be making changes against the current `main` branches. Cite this filename in commit messages so the work is traceable back to the spec.

The agent should treat the **Acceptance criteria** subsections as binding. The **Implementation notes** are guidance, not orders — the agent may pick a better implementation path if one exists, provided the acceptance criteria are met and the design principles below are honoured.

**Version note:** This is v2. v1 had material omissions around validation, failure modes, backwards compatibility, and definition-of-done. v2 closes those.

## Reading the existing system before changing it

Before writing any code, the agent must read at minimum:

- `serp/README.md`
- `serp/run_pipeline.py`
- `serp/serp_audit.py` (the parsing / extraction stages, `parse_data()` in particular)
- `serp/classifiers.py`
- `serp/intent_classifier.py`
- `serp/generate_content_brief.py` (especially `extract_analysis_data_from_json()`, `_compute_strategic_flags()`, `validate_extraction()`, and the validation/correction retry loop)
- `serp/prompts/main_report/system.md`
- `serp/prompts/main_report/user_template.md`
- `serp/prompts/advisory/system.md`
- `serp/prompts/correction/user_template.md`
- `serp-main/Serp-compete/spec.md`
- `serp-main/Serp-compete/GEMINI.md`
- `serp-main/Serp-compete/src/main.py`
- `serp-main/Serp-compete/src/semantic.py`
- `serp-main/Serp-compete/src/scoring_logic.py`
- `serp-main/Serp-compete/src/reframe_engine.py`
- `serp-main/Serp-compete/src/database.py`
- `serp-main/Serp-compete/src/velocity_module.py`
- `serp-main/shared_config.json`
- `serp-main/clinical_dictionary.json`

The agent must not duplicate functionality that already exists. If a feature listed below appears to be partially implemented, the work is to extend, not replace.

## Design principles

These constrain every change in this spec.

1. **Determinism in Python, semantics in the LLM.** Anything that is a count, a presence flag, a label derivable from rules, a structural extraction, or a classification with a fixed taxonomy is computed in Python and stored in the JSON payload. Anything that requires reading prose for meaning, framing, or inference is delegated to the LLM. The existing `serp` system prompt already enforces this boundary; new work must not blur it.
2. **No silent estimation.** If a value cannot be computed from observed data, the field is `null` and the absence is stated explicitly downstream. The LLM must never be allowed to fill a `null` with a guess.
3. **Schema additions are additive.** Existing JSON keys keep their meanings. New keys are added alongside. Downstream consumers (`generate_content_brief.py`, `generate_insight_report.py`, prompt templates, validation rules) are updated in the same change set so nothing breaks.
4. **Validation rules track the schema.** Every new pre-computed field that the LLM is allowed to reference must have a corresponding rule in `validate_extraction()` (or whatever validator applies) that catches the LLM contradicting it. Adding a field without adding a validation rule is incomplete work.
5. **Tests required for every new module.** Each new deterministic function gets a unit test in the existing test pattern (`test_*.py` for `serp`, `tests/` for `Serp-compete`). LLM-facing changes get at least a smoke test that validates output shape, not content.
6. **Configuration-driven, no hard-coded clinical or competitive vocabulary.** Both repos already enforce this. New trigger lists, weight tables, and thresholds go in `shared_config.json` (serp-main) or `config.yml` / a new YAML asset (serp). No new strings hard-coded into `.py` files.
7. **Graceful degradation.** When an external dependency fails (a scrape is blocked, an API returns 429, a JSON-LD block is malformed), the affected sub-signal becomes `null` and the rest of the pipeline continues. Hard-fail only when a foundational dependency is missing (the entire SERP fetch fails, credentials are absent).

## Definition of done

The upgrade is complete when ALL of the following are true:

1. Every gap section's acceptance criteria are met.
2. `pytest` passes in both repos with the new tests included.
3. An end-to-end run of each tool against a fixture dataset produces JSON output that includes every new field with a non-error value (where applicable) or an explicit `null` (where the data didn't support computing the field).
4. The validation/correction loop in Tool 1 covers every new pre-computed field — i.e., a hand-crafted "bad" LLM output that contradicts a new field is caught by the validator, not by visual inspection.
5. The advisory briefing produced by Tool 1 uses (or correctly chooses not to use) the new `mixed_intent_strategy` field on at least one keyword in the fixture run.
6. The strategic briefing produced by Tool 2 contains both Section A (deterministic audit summary) and Section B (LLM reframes) per the spec.
7. README files in both repos document the new fields and the handoff contract.
8. No previously-passing test now fails. No existing JSON schema field has changed meaning.

## Backwards compatibility and migration

Both tools maintain SQLite databases (`serp_data.db` in Tool 1, `living_systems_intel.db` in Tool 2). When new fields are added:

- The agent does NOT need to retrofit historical data to populate the new fields.
- New columns/tables required by the work are added via additive migrations (new columns get sensible defaults; old rows are not retroactively populated).
- Any code that queries the database for new fields must handle the case where historical rows have `NULL` for those fields.
- Tool 2's `velocity_module.py` longitudinal tracking continues to work against the old schema; new velocity dimensions (e.g., EEAT score drift over time, if added later) are out of scope for this iteration.
- A short note in each repo's README states: "As of [date of upgrade], historical data does not contain [list of new fields]. New runs populate them; old runs do not."

---

# Tool 1 — `Serp-Discover` (`dbgnvan2/serp-discover`)

## Current state, as of the spec date

Tool 1 already implements substantially more SERP analysis than a naive reading of the code suggests. The pipeline pre-computes, per keyword:

- Total indexed results
- SERP module presence (`serp_modules`, `has_ai_overview`, `has_local_pack`)
- Entity distribution and `entity_label` (`dominated_by_X`, `X_plurality`, `mixed_X_Y`, `unclassified`)
- Content type counts (`guide`, `service`, `directory`, `news`, `pdf`, `other`) per `ContentClassifier`
- Per-URL author/domain entity classification per `EntityClassifier`
- People Also Ask, autocomplete, related searches
- AI Overview text and citations
- Client position with stability classification (`new`, `stable`, `improving`, `declining`)
- `strategic_flags` with per-keyword action (`defend / strengthen / enter / enter_cautiously / skip`)
- PAA intent tagging into `External Locus / Systemic / General`

The LLM is constrained by an explicit evidence-rules system prompt and is forbidden from inventing counts, cross-cutting claims, or stability labels. There is also a validation/correction retry loop that catches the LLM contradicting pre-computed values. The architecture is sound. What follows is a list of specific gaps, not a redesign.

## Gap 1 — SERP intent verdict is implicit, not explicit

### Problem

The pipeline computes the inputs for an intent verdict (entity mix, content type mix, SERP modules, PAA presence) but does not produce a single per-keyword field that says "this SERP has informational intent" or "this SERP is mixed-intent." The LLM is left to infer this from `entity_label` + `content_type_breakdown` + `serp_modules`. This works most of the time but is not auditable and is the kind of synthesis the design principle assigns to deterministic Python.

### Required change

Add a `serp_intent` block to each entry in `keyword_profiles`. Schema:

```json
"serp_intent": {
  "primary_intent": "informational" | "commercial_investigation" | "transactional" | "navigational" | "local" | "mixed" | null,
  "intent_distribution": {
    "informational": <int>,
    "commercial_investigation": <int>,
    "transactional": <int>,
    "navigational": <int>,
    "local": <int>
  },
  "is_mixed": <bool>,
  "mixed_components": [<intent_label>, ...],
  "confidence": "high" | "medium" | "low",
  "evidence": {
    "content_types_seen": {<content_type>: <count>, ...},
    "entity_types_seen": {<entity_type>: <count>, ...},
    "serp_features_present": [<feature>, ...],
    "classified_url_count": <int>,
    "total_url_count": <int>
  }
}
```

`primary_intent` is `null` when fewer than 5 of the top 10 URLs could be classified. `confidence` is:
- `high` if classified_url_count ≥ 8 of 10
- `medium` if 5–7 of 10
- `low` if < 5 — and `primary_intent` is `null` in this case

### Implementation notes — first deliverable: the mapping draft

The intent-mapping table is editorial. Rather than implementing the agent's first guess, the **first deliverable for this gap is a draft `intent_mapping.yml` plus a written rationale committed as a separate PR for review**. The user (Dave) approves or amends the mapping before any code that consumes it is merged.

Starting point for the draft (the agent should refine):

| Content_Type | Entity_Type | Local pack present | → Intent |
|---|---|---|---|
| service | counselling / legal | yes | local |
| service | counselling / legal | no | transactional |
| service | client's own domain | any | navigational |
| service | known competitor brand | any | navigational |
| service | other | any | transactional |
| guide | any | any | informational |
| directory | any | any | commercial_investigation |
| news | any | any | informational |
| pdf | any | any | informational |
| other | any | any | uncategorised (not counted) |

Decision rules for `primary_intent`:

- A bucket holding ≥60% of classified URLs in the top 10 → that bucket wins.
- No bucket ≥60% but one ≥40% with a clear lead (≥2 URLs over the next bucket) → that bucket wins.
- Otherwise → `primary_intent = "mixed"`, populate `mixed_components` with all buckets holding ≥2 URLs.

`is_mixed` is `True` iff `primary_intent == "mixed"`.

Edge cases the mapping table must address (the agent calls these out explicitly in the rationale doc):
- A `service` page on a directory domain (e.g. Psychology Today profile) — should this be `commercial_investigation` (because directory) or `transactional` (because service)? The mapping table chooses one and explains why.
- A `guide` URL on a counselling provider's domain when the keyword has a local pack — does locality override informational? The mapping table chooses.
- AI Overview presence does NOT shift intent. AI Overviews appear on all intent types now and are not a reliable intent signal.

### Validation rules to add

Update `validate_extraction()` to enforce:
- LLM output must not state a `primary_intent` value different from `serp_intent.primary_intent` for any keyword.
- LLM output must not call a SERP "mixed" if `serp_intent.is_mixed` is `False`, and vice versa.
- These are HARD failures (no retry softening).

### Acceptance criteria

- [ ] `intent_mapping.yml` draft submitted as separate PR with rationale doc; user-approved before code merges.
- [ ] `keyword_profiles[<kw>]["serp_intent"]` is populated for every keyword for which top-10 organic results were collected.
- [ ] `intent_mapping.yml` is loaded at startup; no hard-coded mapping in `.py` files.
- [ ] Every value in `intent_distribution` is a non-negative integer derived from observed URL classifications. No value is estimated.
- [ ] `confidence` field present and correctly set per the rules above.
- [ ] Unit tests cover: pure-informational SERP, pure-transactional SERP, mixed SERP (the GetAccept case), local-pack-present SERP, an all-`unknown` SERP (yields `primary_intent: null`, `confidence: low`), and a SERP with exactly 5 of 10 classified (yields `confidence: medium`).
- [ ] The main report `system.md` is updated to reference `serp_intent.primary_intent`, `serp_intent.is_mixed`, and `serp_intent.confidence` in Section 2's per-keyword profile.
- [ ] Validation rules added to `validate_extraction()` per the section above.
- [ ] A test crafts a "bad" LLM output that contradicts a known `serp_intent` value and confirms the validator catches it.

## Gap 2 — Title pattern extraction across the top 10

### Problem

The transcript's "study the SERP" step includes reading the framing of the titles ("how to X", "X vs Y", "best X for Y", brand-name-only). The current pipeline stores titles per result but does not surface a title-pattern summary to the LLM.

### Required change

Add `title_patterns` to each `keyword_profile`:

```json
"title_patterns": {
  "how_to": <int>,
  "what_is": <int>,
  "best_of": <int>,
  "vs_comparison": <int>,
  "listicle_numeric": <int>,
  "brand_only": <int>,
  "question": <int>,
  "other": <int>,
  "dominant_pattern": "<pattern_name>" | null,
  "examples": {
    "<pattern_name>": ["<title 1>", "<title 2>"]
  }
}
```

### Implementation notes

Use a small set of regular expressions over the top 10 organic titles. The patterns:

- `how_to`: title starts with or contains `how to` (case-insensitive)
- `what_is`: title starts with `what is` / `what are`
- `best_of`: title contains `best ` followed by at least one alphabetic word (allow optional adjectives)
- `vs_comparison`: title contains ` vs `, ` vs. `, or ` versus ` (case-insensitive, surrounded by word boundaries)
- `listicle_numeric`: title starts with a digit followed by whitespace and an alphabetic word
- `brand_only`: title length ≤ 6 words AND ≥ 60% of words match a known brand name (from the brand list)
- `question`: title ends with `?`
- `other`: anything that matched no pattern above

Patterns are checked in priority order: `vs_comparison` > `how_to` > `what_is` > `listicle_numeric` > `best_of` > `question` > `brand_only` > `other`. A title that matches multiple patterns is counted once, in the highest-priority bucket.

`dominant_pattern` is set when one pattern accounts for ≥4 of the top 10. Otherwise `null`.

Brand list construction: the union of (a) known competitor domains from `domain_overrides.yml` reduced to brand-name forms (e.g. `psychologytoday.com` → `psychology today`), (b) the client's brand name from `config.yml`, (c) any explicit additions in a new `known_brands` config block.

### Failure handling

If the title list is empty (no organic results captured), `title_patterns` is set to `null` (not an empty struct). Downstream code must handle `null`.

### Acceptance criteria

- [ ] `title_patterns` populated for every keyword profile that has ≥1 organic result; `null` otherwise.
- [ ] Pattern detection is case-insensitive and handles punctuation variants (em-dashes, smart quotes).
- [ ] Priority ordering applied — a unit test verifies that "How To Compare X vs Y" counts as `vs_comparison`, not `how_to`.
- [ ] Unit tests cover each pattern with positive and negative examples.
- [ ] `dominant_pattern` is `null` (not the string `"none"`) when no pattern reaches the threshold.
- [ ] System prompt mentions `title_patterns.dominant_pattern` in Section 2 as one signal supporting the SERP intent description.
- [ ] Validator catches the LLM contradicting a non-null `dominant_pattern`.

## Gap 3 — Handoff to Tool 2

### Problem

The current `get_latest_market_data()` in Tool 2 reads a JSON file from `serp-keyword/output/` with no validated schema. Tool 1 needs to produce a stable, validated handoff file.

### Decision: separate handoff file

Tool 1 produces a separate `competitor_handoff_<topic>_<timestamp>.json` file alongside its main output. Rationale: the handoff contract should be explicit and versionable, and should not be tied to the shape of `keyword_profiles` (which is geared toward report generation and may evolve independently). Keeping handoff small also simplifies debugging.

### Required change

Tool 1 writes `competitor_handoff_*.json` conforming to a JSON Schema (`handoff_schema.json`, draft-07) at the repo root.

Top-level shape:

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
      "source_keyword": "<keyword>",
      "primary_keyword_for_url": "<keyword>"
    }
  ],
  "exclusions": {
    "client_urls_excluded": <int>,
    "omit_list_excluded": <int>,
    "omit_list_used": ["<domain>", ...]
  }
}
```

The `targets` array includes the top N organic URLs per keyword (default N=10, configurable in `config.yml`) excluding any URL on the client's own domain and any URL whose domain is in an `omit_from_audit` list (configurable, defaulting to `[]`).

### Acceptance criteria

- [ ] `handoff_schema.json` exists at the repo root of `serp` AND a copy at the repo root of `serp-main` (manual sync; out-of-scope to centralise).
- [ ] Tool 1 produces `competitor_handoff_*.json` on every full pipeline run.
- [ ] Tool 1's output validates against the schema before being written. Validation failure aborts the write and logs the schema violation.
- [ ] Omit list and N are configurable; defaults documented in `config.yml`.
- [ ] Client URLs and omitted-domain URLs are not included in `targets` but are counted in `exclusions`.
- [ ] A new section in `serp/README.md` documents the handoff file location and naming convention.

## Gap 4 — Mixed-intent advisory framing

### Problem

When a SERP is mixed-intent, the GetAccept-style "backdoor" play described in the transcript is the right strategic move, but the current advisory prompt does not surface mixed-intent as a distinct strategic situation. It funnels everything into `defend / strengthen / enter / enter_cautiously / skip`.

### Required change

In `_compute_strategic_flags()`, add a `mixed_intent_strategy` field to each entry of `opportunity_scale` when the keyword's `serp_intent.is_mixed` is `True`. Possible values:

- `"compete_on_dominant"` — client framework can plausibly produce content matching the most-represented intent
- `"backdoor"` — client should produce content matching a lesser-represented but client-aligned intent (the GetAccept play)
- `"avoid"` — none of the represented intents fit the client's capabilities
- `null` — keyword is not mixed-intent (field is omitted or null)

The decision is rules-based:

- If the dominant intent matches the client's content-asset history (drawn from `client_position.organic` content types) → `compete_on_dominant`.
- Else if any non-dominant component intent matches a preferred content type from `config.yml` (`client.preferred_content_types`) → `backdoor`.
- Else → `avoid`.

Update both `prompts/main_report/system.md` (Section 7) and `prompts/advisory/system.md` (Action 2 / Action 3 framing) to allow the LLM to reference `mixed_intent_strategy` when it is non-null.

### Validation rules to add

- LLM output for a mixed-intent keyword must not contradict the chosen `mixed_intent_strategy` (e.g. cannot recommend a "backdoor" approach when the field is `compete_on_dominant`). Treat as a SOFT failure (one retry permitted).
- LLM output for a non-mixed keyword must not invoke `mixed_intent_strategy` language at all.

### Acceptance criteria

- [ ] Field populated only for mixed-intent keywords; non-mixed keywords get `null` or omit the field consistently.
- [ ] `client.preferred_content_types` list exists in `config.yml`.
- [ ] Both system prompts (main report and advisory) updated.
- [ ] Validation rules added.
- [ ] Unit test covers each of the three values + the null/non-mixed case.

## Gap 5 — Validation rule consistency check

### Problem

Tool 1's validator (`validate_extraction()` and the correction retry loop) is the firewall that prevents the LLM from contradicting pre-computed data. Adding new pre-computed fields without updating the validator means the LLM can silently contradict them. This is a correctness regression.

### Required change

Add a programmatic check that runs at startup (or in tests) and fails if there is a pre-computed field in `extracted_data` that is referenced in any prompt (system or user template) but has no corresponding rule in the validator. The check is heuristic — it matches field names mentioned in the prompts against rules registered in the validator — but is good enough to catch the common mistake.

This check is itself part of the test suite, not production code.

### Acceptance criteria

- [ ] Test exists that scans prompt files for field references and confirms each is covered by a validator rule.
- [ ] Test fails when a new pre-computed field is added without a matching validator rule.
- [ ] Test passes after Gaps 1, 2, and 4 add their validator rules.

---

# Tool 2 — `Serp-Compete` (`dbgnvan2/serp-compete`)

## Current state

Tool 2 ingests competitor targets, pulls each domain's ranked-keyword profile via DataForSEO, scrapes the top pages of each competitor, and scores them on a tier-1/2/3 dictionary that distinguishes medical-model vocabulary from Bowen-systems vocabulary. The output is a strategic briefing with LLM-generated reframe blueprints. It also tracks longitudinal data via `velocity_module.py` and has circuit-breaker logic for HTTP 429s.

The existing scoring is doing one specific job: detecting framing (medical vs systems) in competitor content. It is not extracting the broader competitive content structure that the transcript identifies as decisive — page outline, EEAT signals, internal linking, content depth.

## Gap 1 — Competitor handoff from Tool 1

### Problem

The current `get_latest_market_data()` reads a JSON file from `serp-keyword/output/` with no validated schema. The contract is fragile.

### Required change

Tool 2 reads `competitor_handoff_*.json` files (produced by Tool 1 per Tool 1 Gap 3) and validates them against `handoff_schema.json`.

Update `get_latest_market_data()` to:

- Look for `competitor_handoff_*.json` files first (configurable path).
- Validate the loaded JSON against the schema using `jsonschema`.
- Hard-fail with a clear error message if validation fails. Do NOT fall back to `manual_targets.json` silently.
- Fall back to `manual_targets.json` only when no handoff file exists at all (this remains the developer override path; document as such).
- Continue to support the legacy `market_analysis_*.json` format for at least one release cycle, with a deprecation warning. Remove in the next iteration.

### Acceptance criteria

- [ ] `handoff_schema.json` present at repo root.
- [ ] Schema validation runs on every load; failures are logged and abort the run.
- [ ] Legacy format still loads, with a `DeprecationWarning`.
- [ ] `manual_targets.json` fallback only triggers when no handoff or legacy file exists.
- [ ] Unit test covers: valid handoff, schema-invalid handoff (hard fail), missing handoff (manual fallback), and legacy format (warning path).

## Gap 2 — Preserve and extract page structure during scrape

### Problem

`semantic.py::scrape_content()` extracts H1/H2/H3 headers AND the first 500 words, then concatenates them into a single string. This destroys structure. The vocabulary scorer doesn't need structure, but a content audit does.

### Required change

Replace the current `scrape_content()` return type with a dataclass:

```python
@dataclass
class ScrapedPage:
    url: str
    fetched_at: str  # ISO 8601
    http_status: int
    extraction_status: Literal["complete", "partial", "blocked", "error"]
    extraction_errors: list[str]
    outline: list[dict]  # [{"level": "h1"|"h2"|"h3", "text": str, "order": int}]
    first_500_words: str
    full_text_word_count: int
    metadata: dict  # see below
```

Metadata sub-dict:

```python
{
    "title": str | None,
    "meta_description": str | None,
    "author_byline": str | None,
    "publish_date": str | None,        # ISO date
    "update_date": str | None,
    "schema_types": list[str],         # JSON-LD @type values found
    "has_faq_schema": bool,
    "has_article_schema": bool,
    "has_localbusiness_schema": bool,
    "image_count": int,
    "image_hosts": list[str],          # unique hostnames of <img src> values
    "external_link_count": int,
    "internal_link_count": int,
    "internal_links": list[str],       # raw URLs, used by Gap 4
    "is_https": bool,
    "has_contact_link": bool,
    "has_privacy_link": bool
}
```

`extraction_status` semantics:
- `complete` — page fetched, fully parsed, all metadata extracted without error
- `partial` — page fetched but some metadata blocks (e.g. JSON-LD) failed to parse; structural data still usable
- `blocked` — HTTP 429 / 403 / bot-detection page
- `error` — network or parser failure; do not use the result

Existing tier-1/2/3 scoring continues to operate on `first_500_words` for backwards compatibility.

### Implementation notes

- Use BeautifulSoup's existing parse, just extract more from it.
- For author byline, check (in order): `<meta name="author">`, `<meta property="article:author">`, JSON-LD `author.name`, then HTML patterns (`.author`, `.byline`, `[rel="author"]`). Return `None` if no signal.
- For dates, prefer JSON-LD `datePublished` / `dateModified`, then `<meta property="article:published_time">`, then `<time>` elements with `datetime` attributes.
- Schema types: parse all `<script type="application/ld+json">` blocks, walk the JSON, collect every `@type` encountered. Wrap each parse in try/except; catch `json.JSONDecodeError` and append the URL + error to `extraction_errors`, but continue.
- Word count is computed on visible body text (drop `<nav>`, `<footer>`, `<script>`, `<style>`, `<aside>`).
- Internal vs external links: a link is internal if its host matches the page's host or is empty (relative). Strip URL fragments and tracking params before deduplication.
- `has_contact_link` / `has_privacy_link`: detect anchor text or `href` containing `contact`, `privacy`, etc. (case-insensitive).

### Acceptance criteria

- [ ] New return shape implemented as a `@dataclass`.
- [ ] Vocabulary scoring continues to work — regression test against existing scoring fixtures passes unchanged.
- [ ] Outline preserves source order and level.
- [ ] All metadata fields gracefully return `None` / `0` / `[]` when the source page provides no signal — never raise.
- [ ] `extraction_status` correctly distinguishes the four cases. Test fixtures cover each.
- [ ] Existing 429 circuit-breaker logic continues to work and now sets `extraction_status="blocked"`.
- [ ] Unit tests using locally-stored HTML fixtures cover: full-schema page, no-schema page, FAQ schema, no-byline page, internal-only links, malformed JSON-LD (yields `partial`).

## Gap 3 — EEAT heuristic scoring

### Problem

The transcript identifies EEAT — particularly the "Experience" leg — as the most heavily weighted dimension Google uses. This claim is from the SEO industry and is not a documented Google statement. The agent should not propagate it as fact, only as the SEO-industry view that motivates the score.

The current Tool 2 has no EEAT scoring of any kind.

### Required change

Add `src/eeat_scorer.py`. Compute a per-page EEAT signal record from the structure extracted in Gap 2:

```json
{
  "url": str,
  "scored_at": <ISO 8601>,
  "experience_signals": {
    "has_author_byline": bool,
    "has_publish_date": bool,
    "has_update_date": bool,
    "has_likely_original_images": bool,
    "first_person_count": int,
    "case_study_signal": bool
  },
  "expertise_signals": {
    "has_credentials_in_byline": bool,
    "matched_credentials": [<str>, ...],
    "schema_author_type": "Person" | "Organization" | null,
    "tier_3_count": int,
    "tier_2_count": int
  },
  "authoritativeness_signals": {
    "domain_authority": int | null,
    "external_link_count": int,
    "schema_organization_present": bool
  },
  "trustworthiness_signals": {
    "is_https": bool,
    "has_contact_link": bool,
    "has_privacy_link": bool
  },
  "scores": {
    "experience": float | null,
    "expertise": float | null,
    "authoritativeness": float | null,
    "trustworthiness": float | null
  },
  "score_confidence": "high" | "medium" | "low",
  "caveat": "Heuristic proxy. Not Google's actual EEAT model."
}
```

Each sub-score is a weighted average of its block's signals, normalised to 0.0–1.0. A sub-score is `null` if fewer than half its underlying signals could be evaluated. `score_confidence` is `low` if any score is `null`, `high` if all four scores were computed from full signal sets, otherwise `medium`.

### Default weights (in `shared_config.json`)

```json
"eeat_weights": {
  "experience": {
    "has_author_byline": 0.15,
    "has_publish_date": 0.10,
    "has_update_date": 0.10,
    "has_likely_original_images": 0.20,
    "first_person_count_normalised": 0.20,
    "case_study_signal": 0.25
  },
  "expertise": {
    "has_credentials_in_byline": 0.40,
    "schema_author_type_person": 0.20,
    "tier_3_or_tier_2_present": 0.40
  },
  "authoritativeness": {
    "domain_authority_normalised": 0.50,
    "external_link_count_normalised": 0.20,
    "schema_organization_present": 0.30
  },
  "trustworthiness": {
    "is_https": 0.40,
    "has_contact_link": 0.30,
    "has_privacy_link": 0.30
  }
}
```

Normalisation rules:
- `first_person_count_normalised`: `min(count / 10, 1.0)` — caps at 10 first-person mentions.
- `domain_authority_normalised`: `min(da / 60, 1.0)` — DA 60+ scores 1.0.
- `external_link_count_normalised`: `min(count / 5, 1.0)` — 5+ outbound links scores 1.0.

### Implementation notes

- The agent must explicitly document in the module docstring that these are heuristic proxies, not Google's actual EEAT model. The heuristic-nature caveat must appear in the strategic briefing output.
- "Original images" heuristic: pull image hosts from `<img src>`. If ≥80% of image hosts are in the configurable `stock_image_hosts` list, set `has_likely_original_images = False`. Otherwise `True`. If `image_count` is 0, set to `False`.
- Default `stock_image_hosts`: `shutterstock.com`, `gettyimages.com`, `istockphoto.com`, `unsplash.com`, `pexels.com`, `pixabay.com`, `stock.adobe.com`. Configurable.
- "Credentials in byline": match against a configurable list (`MD`, `PhD`, `MA`, `MSW`, `RCC`, `LCSW`, `RP`, `RSW`, etc.) word-bounded.
- "Case study signal": page contains any of: "we tested", "case study", "in our experience", "our research", "we conducted", "our findings". Configurable trigger list.
- First-person count: count word-bounded occurrences of `I`, `we`, `our`, `us` in body text (case-insensitive). Exclude `I` inside contractions like "I'd" only if simpler regex causes false positives — agent's call.

### Failure handling

If `ScrapedPage.extraction_status` is `blocked` or `error`, `eeat_scorer` returns a record with all signals `False`/`null` and `score_confidence: "low"`. It does NOT raise.

### Acceptance criteria

- [ ] Module exists with docstring stating the heuristic caveat.
- [ ] Unit tests cover: full-signal page (high confidence), partial-signal page (medium), blocked page (low, all-null scores).
- [ ] Integrates into the audit loop in `main.py` after page scraping.
- [ ] Output is saved per audited URL and is part of the strategic briefing input to the LLM.
- [ ] Reframe engine prompt is updated to receive the per-competitor EEAT record (the underlying signals, not just scores) and to reference at least one specific signal in the generated reframe.
- [ ] Heuristic caveat appears in the strategic briefing output for any section that references EEAT scores.

## Gap 4 — Internal linking detection

### Problem

The transcript's section on topical authority makes the case that internal linking from supporting content to money pages is decisive. Tool 2 does not detect linking patterns within competitor sites.

### Required change

Add `src/cluster_detector.py`. For each competitor domain audited:

1. Collect internal links from each scraped page (extracted in Gap 2).
2. Build a directed graph: nodes are URLs on this domain that were scraped, edges are internal links between them.
3. Compute in-degree and out-degree for each scraped node.
4. Identify hub candidates — pages with in-degree above the configurable threshold.

Output schema, per competitor domain:

```json
{
  "domain": str,
  "pages_analyzed": int,
  "internal_link_graph": {
    "<url>": {
      "out_links_to_domain": [<url>, ...],
      "in_links_from_domain": [<url>, ...],
      "in_degree": int,
      "out_degree": int
    }
  },
  "hub_candidates": [<url>, ...],
  "cluster_signal": "isolated" | "linked" | "clustered" | "insufficient_data",
  "resolution_caveat": "Based on N=<int> scraped pages. Low resolution."
}
```

### Cluster signal rules (configurable thresholds, defaults shown)

- `insufficient_data` — fewer than 3 pages scraped on this domain (hub_in_degree threshold cannot be reliably evaluated)
- `isolated` — no scraped page links to any other scraped page on this domain
- `linked` — at least one inter-page link exists, but no page has in-degree ≥ `hub_in_degree_threshold` (default: 2)
- `clustered` — at least one page has in-degree ≥ `hub_in_degree_threshold`

Configuration block in `shared_config.json`:

```json
"cluster_thresholds": {
  "hub_in_degree_threshold": 2,
  "min_pages_for_signal": 3
}
```

### Honest framing — this is a low-resolution signal

The agent must include in both the module docstring and the strategic briefing the following:

> Cluster detection runs only on the pages this audit scraped (typically 3 per competitor). It cannot see the wider site structure. A domain marked `isolated` may still have a strong internal-link cluster invisible to this audit. Treat the signal as suggestive, not decisive.

A full internal-linking audit would require either crawling the domain or using a third-party API (Ahrefs, Moz site explorer). Both are out of scope for this iteration.

### Acceptance criteria

- [ ] Module exists with low-resolution caveat in the docstring.
- [ ] Integrates into `main.py` after the per-domain audit loop.
- [ ] `cluster_signal` correctly handles all four cases including `insufficient_data`.
- [ ] Threshold is configurable; default documented.
- [ ] Cluster signal is included in the per-competitor section of the strategic briefing with the caveat verbatim.
- [ ] LLM prompt instructs the model to weight competitors with `cluster_signal: clustered` more heavily when assessing competitive threat — but to also acknowledge the low-resolution caveat.
- [ ] Unit tests cover: 3 pages with no inter-links (`isolated`), 3 pages with one link (`linked`), 3 pages forming a hub (`clustered`), 2 pages (`insufficient_data`).

## Gap 5 — Strategic briefing structure update

### Problem

The current strategic briefing is dominated by Bowen reframe blueprints. It does not present a structured competitor-by-competitor audit summary that incorporates the new EEAT, structure, and clustering data.

### Required change

The briefing now contains two distinct sections:

**Section A: Per-competitor audit summary.** For each competitor domain audited, a structured block:

- Domain, average page authority (or "N/A — Moz unavailable"), ranked keywords count
- Cluster signal (`isolated` / `linked` / `clustered` / `insufficient_data`) with the resolution caveat
- Hub URLs if any
- Per-page rows with: URL, rank, content_type, EEAT scores (or "low confidence" badge), page-structure summary (word count, image count, has FAQ schema, has author byline with credentials), tier-1 / tier-2 / tier-3 vocabulary counts, scrape `extraction_status`
- One-line LLM-generated commentary per page summarising the strategic threat (this is the only LLM call in Section A)

**Section B: Bowen reframe blueprints.** The existing reframe content, but anchored to audit findings: the LLM's reframe must reference at least one specific structural or EEAT signal from the audited competitor it is reframing against.

### Required heuristic caveats in the output

- EEAT caveat (verbatim): "EEAT scores are heuristic proxies based on page-level signals. They are not Google's actual EEAT model and should be read as competitive structural signals, not authoritative SEO measurements."
- Cluster caveat (verbatim): "Cluster signals are derived from a 3-page sample of each competitor's site. They are suggestive of internal-linking patterns but cannot be conclusive."

Both appear as a "Methodology notes" block at the end of Section A.

### Acceptance criteria

- [ ] Strategic briefing produces both sections in every run.
- [ ] Section A is generated deterministically from the audit data — only LLM call in Section A is the one-line per-page commentary.
- [ ] Section B's reframe prompts are updated to require an explicit audit-finding reference; if the LLM produces a reframe with no specific signal reference, the validation soft-fails and retries once.
- [ ] Both heuristic caveats appear verbatim in every briefing.
- [ ] An example briefing committed to the repo (`docs/example_strategic_briefing.md`) shows the new structure.
- [ ] Existing briefings (`strategic_briefing_run_*.md`) are not modified — they remain as historical artifacts.

---

# Cross-cutting work

## Tests

- Tool 1: every new function in intent classification, title pattern detection, and strategic flag computation gets unit tests in the existing `test_*.py` pattern.
- Tool 2: every new module gets a corresponding `tests/test_*.py` file using `pytest`.
- A new integration test in each repo runs the pipeline end-to-end against a small fixture dataset and asserts the new fields exist with expected types.
- Tool 1 has a new test that scans prompt files for pre-computed-field references and confirms each has a validator rule (Tool 1 Gap 5).

## Documentation

- Tool 1: update `README.md` to describe the new `serp_intent`, `title_patterns`, `mixed_intent_strategy` fields, the handoff file, and the backwards-compatibility note about historical data.
- Tool 2: update `Serp-compete/spec.md` with the new modules. Update `GEMINI.md` with the expanded scope. Document the EEAT and cluster heuristic caveats prominently. Add the backwards-compatibility note.

## Configuration consolidation

- Tool 1: add to `config.yml`:
  - `serp_intent.thresholds` (60% / 40%/2 lead margin / mixed)
  - `audit_targets.n` (default 10), `audit_targets.omit_from_audit` (default empty list)
  - `client.preferred_content_types` (list)
  - `known_brands` (list, augments domain-overrides-derived brands)
- Tool 2: add to `shared_config.json`:
  - `eeat_weights` (default block above)
  - `stock_image_hosts` (default list above)
  - `credential_list` (default list of suffixes/abbreviations)
  - `case_study_triggers` (default list)
  - `cluster_thresholds.hub_in_degree_threshold` (default 2), `cluster_thresholds.min_pages_for_signal` (default 3)

## Cost / API budget

- The new work in Tool 2 increases token consumption per LLM call (richer audit context in reframe prompts, plus per-page commentary lines in Section A). Estimate before merging: a typical run with 5 competitors × 3 pages = 15 commentary calls + 5 reframe calls. The agent must measure the actual token usage on the fixture dataset and report the cost delta in the PR description.
- Tool 1's existing API tier modes (`Low` / `Balanced` / `Deep Research`) are unchanged. The new SERP intent computation is local-only and adds no external API calls.
- Tool 2 adds no external API calls beyond what already exists.

## Out of scope

The following came up during analysis but are explicitly not part of this iteration:

- Centralised schema repository for the handoff format (currently duplicated across both repos by manual sync).
- Full domain-level internal linking audit (requires crawling or third-party APIs).
- Replacing the deterministic `EntityClassifier` and `ContentClassifier` with ML models.
- Automated ingestion of the strategic briefing back into Tool 1's prioritisation (closing the loop).
- Multi-language support — both tools assume English.
- Migrating historical SQLite rows to populate new fields.
- Velocity tracking for new EEAT signals over time.

## Caveats the agent should not paper over

- The transcript's claim that "Experience is the most heavily weighted EEAT factor" is an SEO industry assertion, not a documented Google statement. The EEAT scorer operationalises a heuristic, not a Google-internal model.
- The cluster detector's resolution is bounded by how many pages Tool 2 actually scrapes per domain. Three-page samples produce signal but not certainty.
- Title pattern regex is brittle by design — the agent should not over-engineer it. False negatives are acceptable; false positives are not. When in doubt, classify as `other`.
- The intent mapping table is editorial. The agent submits a draft for user review before any code consumes it (Tool 1 Gap 1).
- Backwards compatibility is preserved at the schema level (new fields added, old fields unchanged) and the database level (no retroactive backfill). Old runs will have nulls where new data lives.
