# serp

## Overview

A Market Intelligence Tool designed to support the "Bridge Strategy" for a non-profit counselling agency. It maps "Problem-Aware" queries to "Solution-Aware" content using SERP data.

## Installation

**Prerequisites:**

- Python 3.8+
- A valid SerpApi Key

1. Create a virtual environment:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Set your API Key:
   ```bash
   export SERPAPI_KEY="your_api_key_here"
   ```

## Running the Tool

To execute the full pipeline (Audit -> Validation -> Verification):

```bash
python run_pipeline.py
```

To launch the GUI with the pinned Python 3.12 interpreter:

```bash
./run_serp_launcher.sh
```

In the GUI, you can optionally enter one term in `Single Search Term` to override `keywords.csv` for that run.

CLI equivalent override:

```bash
SERP_SINGLE_KEYWORD="estrangement Vancouver" python serp_audit.py
```

## Content Opportunities Report

`List Content Opportunities` now generates a richer report using the latest
`market_analysis_v2.json` and writes:

```bash
content_opportunities_report.md
```

It uses the prompt spec in `serp_analysis_prompt_v3.md` with Anthropic and
loads client context from `config.yml` under `analysis_report`.

Required for launcher mode:

- `ANTHROPIC_API_KEY` env var
- `anthropic` Python package

If LLM access is unavailable, `List Content Opportunities` fails (no fallback).
If the LLM returns a report that contradicts the pre-verified extraction
facts, the script now fails evidence validation instead of writing the
report. When validation fails after retry, the script writes a companion
artifact next to the intended output, such as:

```bash
content_opportunities_report.validation.md
advisory_briefing.validation.md
```

These files list the rejected claims and include the rejected draft text.
You can bypass first-pass report validation only with:

```bash
python generate_content_brief.py --json market_analysis_v2.json --list --use-llm --allow-unverified-report
```

## Domain Override Review

The full pipeline now also generates:

```bash
domain_override_candidates.md
```

This report lists recurring domains that are not already in
`domain_overrides.yml` and may be worth adding after review. You can
also generate it directly with:

```bash
python generate_domain_override_candidates.py --json market_analysis_v2.json --overrides domain_overrides.yml --out domain_override_candidates.md
```

By default it suppresses low-confidence unclassified domains and focuses
on domains that are more likely to benefit from an override.

In the GUI, `6. Review Domain Override Candidates` now opens an in-app
checklist. High-confidence items are pre-checked, lower-confidence items
are left unchecked, and `Approve Checked` writes only the selected domains
into `domain_overrides.yml`. You can also choose the category for the
selected domain before approval. The current entity categories are:
`counselling`, `legal`, `directory`, `nonprofit`, `government`,
`media`, `professional_association`, and `education`.

When `Run Full Pipeline` finishes successfully in the GUI, the app now
auto-opens this review window if candidates exist. After you approve
checked domains, the app refreshes the current JSON/XLSX analysis files
locally so `List Content Opportunities` uses the updated entity labels
without requiring another SERP fetch.

CLI equivalent:

```bash
python apply_domain_override_candidates.py --json market_analysis_v2.json --overrides domain_overrides.yml
python refresh_analysis_outputs.py --json market_analysis_v2.json --xlsx market_analysis_v2.xlsx --overrides domain_overrides.yml
```

## Utilities

**Visualize Volatility:** Plot rank history for a keyword.

```bash
python visualize_volatility.py --list
python visualize_volatility.py --keyword "Free counselling North Vancouver"
```

**Export History:** Dump SQLite database to CSVs.

```bash
python export_history.py
```

## Testing

To run the regression tests:

```bash
python -m unittest test_enrichment.py
python -m unittest test_serp_audit.py
python -m unittest test_generate_content_brief.py
python -m unittest test_generate_domain_override_candidates.py
python -m unittest test_apply_domain_override_candidates.py
python -m unittest test_refresh_analysis_outputs.py
```
