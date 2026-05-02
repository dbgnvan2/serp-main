"""
Tests for config_validators module.

Purpose: Verify that all configuration validators are correctly implemented and return
proper validation results (is_valid, errors, warnings) for both valid and invalid inputs.

Spec: serp_tool1_improvements_spec.md#phase-1
Tests: tests/test_config_validators.py
"""

import pytest
import yaml
import json
import tempfile
import os
from config_validators import (
    validate_intent_mapping,
    validate_strategic_patterns,
    validate_brief_pattern_routing,
    validate_intent_classifier_triggers,
    validate_config_yml,
    validate_domain_overrides,
    validate_classification_rules,
    validate_url_pattern_rules,
    validate_cross_file_constraints,
    VALID_INTENTS,
    VALID_CONTENT_TYPES,
    VALID_ENTITY_TYPES,
)


class TestValidateIntentMapping:
    """Test intent_mapping.yml validator."""

    def test_valid_intent_mapping(self):
        """Valid intent mapping should pass validation."""
        data = {
            "version": 1,
            "rules": [
                {
                    "match": {
                        "content_type": "guide",
                        "entity_type": "counselling",
                        "local_pack": "no",
                        "domain_role": "client"
                    },
                    "intent": "informational"
                }
            ]
        }
        is_valid, errors, warnings = validate_intent_mapping(data)
        assert is_valid is True, f"Validation failed: {errors}"
        assert len(errors) == 0

    def test_invalid_intent_value(self):
        """Invalid intent value should fail validation."""
        data = {
            "version": 1,
            "rules": [
                {
                    "match": {
                        "content_type": "guide",
                        "entity_type": "counselling",
                        "local_pack": "no",
                        "domain_role": "client"
                    },
                    "intent": "invalid_intent"
                }
            ]
        }
        is_valid, errors, warnings = validate_intent_mapping(data)
        assert is_valid is False
        assert len(errors) > 0

    def test_missing_required_match_fields(self):
        """Missing required match fields should fail validation."""
        data = {
            "version": 1,
            "rules": [
                {
                    "match": {
                        "content_type": "guide",
                        # Missing entity_type, local_pack, domain_role
                    },
                    "intent": "informational"
                }
            ]
        }
        is_valid, errors, warnings = validate_intent_mapping(data)
        assert is_valid is False
        assert len(errors) > 0

    def test_wildcard_values_allowed(self):
        """Wildcard 'any' values should be allowed in match fields."""
        data = {
            "version": 1,
            "rules": [
                {
                    "match": {
                        "content_type": "any",
                        "entity_type": "any",
                        "local_pack": "any",
                        "domain_role": "any"
                    },
                    "intent": "informational"
                }
            ]
        }
        is_valid, errors, warnings = validate_intent_mapping(data)
        assert is_valid is True, f"Validation failed: {errors}"
        assert len(errors) == 0

    def test_empty_rules_list(self):
        """Empty rules list should fail validation."""
        data = {
            "version": 1,
            "rules": []
        }
        is_valid, errors, warnings = validate_intent_mapping(data)
        assert is_valid is False


class TestValidateDomainOverrides:
    """Test domain_overrides.yml validator."""

    def test_valid_domain_overrides(self):
        """Valid domain overrides should pass validation."""
        data = {
            "example.com": "counselling",
            "psychologytoday.com": "directory"
        }
        is_valid, errors, warnings = validate_domain_overrides(data)
        assert is_valid is True
        assert len(errors) == 0

    def test_empty_domain_overrides(self):
        """Empty domain overrides is valid (but could warn)."""
        data = {}
        is_valid, errors, warnings = validate_domain_overrides(data)
        # Empty dict is valid but might warn
        assert is_valid is True

    def test_invalid_entity_type(self):
        """Invalid entity type should fail validation."""
        data = {
            "example.com": "invalid_type"
        }
        is_valid, errors, warnings = validate_domain_overrides(data)
        assert is_valid is False
        assert len(errors) > 0


class TestValidateClassificationRules:
    """Test classification_rules.json validator."""

    def test_valid_classification_rules(self):
        """Valid classification rules should pass validation."""
        data = {
            "content_types": ["article", "product", "directory"],
            "entity_types": ["counselling", "legal", "nonprofit"],
            "entity_type_descriptions": {
                "counselling": "Counselling and therapy services",
                "legal": "Legal services"
            }
        }
        is_valid, errors, warnings = validate_classification_rules(data)
        assert is_valid is True

    def test_missing_entity_types_section(self):
        """Missing entity_types section should fail validation."""
        data = {
            "content_types": ["article"],
            # Missing entity_types
        }
        is_valid, errors, warnings = validate_classification_rules(data)
        assert is_valid is False


class TestValidateConfigYml:
    """Test config.yml validator."""

    def test_valid_config(self):
        """Valid config.yml should pass validation."""
        data = {
            "version": "2.0",
            "serpapi": {
                "engine": "google",
                "gl": "ca"
            },
            "files": {
                "output_folder": "output"
            }
        }
        is_valid, errors, warnings = validate_config_yml(data)
        assert is_valid is True

    def test_empty_config(self):
        """Empty config might be valid or warn depending on implementation."""
        data = {}
        is_valid, errors, warnings = validate_config_yml(data)
        # This depends on whether empty config is acceptable
        # For now, it should at least not crash
        assert isinstance(is_valid, bool)


