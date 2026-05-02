---
name: Development setup
description: How to run tests, activate venv, key env vars
type: project
---

Always activate venv before running Python: `source venv/bin/activate`

Run tests: `python -m pytest test_*.py -q` — expected 76 passed, 3 skipped (tkinter skipped in headless env).

Required env vars: `SERPAPI_KEY` and `ANTHROPIC_API_KEY` (only for content brief generation). Set in `.env`.

**Why:** Project uses a local venv. `pytest` and `anthropic` are now in requirements.txt but may not be installed in a fresh venv — run `pip install -r requirements.txt` first.

**How to apply:** Don't use system Python or suggest `python` (not aliased); use `python3` or the venv's `python`.
