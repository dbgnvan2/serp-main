"""Unit tests for intent_verdict.py.

Covers:
  - YAML schema validation (load_mapping)
  - Each rule path in intent_mapping.yml fires correctly
  - Aggregation: distribution (integers), primary_intent, is_mixed, confidence
  - Fix 1: denominator is top-10 organic only; local pack / other modules excluded
  - Fix 2: intent_distribution values are integers; evidence.intent_counts removed
  - Edge cases: empty SERP, all uncategorised, null primary_intent (n<5),
    exactly-at-threshold, ties
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from intent_verdict import (
    DEFAULT_THRESHOLDS,
    VALID_INTENTS,
    _classify_url,
    _domain_role_for_url,
    _matches_rule,
    compute_serp_intent,
    load_mapping,
)


# ─── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def real_mapping():
    """The committed intent_mapping.yml — proves the file we ship loads."""
    return load_mapping()


@pytest.fixture
def minimal_mapping():
    """A tiny in-memory mapping for isolated rule tests."""
    return {
        "version": 1,
        "rules": [
            {
                "match": {
                    "domain_role": "client",
                    "content_type": "any",
                    "entity_type": "any",
                    "local_pack": "any",
                },
                "intent": "navigational",
            },
            {
                "match": {
                    "content_type": "guide",
                    "entity_type": "any",
                    "local_pack": "any",
                    "domain_role": "any",
                },
                "intent": "informational",
            },
            {
                "match": {
                    "content_type": "service",
                    "entity_type": "counselling",
                    "local_pack": "yes",
                    "domain_role": "any",
                },
                "intent": "local",
            },
            {
                "match": {
                    "content_type": "any",
                    "entity_type": "any",
                    "local_pack": "any",
                    "domain_role": "any",
                },
                "intent": "uncategorised",
            },
        ],
    }


def _row(rank, link, content_type, entity_type, title="t", source=None):
    return {
        "rank": rank,
        "title": title,
        "source": source or link,
        "link": link,
        "content_type": content_type,
        "entity_type": entity_type,
    }


# ─── load_mapping schema validation ──────────────────────────────────────────


class TestLoadMapping:
    def test_loads_real_yaml(self, real_mapping):
        assert "rules" in real_mapping
        assert len(real_mapping["rules"]) > 0

    def test_real_yaml_has_catch_all(self, real_mapping):
        last = real_mapping["rules"][-1]
        assert all(v == "any" for v in last["match"].values())

    def test_real_yaml_yes_no_are_strings(self, real_mapping):
        # Regression: PyYAML would otherwise convert unquoted yes/no to booleans
        for rule in real_mapping["rules"]:
            lp = rule["match"]["local_pack"]
            assert lp in ("yes", "no", "any"), f"local_pack={lp!r} got bool-converted"

    def test_real_yaml_intents_are_valid(self, real_mapping):
        for rule in real_mapping["rules"]:
            assert rule["intent"] in VALID_INTENTS

    def test_rejects_missing_rules(self, tmp_path):
        bad = tmp_path / "bad.yml"
        bad.write_text("version: 1\n")
        with pytest.raises(ValueError, match="missing top-level 'rules'"):
            load_mapping(str(bad))

    def test_rejects_invalid_intent(self, tmp_path):
        bad = tmp_path / "bad.yml"
        bad.write_text(yaml.safe_dump({
            "rules": [{
                "match": {"content_type": "any", "entity_type": "any",
                          "local_pack": "any", "domain_role": "any"},
                "intent": "buying",
            }]
        }))
        with pytest.raises(ValueError, match="invalid intent"):
            load_mapping(str(bad))

    def test_rejects_missing_match_key(self, tmp_path):
        bad = tmp_path / "bad.yml"
        bad.write_text(yaml.safe_dump({
            "rules": [{
                "match": {"content_type": "any", "entity_type": "any",
                          "local_pack": "any"},  # missing domain_role
                "intent": "informational",
            }]
        }))
        with pytest.raises(ValueError, match="missing key"):
            load_mapping(str(bad))


# ─── _domain_role_for_url ────────────────────────────────────────────────────


class TestDomainRole:
    def test_client_match(self):
        assert _domain_role_for_url(
            "https://livingsystems.ca/about", "livingsystems.ca", []
        ) == "client"

    def test_known_competitor_match(self):
        assert _domain_role_for_url(
            "https://example-rival.ca/foo",
            "livingsystems.ca",
            ["example-rival.ca"],
        ) == "known_competitor"

    def test_other_when_no_match(self):
        assert _domain_role_for_url(
            "https://psychologytoday.com/x", "livingsystems.ca", []
        ) == "other"

    def test_client_takes_precedence_over_known(self):
        assert _domain_role_for_url(
            "https://livingsystems.ca/x",
            "livingsystems.ca",
            ["livingsystems.ca"],
        ) == "client"

    def test_empty_link_returns_other(self):
        assert _domain_role_for_url("", "livingsystems.ca", []) == "other"

    def test_case_insensitive(self):
        assert _domain_role_for_url(
            "https://LivingSystems.ca/x", "livingsystems.ca", []
        ) == "client"


# ─── _matches_rule ───────────────────────────────────────────────────────────


class TestMatchesRule:
    def test_any_matches_anything(self):
        assert _matches_rule(
            {"content_type": "any", "entity_type": "any",
             "local_pack": "any", "domain_role": "any"},
            {"content_type": "guide", "entity_type": "media",
             "local_pack": "yes", "domain_role": "other"},
        )

    def test_specific_must_match_exactly(self):
        assert not _matches_rule(
            {"content_type": "service", "entity_type": "any",
             "local_pack": "any", "domain_role": "any"},
            {"content_type": "guide", "entity_type": "any",
             "local_pack": "any", "domain_role": "any"},
        )

    def test_yes_does_not_match_no(self):
        assert not _matches_rule(
            {"content_type": "any", "entity_type": "any",
             "local_pack": "yes", "domain_role": "any"},
            {"content_type": "guide", "entity_type": "any",
             "local_pack": "no", "domain_role": "any"},
        )


# ─── _classify_url with minimal_mapping ──────────────────────────────────────


class TestClassifyUrl:
    def test_client_overrides_content(self, minimal_mapping):
        intent = _classify_url(
            {"content_type": "guide", "entity_type": "counselling",
             "local_pack": "yes", "domain_role": "client"},
            minimal_mapping["rules"],
        )
        assert intent == "navigational"

    def test_guide_when_not_client(self, minimal_mapping):
        intent = _classify_url(
            {"content_type": "guide", "entity_type": "counselling",
             "local_pack": "yes", "domain_role": "other"},
            minimal_mapping["rules"],
        )
        assert intent == "informational"

    def test_local_when_service_counselling_local(self, minimal_mapping):
        intent = _classify_url(
            {"content_type": "service", "entity_type": "counselling",
             "local_pack": "yes", "domain_role": "other"},
            minimal_mapping["rules"],
        )
        assert intent == "local"

    def test_falls_through_to_catch_all(self, minimal_mapping):
        intent = _classify_url(
            {"content_type": "news", "entity_type": "media",
             "local_pack": "no", "domain_role": "other"},
            minimal_mapping["rules"],
        )
        assert intent == "uncategorised"


# ─── Real intent_mapping.yml — spot-check critical edge cases ────────────────


class TestRealMappingEdgeCases:
    def test_service_on_directory_is_commercial_investigation(self, real_mapping):
        intent = _classify_url(
            {"content_type": "service", "entity_type": "directory",
             "local_pack": "yes", "domain_role": "other"},
            real_mapping["rules"],
        )
        assert intent == "commercial_investigation"

    def test_guide_on_counselling_with_local_pack_is_informational(self, real_mapping):
        intent = _classify_url(
            {"content_type": "guide", "entity_type": "counselling",
             "local_pack": "yes", "domain_role": "other"},
            real_mapping["rules"],
        )
        assert intent == "informational"

    def test_nonprofit_service_is_transactional(self, real_mapping):
        intent = _classify_url(
            {"content_type": "service", "entity_type": "nonprofit",
             "local_pack": "no", "domain_role": "other"},
            real_mapping["rules"],
        )
        assert intent == "transactional"

    def test_other_content_is_uncategorised(self, real_mapping):
        intent = _classify_url(
            {"content_type": "other", "entity_type": "media",
             "local_pack": "no", "domain_role": "other"},
            real_mapping["rules"],
        )
        assert intent == "uncategorised"

    def test_unknown_content_is_uncategorised(self, real_mapping):
        intent = _classify_url(
            {"content_type": "unknown", "entity_type": "N/A",
             "local_pack": "no", "domain_role": "other"},
            real_mapping["rules"],
        )
        assert intent == "uncategorised"

    def test_client_url_always_navigational(self, real_mapping):
        intent = _classify_url(
            {"content_type": "guide", "entity_type": "counselling",
             "local_pack": "no", "domain_role": "client"},
            real_mapping["rules"],
        )
        assert intent == "navigational"

    def test_counselling_service_no_local_pack_is_transactional(self, real_mapping):
        intent = _classify_url(
            {"content_type": "service", "entity_type": "counselling",
             "local_pack": "no", "domain_role": "other"},
            real_mapping["rules"],
        )
        assert intent == "transactional"

    def test_counselling_service_with_local_pack_is_local(self, real_mapping):
        intent = _classify_url(
            {"content_type": "service", "entity_type": "counselling",
             "local_pack": "yes", "domain_role": "other"},
            real_mapping["rules"],
        )
        assert intent == "local"

    def test_directory_listicle_is_commercial_investigation(self, real_mapping):
        intent = _classify_url(
            {"content_type": "directory", "entity_type": "media",
             "local_pack": "no", "domain_role": "other"},
            real_mapping["rules"],
        )
        assert intent == "commercial_investigation"

    def test_news_is_informational(self, real_mapping):
        intent = _classify_url(
            {"content_type": "news", "entity_type": "media",
             "local_pack": "no", "domain_role": "other"},
            real_mapping["rules"],
        )
        assert intent == "informational"

    def test_pdf_is_informational(self, real_mapping):
        intent = _classify_url(
            {"content_type": "pdf", "entity_type": "government",
             "local_pack": "no", "domain_role": "other"},
            real_mapping["rules"],
        )
        assert intent == "informational"

    def test_government_service_is_transactional(self, real_mapping):
        intent = _classify_url(
            {"content_type": "service", "entity_type": "government",
             "local_pack": "no", "domain_role": "other"},
            real_mapping["rules"],
        )
        assert intent == "transactional"


# ─── compute_serp_intent integration ─────────────────────────────────────────


class TestComputeSerpIntent:
    def test_empty_serp(self, real_mapping):
        result = compute_serp_intent(
            organic_rows=[], has_local_pack=False, mapping=real_mapping
        )
        # No rows → classified < 5 → primary_intent is None
        assert result["primary_intent"] is None
        assert result["is_mixed"] is False
        assert result["confidence"] == "low"
        ev = result["evidence"]
        assert ev["organic_url_count"] == 0
        assert ev["classified_organic_url_count"] == 0
        assert ev["uncategorised_organic_url_count"] == 0
        assert ev["local_pack_present"] is False
        assert ev["local_pack_member_count"] == 0
        # intent_counts must NOT appear (Fix 2)
        assert "intent_counts" not in ev

    def test_all_uncategorised(self, real_mapping):
        rows = [
            _row(1, "https://example.com/1", "other", "media"),
            _row(2, "https://example.com/2", "unknown", "N/A"),
        ]
        result = compute_serp_intent(
            organic_rows=rows, has_local_pack=False, mapping=real_mapping
        )
        # 0 classified → primary_intent is None
        assert result["primary_intent"] is None
        assert result["confidence"] == "low"
        assert result["evidence"]["uncategorised_organic_url_count"] == 2

    def test_pure_informational_high_confidence(self, real_mapping):
        # 10 guides → classified=10, organic=10 → high confidence
        rows = [
            _row(i, f"https://e{i}.com/g", "guide", "media")
            for i in range(1, 11)
        ]
        result = compute_serp_intent(
            organic_rows=rows, has_local_pack=False, mapping=real_mapping
        )
        assert result["primary_intent"] == "informational"
        assert result["is_mixed"] is False
        assert result["confidence"] == "high"
        # Fix 2: intent_distribution is integers, not fractions
        assert result["intent_distribution"]["informational"] == 10
        assert isinstance(result["intent_distribution"]["informational"], int)

    def test_pure_local(self, real_mapping):
        rows = [
            _row(i, f"https://clinic{i}.ca/", "service", "counselling")
            for i in range(1, 11)
        ]
        result = compute_serp_intent(
            organic_rows=rows, has_local_pack=True, mapping=real_mapping
        )
        assert result["primary_intent"] == "local"
        assert result["is_mixed"] is False
        assert result["evidence"]["local_pack_present"] is True

    def test_mixed_intent_5_5(self, real_mapping):
        rows = [
            _row(i, f"https://g{i}.com/", "guide", "media")
            for i in range(1, 6)
        ] + [
            _row(i, f"https://s{i}.ca/", "service", "counselling")
            for i in range(6, 11)
        ]
        result = compute_serp_intent(
            organic_rows=rows, has_local_pack=False, mapping=real_mapping
        )
        assert result["is_mixed"] is True
        assert result["primary_intent"] == "mixed"
        assert set(result["mixed_components"]) == {"informational", "transactional"}
        # intent_distribution: integers
        assert result["intent_distribution"]["informational"] == 5
        assert result["intent_distribution"]["transactional"] == 5

    def test_null_primary_when_fewer_than_5_classified(self, real_mapping):
        # 4 classified + 6 uncategorised → primary_intent must be None
        rows = [
            _row(i, f"https://g{i}.com/", "guide", "media") for i in range(1, 5)
        ] + [
            _row(i, f"https://x{i}.com/", "other", "media") for i in range(5, 11)
        ]
        result = compute_serp_intent(
            organic_rows=rows, has_local_pack=False, mapping=real_mapping
        )
        # n=4 < 5 → null primary, even though informational dominates
        assert result["primary_intent"] is None
        assert result["is_mixed"] is False
        assert result["confidence"] == "low"
        # distribution still populated from what was classified
        assert result["intent_distribution"]["informational"] == 4

    def test_confidence_medium_exactly_5_classified(self, real_mapping):
        # 5 classified + 5 uncategorised; organic=10, classified=5 → medium
        rows = [
            _row(i, f"https://g{i}.com/", "guide", "media") for i in range(1, 6)
        ] + [
            _row(i, f"https://x{i}.com/", "other", "media") for i in range(6, 11)
        ]
        result = compute_serp_intent(
            organic_rows=rows, has_local_pack=False, mapping=real_mapping
        )
        assert result["confidence"] == "medium"
        assert result["primary_intent"] == "informational"

    def test_confidence_high_exactly_8_classified(self, real_mapping):
        # 8 guides + 2 uncategorised; organic=10, classified=8 → high
        rows = [
            _row(i, f"https://g{i}.com/", "guide", "media") for i in range(1, 9)
        ] + [
            _row(i, f"https://x{i}.com/", "other", "media") for i in range(9, 11)
        ]
        result = compute_serp_intent(
            organic_rows=rows, has_local_pack=False, mapping=real_mapping
        )
        assert result["confidence"] == "high"

    def test_denominator_is_organic_rows_only(self, real_mapping):
        # Fix 1: 10 organic + simulated non-organic rows should not affect denominator.
        # Caller must cap to top-10 before calling; here we verify that passing
        # exactly 10 organic rows produces organic_url_count=10.
        organic_10 = [
            _row(i, f"https://g{i}.com/", "guide", "media") for i in range(1, 11)
        ]
        # Also simulate 5 local pack entries and 8 forum rows as SEPARATE inputs
        # (the caller would never pass them in — this test confirms the function
        # counts only what it receives).
        result = compute_serp_intent(
            organic_rows=organic_10,
            has_local_pack=True,
            local_pack_member_count=5,
            mapping=real_mapping,
        )
        assert result["evidence"]["organic_url_count"] == 10
        assert result["evidence"]["local_pack_member_count"] == 5
        assert result["evidence"]["local_pack_present"] is True

    def test_fallback_threshold_40_with_low_runner_up(self, real_mapping):
        # 4 informational + 1 transactional + 5 uncategorised → classified=5
        # info share = 4/5 = 0.8 → primary should be informational (not mixed)
        rows = [
            _row(i, f"https://g{i}.com/", "guide", "media") for i in range(1, 5)
        ] + [
            _row(5, "https://s.ca/", "service", "counselling"),
        ] + [
            _row(i, f"https://other{i}.com/", "other", "media") for i in range(6, 11)
        ]
        result = compute_serp_intent(
            organic_rows=rows, has_local_pack=False, mapping=real_mapping
        )
        assert result["primary_intent"] == "informational"
        assert result["is_mixed"] is False
        assert result["confidence"] == "medium"

    def test_confidence_low_when_few_classified(self, real_mapping):
        # 2 classified out of 10 → low (n=2 < 5)
        rows = [
            _row(1, "https://g.com/", "guide", "media"),
            _row(2, "https://s.ca/", "service", "counselling"),
        ] + [
            _row(i, f"https://x{i}.com/", "other", "media") for i in range(3, 11)
        ]
        result = compute_serp_intent(
            organic_rows=rows, has_local_pack=False, mapping=real_mapping
        )
        assert result["confidence"] == "low"
        # n=2 < 5 → primary_intent is None
        assert result["primary_intent"] is None

    def test_client_urls_informational_primary(self, real_mapping):
        # 1 client URL + 9 informational guides → primary informational
        # client URL → navigational (1 count), guides → informational (9 counts)
        # classified = 10, organic = 10 → high confidence
        # 9/10 informational = 0.9 share → primary = informational
        rows = [
            _row(1, "https://livingsystems.ca/about", "service", "counselling"),
        ] + [
            _row(i, f"https://g{i}.com/", "guide", "media") for i in range(2, 11)
        ]
        result = compute_serp_intent(
            organic_rows=rows,
            has_local_pack=False,
            client_domain="livingsystems.ca",
            mapping=real_mapping,
        )
        assert result["primary_intent"] == "informational"
        assert result["confidence"] == "high"
        assert result["intent_distribution"]["informational"] == 9

    def test_branded_serp_dominated_by_client(self, real_mapping):
        rows = [
            _row(i, f"https://livingsystems.ca/p{i}", "guide", "counselling")
            for i in range(1, 8)
        ] + [
            _row(i, f"https://psychologytoday.com/p{i}", "directory", "directory")
            for i in range(8, 11)
        ]
        result = compute_serp_intent(
            organic_rows=rows,
            has_local_pack=False,
            client_domain="livingsystems.ca",
            mapping=real_mapping,
        )
        assert result["primary_intent"] == "navigational"
        assert result["is_mixed"] is False

    def test_evidence_new_field_names(self, real_mapping):
        # Fix 1: verify new field names are present; old names are absent
        rows = [
            _row(1, "https://a.com/", "guide", "media"),
            _row(2, "https://b.com/", "service", "counselling"),
            _row(3, "https://c.com/", "other", "media"),
        ]
        result = compute_serp_intent(
            organic_rows=rows, has_local_pack=False, mapping=real_mapping
        )
        ev = result["evidence"]
        # New names present
        assert "organic_url_count" in ev
        assert "classified_organic_url_count" in ev
        assert "uncategorised_organic_url_count" in ev
        assert "local_pack_present" in ev
        assert "local_pack_member_count" in ev
        # Old names absent
        assert "total_url_count" not in ev
        assert "classified_url_count" not in ev
        assert "uncategorised_count" not in ev
        # Fix 2: intent_counts removed
        assert "intent_counts" not in ev

    def test_evidence_counts_sum_to_organic_url_count(self, real_mapping):
        rows = [
            _row(1, "https://a.com/", "guide", "media"),
            _row(2, "https://b.com/", "service", "counselling"),
            _row(3, "https://c.com/", "other", "media"),
        ]
        result = compute_serp_intent(
            organic_rows=rows, has_local_pack=False, mapping=real_mapping
        )
        ev = result["evidence"]
        assert ev["organic_url_count"] == 3
        assert (ev["classified_organic_url_count"] + ev["uncategorised_organic_url_count"]
                == ev["organic_url_count"])

    def test_distribution_excludes_uncategorised_and_is_integer(self, real_mapping):
        rows = [
            _row(1, "https://a.com/", "guide", "media"),
            _row(2, "https://b.com/", "other", "media"),
            _row(3, "https://c.com/", "other", "media"),
            _row(4, "https://d.com/", "other", "media"),
            _row(5, "https://e.com/", "other", "media"),
        ]
        result = compute_serp_intent(
            organic_rows=rows, has_local_pack=False, mapping=real_mapping
        )
        dist = result["intent_distribution"]
        # uncategorised must not appear in distribution
        assert "uncategorised" not in dist
        # Values are integers (Fix 2)
        assert dist["informational"] == 1
        assert isinstance(dist["informational"], int)

    def test_local_pack_member_count_passed_through(self, real_mapping):
        result = compute_serp_intent(
            organic_rows=[],
            has_local_pack=True,
            local_pack_member_count=3,
            mapping=real_mapping,
        )
        assert result["evidence"]["local_pack_member_count"] == 3
        assert result["evidence"]["local_pack_present"] is True


# ─── Threshold customisation ─────────────────────────────────────────────────


class TestThresholdOverrides:
    def test_custom_thresholds_change_primary_decision(self, real_mapping):
        rows = [
            _row(i, f"https://g{i}.com/", "guide", "media") for i in range(1, 6)
        ] + [
            _row(i, f"https://s{i}.ca/", "service", "counselling") for i in range(6, 11)
        ]
        strict = compute_serp_intent(
            rows, has_local_pack=False, mapping=real_mapping,
            thresholds={"primary_share": 0.7, "fallback_share": 0.7,
                        "fallback_runner_up_max": 0.0},
        )
        assert strict["is_mixed"] is True
        assert strict["primary_intent"] == "mixed"
        assert "mixed_components" in strict

        loose = compute_serp_intent(
            rows, has_local_pack=False, mapping=real_mapping,
            thresholds={"primary_share": 0.5, "fallback_share": 0.5,
                        "fallback_runner_up_max": 0.5},
        )
        assert loose["is_mixed"] is False
