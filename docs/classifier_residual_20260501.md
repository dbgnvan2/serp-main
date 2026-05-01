# Classifier Residual Report

**Date:** 2026-05-01  
**Fixture:** `output/market_analysis_couples_therapy_20260501_0717.json`  
**Changes applied:** Fix 1 (top-10 organic denominator) + Fix 5b (url_pattern_rules.yml)

---

## Before fixes

All 6 keywords: `confidence: low`  
Root cause: denominator included all 25–30 rows (multiple pages + all SERP modules), not top-10 organic.

---

## After Fix 1 + Fix 5b

| Keyword | Primary Intent | Confidence | Classified / Organic |
|---------|---------------|------------|----------------------|
| How much is couples therapy in Vancouver? | informational | **high** | 8/10 |
| success rate of couples therapy? | informational | **high** | 9/10 |
| What type of therapist is best for couples therapy | informational | **high** | 8/10 |
| effective couples therapy? | informational | **medium** | 7/10 |
| couples counselling | mixed | **high** | 8/10 |
| how does couples counselling work | informational | **medium** | 6/10 |

All 6 keywords improved from `low` to `medium` or `high`. Spec acceptance criterion met.

---

## Residual unclassified URLs

Of the original 113 rows with `other`/`N/A`/`unknown` content type:
- **36 reclassified** by URL pattern rules (32%)
- **77 still unclassified** (68%)

### What remains in the residual

Top remaining contributors:
- **Reddit threads** (4+ rows): Correctly uncategorised per spec edge case 5. Reddit is a discussion forum, not a service or guide page. No rule added.
- **Bare domain roots with unknown entity type** (e.g. `stephenmadigan.ca/`): Entity_Type = "N/A" → URL pattern rule requires a known entity type. These stay uncategorised.
- **Non-standard URL paths** on counselling providers: paths like `/about-us/`, `/contact/`, `/faq/` that don't match the service-path pattern. Low value to classify.
- **URLs from SERP pages 2 and 3** (ranks 11–30): These are excluded from intent computation by the top-10 cap. Reclassifying them would not change confidence scores.

### Agent assessment

**Acceptable.** With 6/10 to 9/10 classified organic URLs per keyword, confidence is `medium` or `high` for all keywords. The remaining `other` and `N/A` rows are:
1. Genuinely ambiguous (bare paths, unknown entity types)
2. Reddit/forum content that should remain uncategorised per spec
3. From pages 2–3 which don't affect the verdict denominator

Further improvement would require entity type classification of bare domains (entity enrichment is a separate concern) or deeper HTML content analysis. Neither is required for the spec to be satisfied.

---

## Recommendation

The current url_pattern_rules.yml is sufficient for this fixture. Monitor the `classified_organic_url_count` field in future runs — if it drops below 5 for any keyword, that keyword will show `primary_intent: null` and should trigger entity classifier investigation.