class TestValidateStrategicPatterns:
    """Test strategic_patterns.yml validator."""

    def test_valid_strategic_patterns(self):
        """Valid strategic patterns should pass validation."""
        data = [
            {
                "Pattern_Name": "example_pattern",
                "Triggers": ["trigger1", "trigger2"],
                "Status_Quo_Message": "Message",
                "Bowen_Bridge_Reframe": "Reframe",
                "Content_Angle": "Angle"
            }
        ]
        is_valid, errors, warnings = validate_strategic_patterns(data)
        assert is_valid is True, f"Validation failed: {errors}"

    def test_pattern_missing_required_fields(self):
        """Pattern missing required fields should fail."""
        data = [
            {
                "Pattern_Name": "example_pattern",
                # Missing Triggers, Status_Quo_Message, etc.
            }
        ]
        is_valid, errors, warnings = validate_strategic_patterns(data)
        assert is_valid is False


class TestValidateBriefPatternRouting:
    """Test brief_pattern_routing.yml validator."""

    def test_valid_brief_pattern_routing(self):
        """Valid brief pattern routing should pass validation."""
        data = {
            "version": 1,
            "patterns": [
                {
                    "pattern_name": "example_pattern",
                    "paa_themes": ["theme1"],
                    "paa_categories": ["category1"],
                    "keyword_hints": ["hint1"],
                    "intent_slot_descriptions": {}
                }
            ]
        }
        is_valid, errors, warnings = validate_brief_pattern_routing(data)
        assert is_valid is True, f"Validation failed: {errors}"


class TestValidateIntentClassifierTriggers:
    """Test intent_classifier_triggers.yml validator."""

    def test_valid_triggers(self):
        """Valid intent classifier triggers should pass validation."""
        data = {
            "version": 1,
            "medical_triggers": {
                "multi_word": ["trigger phrase", "another phrase"],
                "single_word": ["trigger", "word"]
            },
            "systemic_triggers": {
                "multi_word": ["systemic phrase"],
                "single_word": ["systemic"]
            }
        }
        is_valid, errors, warnings = validate_intent_classifier_triggers(data)
        assert is_valid is True, f"Validation failed: {errors}"


class TestValidateUrlPatternRules:
    """Test url_pattern_rules.yml validator."""

    def test_valid_url_pattern_rules(self):
        """Valid URL pattern rules should pass validation."""
        data = [
            {
                "pattern": ".*\\.com$",
                "content_type": "guide",
                "entity_types": ["counselling"]
            }
        ]
        is_valid, errors, warnings = validate_url_pattern_rules(data)
        assert is_valid is True, f"Validation failed: {errors}"


class TestValidateCrossFileConstraints:
    """Test cross-file constraint validation."""

    def test_valid_cross_file_constraints(self):
        """Valid cross-file references should pass validation."""
        intent_mapping = {
            "version": 1,
            "rules": [
                {
                    "match": {
                        "content_type": "guide",
                        "entity_type": "counselling",
                        "local_pack": "no",
                        "domain_role": "client"
                    },
                    "intent": "informational"
                }
            ]
        }
        strategic_patterns = {
            "patterns": [
                {
                    "Pattern_Name": "example_pattern",
                    "Triggers": ["trigger"],
                    "Status_Quo_Message": "Message",
                    "Bowen_Bridge_Reframe": "Reframe",
                    "Content_Angle": "Angle"
                }
            ]
        }
        brief_pattern_routing = {
            "version": 1,
            "patterns": [
                {
                    "pattern_name": "example_pattern",
                    "paa_themes": ["theme1"],
                    "paa_categories": ["category1"],
                    "keyword_hints": ["hint1"],
                    "intent_slot_descriptions": {}
                }
            ]
        }
        domain_overrides = {
            "example.com": "counselling"
        }
        classification_rules = {
            "content_types": ["article"],
            "entity_types": ["counselling"],
            "entity_type_descriptions": {}
        }

        is_valid, errors, warnings = validate_cross_file_constraints(
            intent_mapping=intent_mapping,
            strategic_patterns=strategic_patterns,
            brief_pattern_routing=brief_pattern_routing,
            domain_overrides=domain_overrides,
            classification_rules=classification_rules,
        )
        assert is_valid is True, f"Validation failed: {errors}"


class TestValidatorReturnSignature:
    """Test that all validators return correct tuple signature."""

    @pytest.mark.parametrize("validator_func", [
        validate_intent_mapping,
        validate_strategic_patterns,
        validate_brief_pattern_routing,
        validate_intent_classifier_triggers,
        validate_config_yml,
        validate_domain_overrides,
        validate_classification_rules,
        validate_url_pattern_rules,
    ])
    def test_validator_return_signature(self, validator_func):
        """All validators should return (is_valid, errors, warnings) tuple."""
        # Test with empty dict
        result = validator_func({})
        assert isinstance(result, tuple)
        assert len(result) == 3
        is_valid, errors, warnings = result
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)
        assert isinstance(warnings, list)
