# API modes — Low API / Balanced / Deep Research

| Mode | Google Pages | Maps Pages | AI Follow-up |
|------|-------------|-----------|--------------|
| Low API | 1 | 1 | No |
| Balanced (default) | 3 | 1 | Defend/Strengthen only |
| Deep Research | configurable | configurable | Yes (up to 5 calls) |

Set via `config.yml` (`app.balanced_mode`, `app.deep_research_mode`) or env vars:
```bash
SERP_LOW_API_MODE=1
SERP_BALANCED_MODE=1
SERP_DEEP_RESEARCH_MODE=1
```
