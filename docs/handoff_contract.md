# Competitor Handoff Contract

**File:** `competitor_handoff_<topic>_<timestamp>.json`  
**Schema:** `handoff_schema.json` (JSON Schema draft-07)  
**Version:** 1.0

This document describes the contract between Tool 1 (`serp-discover`) and Tool 2 (`serp-compete`). The handoff file is the stable, validated interface between the two tools.

---

## Purpose

Tool 1 audits SERPs and identifies which competitor URLs rank for each keyword. Tool 2 audits those competitor pages in depth (vocabulary analysis, EEAT scoring, cluster detection). The handoff file tells Tool 2 exactly which URLs to audit and why.

---

## File location and naming

Produced on every full pipeline run alongside the other output files:

```
output/competitor_handoff_<topic>_<YYYYMMDD_HHMM>.json
```

The `<topic>` slug is derived from the input keyword CSV filename (same as `market_analysis_*.json`).

---

## Schema

### Top-level fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | string | ✅ | Always `"1.0"` |
| `source_run_id` | string | ✅ | Unique ID of the Tool 1 run that produced this file |
| `source_run_timestamp` | string | ✅ | ISO 8601 UTC timestamp of the run |
| `client_domain` | string | ✅ | The client's primary domain (e.g. `livingsystems.ca`) |
| `client_brand_names` | array of strings | ✅ | Brand name patterns for the client |
| `targets` | array of target objects | ✅ | Competitor URLs for Tool 2 to audit (may be empty) |
| `exclusions` | object | ✅ | Counts of URLs excluded from `targets` |

### Target object fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | string | ✅ | Full URL of the competitor page |
| `domain` | string | ✅ | Hostname extracted from the URL |
| `rank` | integer | ✅ | Organic rank position on the SERP |
| `entity_type` | string | ✅ | Entity classification (counselling, directory, media, etc.) |
| `content_type` | string | ✅ | Content type (service, guide, directory, news, pdf, other) |
| `title` | string | ✅ | Page title from the SERP result |
| `source_keyword` | string | ✅ | The root keyword for which this URL ranked |
| `primary_keyword_for_url` | string | ✅ | The keyword for which this URL had its best (lowest) rank |

### Exclusions object fields

| Field | Type | Description |
|-------|------|-------------|
| `client_urls_excluded` | integer | URLs on the client domain that were excluded |
| `omit_list_excluded` | integer | URLs excluded because their domain is in `omit_from_audit` |
| `omit_list_used` | array of strings | The domains that were in the omit list for this run |

---

## Selection logic

For each keyword:

1. Take the top N organic results (default N=10, set by `config.yml → audit_targets.n`).
2. Exclude URLs whose domain matches the client domain.
3. Exclude URLs whose domain is in `config.yml → audit_targets.omit_from_audit`.
4. Add each remaining URL to `targets` with `source_keyword` set.

If the same URL ranks for multiple keywords, it appears in `targets` multiple times (once per `source_keyword`). This is intentional — Tool 2 uses `source_keyword` to understand why each target matters.

---

## How Tool 2 consumes this file

Tool 2's `get_latest_market_data()` reads this file to populate its audit queue. It uses:

- `targets[*].url` — the page to fetch and audit
- `targets[*].source_keyword` — for context on why the page matters
- `targets[*].entity_type` and `targets[*].content_type` — for initial scoring context
- `client_domain` — to exclude the client from competitor comparisons
- `exclusions` — for audit traceability

---

## Validation

Tool 1 validates the handoff against `handoff_schema.json` before writing. If validation fails:
- The handoff file is **not written**
- The schema violation is logged with the specific failing field
- The other output files (`market_analysis_*.json`, `*.xlsx`, `*.md`) are **not deleted**

If organic results are empty (no SERP data collected), no handoff file is written.

---

## Configuration

```yaml
# config.yml
audit_targets:
  n: 10                  # Number of top organic URLs per keyword
  omit_from_audit: []    # Domains to exclude from the handoff
```
