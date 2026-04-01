# Expert System Spec: The "Systemic Strategist" (Phase 3)

## 1. Objective
To transition from static snapshots to a continuous intelligence engine that tracks competitor volatility, identifies "Anxiety Loops" in search intent, and automatically drafts Bowen-based content reframes.

## 2. Core Functional Modules

### Module A: The Longitudinal Memory (SQL Persistence)
- **Action:** Replace CSV-based storage with a relational database (SQLite/PostgreSQL).
- **Requirement:** Create tables for `competitor_history`, `keyword_rank_tracking`, and `semantic_gap_logs`.
- **Expert Logic:** Implement **Volatility Alerts**—if a competitor's average position moves by more than 3 places or their "Systems Score" drops on a high-traffic page, the system flags a "Strategic Opening".

### Module B: The "Anxiety Loop" Intersector
- **Action:** Cross-reference People Also Ask (PAA) data with Competitor Traffic Magnets.
- **Requirement:** Automatically map common user anxieties (e.g., "cost of counselling") to the specific competitor pages currently "owning" those answers.
- **Expert Logic:** Rank content opportunities by "Conversion Potential"—prioritizing keywords where high traffic meets a total "Systemic Vacuum" (0% systems score).

### Module C: The Automated Bowen Reframe Engine
- **Action:** Generate structured content briefs that explicitly counter the "Medical Model".
- **Requirement:** For any "Traffic Magnet" identified as having a high Medical Score (e.g., Wellspring's North Vancouver page at score 13), generate a brief that targets the same keywords but applies a systems lens.
- **Expert Logic:** The output must not be a generic article; it should be a "Pattern-First" blueprint that addresses the nuclear family process behind the symptom.

## 3. Technical Requirements for the "Expert" Shift

| Feature | Junior Developer Level | Expert System Level |
| :--- | :--- | :--- |
| **Data Architecture** | Reads `Key_domains.csv` and prints a table. | Maintains a `competitor_history.db` to track trends over months. |
| **Analysis Depth** | Lists keywords and DAs. | Calculates "Feasibility Drift"—identifying when your DA (35) is catching up to a competitor's PA. |
| **Reframing** | Counts "Medical" vs. "Systems" phrases. | Uses LLM agents to draft a 500-word "Systems Reframe" of a competitor's top page. |
| **Operation** | Runs only when manually triggered. | Runs on a weekly schedule (CRON) and outputs a "Strategic Briefing." |

## 4. Updated Database Schema Recommendation
To support this, your coding agent should initialize the following SQLite structure:
- **Competitors:** `domain`, `avg_da`, `last_crawled_at`.
- **Traffic_Magnets:** `url`, `primary_keyword`, `est_traffic`, `medical_score`, `systems_score`.
- **Market_Gaps:** `keyword`, `competitor_overlap_count`, `feasibility_status`.

## Strategic Outcome
By executing this spec, your system will identify that while No Fear Counselling dominates the "Vancouver" market with an average position of 2.1, their 0% systems score on attachment-based keywords represents a "Relational Pattern" gap. Your expert system will then automatically draft the "Bowen Reframe" page needed to capture that specific traffic.
