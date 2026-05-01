"""Diagnostic script for content-type classifier gaps.

Loads a fixture run's organic results and reports which URLs are classified
as 'other', grouping them by domain and showing titles + snippets for review.

Usage:
    python scripts/classifier_audit.py output/market_analysis_<topic>_<ts>.json
    python scripts/classifier_audit.py output/market_analysis_<topic>_<ts>.json --output docs/classifier_audit_<topic>.md
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


def run_audit(json_path: str) -> list[str]:
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    organic = data.get("organic_results", [])
    if not organic:
        return ["No organic_results in file."]

    total = len(organic)
    other_rows = [r for r in organic if (r.get("Content_Type") or "").lower() == "other"]
    other_count = len(other_rows)

    lines = []
    lines.append(f"# Classifier Audit")
    lines.append(f"")
    lines.append(f"**Source:** `{json_path}`")
    lines.append(f"**Total organic rows:** {total}")
    lines.append(f"**Classified as `other`:** {other_count} ({100*other_count/max(1,total):.1f}%)")
    lines.append(f"")

    # Count by content type
    ct_counts = Counter(r.get("Content_Type", "N/A") for r in organic)
    lines.append("## Content-type distribution (all organic)")
    lines.append("")
    for ct, count in sorted(ct_counts.items(), key=lambda x: -x[1]):
        lines.append(f"- `{ct}`: {count} ({100*count/total:.1f}%)")
    lines.append("")

    if not other_rows:
        lines.append("No `other` classifications to audit.")
        return lines

    # Group 'other' rows by domain
    domain_groups: dict[str, list] = defaultdict(list)
    for r in other_rows:
        domain = r.get("Source") or r.get("domain") or "unknown"
        domain_groups[domain].append(r)

    lines.append(f"## Domains contributing most `other` classifications")
    lines.append("")
    domain_counts = sorted(domain_groups.items(), key=lambda x: -len(x[1]))
    for domain, rows in domain_counts[:20]:
        lines.append(f"### {domain} ({len(rows)} rows)")
        for r in rows[:5]:
            kw = r.get("Source_Keyword") or r.get("Root_Keyword") or ""
            link = r.get("Link") or ""
            title = r.get("Title") or ""
            snippet = (r.get("Snippet") or "")[:80]
            entity = r.get("Entity_Type") or "N/A"
            lines.append(f"- **kw:** {kw[:50]}")
            lines.append(f"  **link:** {link}")
            lines.append(f"  **title:** {title}")
            lines.append(f"  **entity:** {entity}  **snippet:** {snippet}")
        lines.append("")

    # Suggest likely fixes based on URL patterns
    lines.append("## Pattern analysis — likely misclassifications")
    lines.append("")
    service_candidates = []
    guide_candidates = []
    for r in other_rows:
        link = (r.get("Link") or "").lower()
        title = (r.get("Title") or "").lower()
        entity = (r.get("Entity_Type") or "").lower()
        domain = r.get("Source") or ""
        if any(seg in link for seg in ["/service", "/services/", "/therapy", "/counselling",
                                       "/counseling", "/our-team", "/about-us"]):
            service_candidates.append((domain, link, r.get("Title", "")))
        elif link.rstrip("/").count("/") <= 3 and entity in ("counselling", "nonprofit", "legal"):
            # bare domain root or single-path on a provider domain
            service_candidates.append((domain, link, r.get("Title", "")))
        elif any(seg in link for seg in ["/blog/", "/articles/", "/posts/", "/news/", "/resources/"]):
            guide_candidates.append((domain, link, r.get("Title", "")))

    if service_candidates:
        lines.append(f"### Likely service pages ({len(service_candidates)} candidates)")
        lines.append("These 'other' URLs have URL paths or domain types that suggest they are service pages:")
        for domain, link, title in service_candidates[:15]:
            lines.append(f"- `{link}` — {title[:60]}")
        lines.append("")

    if guide_candidates:
        lines.append(f"### Likely guide/blog pages ({len(guide_candidates)} candidates)")
        lines.append("These 'other' URLs have blog/article paths that suggest they are guides:")
        for domain, link, title in guide_candidates[:15]:
            lines.append(f"- `{link}` — {title[:60]}")
        lines.append("")

    lines.append("## Recommended rules for `url_pattern_rules.yml`")
    lines.append("")
    lines.append("Based on the above, add the following to `url_pattern_rules.yml` and re-run:")
    lines.append("")
    lines.append("```yaml")
    lines.append("# Patterns applied AFTER entity classification; first match wins.")
    lines.append("# pattern: regex matched against the full URL (lowercased)")
    lines.append("# entity_types: list of entity types where this rule applies (or [any])")
    lines.append("# content_type: the content type to assign")
    lines.append("url_pattern_rules:")
    lines.append("  - pattern: '/service[s]?(/|$)|/therapy(/|$)|/counselling(/|$)|/counseling(/|$)|/our-team(/|$)'")
    lines.append("    entity_types: [counselling, nonprofit, legal]")
    lines.append("    content_type: service")
    lines.append("  - pattern: '^https?://[^/]+/?$'")
    lines.append("    entity_types: [counselling, nonprofit, legal]")
    lines.append("    content_type: service")
    lines.append("  - pattern: '/blog/|/articles?/|/posts?/|/resources/'")
    lines.append("    entity_types: [any]")
    lines.append("    content_type: guide")
    lines.append("```")
    lines.append("")

    return lines


def main():
    parser = argparse.ArgumentParser(description="Audit content classifier 'other' output")
    parser.add_argument("json_file", help="Path to market_analysis_*.json")
    parser.add_argument("--output", "-o", help="Write report to this file (default: stdout)")
    args = parser.parse_args()

    lines = run_audit(args.json_file)
    report = "\n".join(lines)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(report + "\n", encoding="utf-8")
        print(f"Audit report written to {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
