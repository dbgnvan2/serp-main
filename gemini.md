# Project Context: SERP Intelligence & Content Strategy Map# Master Project Standards: Living Systems Suite

## 🏗️ Architectural Core
- **Zero Hard-Coding:** Strings for clinical terms, API keys, or competitor domains are forbidden in `.py` files.
- **Single Source of Truth:** - Technical/Client settings: `./shared_config.json`
  - Clinical Theory/Weights: `./clinical_dictionary.json`
- **Inter-App Handover:** `serp-compete` must prioritize targets found dynamically by `serp-keyword`.

## 🧠 Clinical Integrity (Bowen Theory)
- **The Filter:** All analysis must distinguish between Symptom-Fixing (Tier 1) and Pattern-Observing (Tier 3).
- **The Pivot:** If Tier 1 keywords are high, the system must trigger a "Pattern-First" reframe.