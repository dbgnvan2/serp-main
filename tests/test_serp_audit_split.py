"""
Tests for Fix I.6 — extract pattern_matching.py and handoff_writer.py from serp_audit.py.

Spec: serp_tool1_improvements_spec.md#I.6
Approved scope: pattern_matching.py + handoff_writer.py only (reduced scope per
docs/serp_audit_split_plan_20260501.md — 500-line target relaxed to guideline).
"""
import importlib
import os
import unittest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestI62FilesExistWithFunctions(unittest.TestCase):
    """I.6.2 — New files exist with the approved functions."""

    _EXPECTED = {
        "pattern_matching": [
            "get_ngrams",
            "count_syllables",
            "calculate_reading_level",
            "calculate_sentiment",
            "calculate_subjectivity",
            "_dataset_topic_profile",
            "_validate_strategic_patterns",
            "_load_strategic_patterns",
            "analyze_strategic_opportunities",
        ],
        "handoff_writer": [
            "build_competitor_handoff",
        ],
    }

    def test_i62_files_exist_with_functions(self):
        for module_name, expected_fns in self._EXPECTED.items():
            path = os.path.join(_REPO_ROOT, f"{module_name}.py")
            self.assertTrue(os.path.exists(path), f"{module_name}.py does not exist")
            mod = importlib.import_module(module_name)
            for fn in expected_fns:
                self.assertTrue(
                    hasattr(mod, fn),
                    f"{module_name}.{fn} not found after split"
                )


class TestI63MainModuleSize(unittest.TestCase):
    """I.6.3 — serp_audit.py is smaller than before the split.

    The 500-line target was relaxed (size is a guideline, not a hard rule).
    Reduced scope extracts ~270 lines; the original was 2332 lines.
    """

    def test_i63_main_module_size(self):
        path = os.path.join(_REPO_ROOT, "serp_audit.py")
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
        self.assertLessEqual(
            len(lines), 2200,
            f"serp_audit.py is {len(lines)} lines; extraction did not reduce size below 2200"
        )


class TestI65PipelineOutputUnchanged(unittest.TestCase):
    """I.6.5 — serp_audit re-exports resolve to the same implementations as the new modules."""

    def test_i65_pattern_matching_passthrough(self):
        import serp_audit
        import pattern_matching
        self.assertIs(
            serp_audit.get_ngrams, pattern_matching.get_ngrams,
            "serp_audit.get_ngrams should resolve to pattern_matching.get_ngrams"
        )
        self.assertIs(
            serp_audit.analyze_strategic_opportunities,
            pattern_matching.analyze_strategic_opportunities,
            "serp_audit.analyze_strategic_opportunities should resolve to "
            "pattern_matching.analyze_strategic_opportunities"
        )

    def test_i65_handoff_passthrough(self):
        import serp_audit
        import handoff_writer
        self.assertIs(
            serp_audit.build_competitor_handoff,
            handoff_writer.build_competitor_handoff,
            "serp_audit.build_competitor_handoff should resolve to "
            "handoff_writer.build_competitor_handoff"
        )

    def test_i65_get_ngrams_output_unchanged(self):
        import pattern_matching
        text = "clinical diagnosis treatment family therapy"
        result = pattern_matching.get_ngrams(text, 2)
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0, "get_ngrams should return bigrams")
        for phrase in result:
            self.assertEqual(len(phrase.split()), 2, f"Expected bigram, got: {phrase!r}")

    def test_i65_analyze_strategic_opportunities_returns_list(self):
        import pattern_matching
        ngrams = [
            {"Phrase": "clinical diagnosis", "Count": 3},
            {"Phrase": "medical treatment", "Count": 2},
        ]
        result = pattern_matching.analyze_strategic_opportunities(ngrams)
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0, "Should return at least one recommendation")

    def test_i65_build_competitor_handoff_structure(self):
        from handoff_writer import build_competitor_handoff
        organic = [
            {"Root_Keyword": "couples therapy", "Rank": 1,
             "Link": "https://example.com/page", "Entity_Type": "practice",
             "Content_Type": "service_page", "Title": "Example Page"},
        ]
        result = build_competitor_handoff(
            organic, run_id="test", run_timestamp="2026-05-01",
            client_domain="livingsystems.ca", client_brand_names=["Living Systems"],
        )
        self.assertIsNotNone(result)
        self.assertIn("targets", result)
        self.assertIn("schema_version", result)
