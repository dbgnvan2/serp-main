# Database — SQLite schema, tables, and migration notes

SQLite at `serp_data.db`. Key tables:

| Table | Contents |
|-------|----------|
| `runs` | Each audit run (run_id, date, params_hash) |
| `serp_results` | All ranked results per keyword per run |
| `url_features` | Enriched URL data including Moz DA/PA columns |
| `domain_features` | Entity type per domain |
| `autocomplete_suggestions` | Search autocomplete data |
| `keyword_feasibility` | DA gap scores, feasibility status, pivot variants per run |
| `da_cache` | DataForSEO domain rank cache (30-day TTL) |
| `moz_cache` | Moz DA/PA cache (30-day TTL) |

All schema changes use `CREATE TABLE IF NOT EXISTS` or `ALTER TABLE … ADD COLUMN` wrapped in `try/except OperationalError` — migrations run automatically on first use.
