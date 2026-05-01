# PAA intent classification — External Locus / Systemic / General tagging

`intent_classifier.py` tags every PAA question with:
- **External Locus** — Medical model language (diagnosis, treatment, disorder, patient…)
- **Systemic** — Bowen Theory language (differentiation, emotional cutoff, triangulation…)
- **General** — Neither

Tags written to `market_analysis_*.json` (`Intent_Tag`, `Intent_Confidence` fields). Systemic-tagged questions are passed to the LLM as `bowen_reframe_faqs` in the content brief payload.
