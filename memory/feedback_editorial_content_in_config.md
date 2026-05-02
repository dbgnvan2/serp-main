---
name: Editorial content belongs in config files
description: Flag and externalize trigger words, rules, vocabulary lists embedded in .py files
type: feedback
originSessionId: 84eed1ae-a2bd-4855-bb22-45464b86319c
---
Editorial content lives in config files (YAML/JSON), not Python source. This includes trigger words, classification rules, mapping tables, and vocabulary lists — anything that requires editorial judgment to refine.

**Why:** Discovered when Bowen pattern trigger words were hardcoded in `serp_audit.py`. Editing triggers required a Python change and test run instead of a simple YAML edit. Externalized to `strategic_patterns.yml`.

**How to apply:** During any task, if you find editorial content in a `.py` file, flag it as technical debt to externalize — even when not asked to fix it. This is Rule 7 in `~/.claude/CLAUDE.md`.
