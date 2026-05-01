# Configuration reference — config.yml keys and rule files

**`config.yml`** — all operational settings:
- `serpapi.*` — API params (engine, location, pagination, retries, modes)
- `files.*` — input/output file paths (auto-updated by GUI after each run)
- `enrichment.*` — URL enrichment settings
- `app.*` — API mode flags (`balanced_mode`, `deep_research_mode`)
- `moz.cache_ttl_days` — DA cache lifetime in days (default 30)
- `feasibility.*` — DA gap thresholds, client DA, neighbourhoods, pivot settings
- `audit_targets.n` — top-N organic URLs per keyword exported to competitor handoff (default 10)
- `audit_targets.omit_from_audit` — domains excluded from the handoff (never sent to Tool 2)
- `client.preferred_intents` — intents the client can produce content for; drives `mixed_intent_strategy`
- `analysis_report.*` — client context injected into LLM prompts

**`domain_overrides.yml`** — manual entity type overrides (e.g., `psychologytoday.com: directory`).

**`intent_mapping.yml`** (spec v2) — rule table mapping `(content_type, entity_type, local_pack, domain_role)` → SERP intent (informational / commercial_investigation / transactional / navigational / local / uncategorised). First-match-wins, top of file = highest priority. Edit this file to refine intent assignments — don't push exceptions into Python.

**`url_pattern_rules.yml`** — URL-path fallback rules for pages the HTML enricher couldn't classify. Edit to improve classification rates without touching Python.
