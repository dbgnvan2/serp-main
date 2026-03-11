import unittest

from classifiers import EntityClassifier
import generate_domain_override_candidates as gdoc


class TestGenerateDomainOverrideCandidates(unittest.TestCase):
    def test_collect_candidates_filters_existing_overrides(self):
        data = {
            "organic_results": [
                {
                    "Link": "https://example.com/a",
                    "Source": "Example",
                    "Title": "A",
                    "Rank": 1,
                    "Source_Keyword": "kw1",
                    "Entity_Type": "counselling",
                },
                {
                    "Link": "https://example.com/b",
                    "Source": "Example",
                    "Title": "B",
                    "Rank": 2,
                    "Source_Keyword": "kw2",
                    "Entity_Type": "counselling",
                },
                {
                    "Link": "https://counsellingbc.com/a",
                    "Source": "CounsellingBC",
                    "Title": "C",
                    "Rank": 3,
                    "Source_Keyword": "kw1",
                    "Entity_Type": "directory",
                },
                {
                    "Link": "https://counsellingbc.com/b",
                    "Source": "CounsellingBC",
                    "Title": "D",
                    "Rank": 4,
                    "Source_Keyword": "kw2",
                    "Entity_Type": "directory",
                },
                {
                    "Link": "https://counsellingbc.com/c",
                    "Source": "CounsellingBC",
                    "Title": "E",
                    "Rank": 5,
                    "Source_Keyword": "kw2",
                    "Entity_Type": "directory",
                },
            ]
        }
        overrides = {"example.com": "counselling"}
        classifier = EntityClassifier(override_file="/nonexistent/overrides.yml")
        candidates = gdoc.collect_candidates(data, overrides, classifier, min_rows=3, min_keywords=2)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["domain"], "counsellingbc.com")

    def test_render_markdown_includes_candidate(self):
        report = gdoc.render_markdown(
            [
                {
                    "domain": "fresh.com",
                    "suggested_type": "legal",
                    "confidence": 0.7,
                    "evidence": ["domain_legal_pattern"],
                    "organic_rows": 4,
                    "source_keywords": ["kw1", "kw2"],
                    "source_keyword_count": 2,
                    "best_rank": 1,
                    "current_entity_types": {"legal": 4},
                    "sample_titles": ["Title 1", "Title 2"],
                }
            ],
            "market_analysis_v2.json",
            "domain_overrides.yml",
            3,
            2,
        )
        self.assertIn("fresh.com", report)
        self.assertIn("## Needs Human Judgment", report)
        self.assertIn("Suggested Type", report)

    def test_split_candidates_separates_high_confidence(self):
        high_confidence, needs_judgment = gdoc.split_candidates([
            {
                "domain": "reddit.com",
                "suggested_type": "media",
                "confidence": 0.9,
                "evidence": ["known_media_domain"],
                "organic_rows": 5,
                "source_keywords": ["kw1", "kw2"],
                "source_keyword_count": 2,
                "best_rank": 1,
                "current_entity_types": {"media": 5},
                "sample_titles": ["Title 1"],
            },
            {
                "domain": "macleanfamilylaw.ca",
                "suggested_type": "legal",
                "confidence": 0.7,
                "evidence": ["domain_legal_pattern"],
                "organic_rows": 4,
                "source_keywords": ["kw1", "kw2"],
                "source_keyword_count": 2,
                "best_rank": 2,
                "current_entity_types": {},
                "sample_titles": ["Title 2"],
            },
        ])
        self.assertEqual([item["domain"] for item in high_confidence], ["reddit.com"])
        self.assertEqual([item["domain"] for item in needs_judgment], ["macleanfamilylaw.ca"])

    def test_collect_candidates_skips_unclassified_noise(self):
        data = {
            "organic_results": [
                {
                    "Link": "https://unknown-a.com/1",
                    "Source": "Unknown A",
                    "Title": "A1",
                    "Rank": 1,
                    "Source_Keyword": "kw1",
                    "Entity_Type": "N/A",
                },
                {
                    "Link": "https://unknown-a.com/2",
                    "Source": "Unknown A",
                    "Title": "A2",
                    "Rank": 2,
                    "Source_Keyword": "kw2",
                    "Entity_Type": "N/A",
                },
                {
                    "Link": "https://unknown-a.com/3",
                    "Source": "Unknown A",
                    "Title": "A3",
                    "Rank": 3,
                    "Source_Keyword": "kw3",
                    "Entity_Type": "N/A",
                },
                {
                    "Link": "https://unknown-a.com/4",
                    "Source": "Unknown A",
                    "Title": "A4",
                    "Rank": 4,
                    "Source_Keyword": "kw3",
                    "Entity_Type": "N/A",
                },
            ]
        }
        overrides = {}
        classifier = EntityClassifier(override_file="/nonexistent/overrides.yml")
        candidates = gdoc.collect_candidates(data, overrides, classifier, min_rows=4, min_keywords=2)
        self.assertEqual(candidates, [])


if __name__ == "__main__":
    unittest.main()
