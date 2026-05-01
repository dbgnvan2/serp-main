# GUI step reference — serp-me.py

| Step | Script | When to run |
|------|--------|-------------|
| 1. Full Pipeline | `run_pipeline.py` | Fresh SERP fetch for a keyword set |
| 2. Fetch SERPs Only | `serp_audit.py` | Fetch without pipeline validation |
| 3. Content Brief | `generate_content_brief.py` | After a pipeline run |
| 4. Refresh Outputs | `refresh_analysis_outputs.py` | Re-classify without re-fetching |
| 5. Export History | `export_history.py` | Export DB to CSV |
| 6. Domain Overrides | — | Review/approve entity type overrides |
| 7. Feasibility Analysis | `run_feasibility.py` | DA scoring from existing JSON (cached — free to re-run) |
