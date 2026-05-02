"""
Tests for config_manager module.

Purpose: Verify that the Configuration Manager window initializes correctly and tabs
are properly created with correct file associations.

Spec: serp_tool1_improvements_spec.md#phase-1
Tests: tests/test_config_manager.py
"""

import pytest

try:
    import tkinter as tk
    from tkinter import ttk
    TKINTER_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    TKINTER_AVAILABLE = False

# Non-GUI tests can run without tkinter
from config_manager import (
    ConfigManagerWindow,
    BaseConfigTab,
    DomainOverridesTab,
    ClassificationRulesTab,
    IntentMappingTab,
    StrategicPatternsTab,
    BriefPatternRoutingTab,
    IntentClassifierTriggersTab,
    ConfigSettingsTab,
    UrlPatternRulesTab,
    VALIDATORS_BY_FILE,
    HELP_BY_FILE,
    HELP_BY_FIELD,
)


@pytest.mark.skipif(not TKINTER_AVAILABLE, reason="tkinter not available")
class TestConfigManagerWindowCreation:
    """Test ConfigManagerWindow initialization."""

    def test_window_creates_without_error(self):
        """ConfigManagerWindow should create without raising exceptions."""
        root = tk.Tk()
        try:
            window = ConfigManagerWindow(root)
            assert window.window is not None
            assert window.window.winfo_exists()
            window.window.destroy()
        finally:
            root.destroy()

    def test_window_title_set(self):
        """Window title should be set correctly."""
        root = tk.Tk()
        try:
            window = ConfigManagerWindow(root)
            assert window.window.title() == "Configuration Manager"
            window.window.destroy()
        finally:
            root.destroy()

    def test_tabs_created(self):
        """All 8 tabs should be created."""
        root = tk.Tk()
        try:
            window = ConfigManagerWindow(root)
            assert len(window.tabs) == 8
            window.window.destroy()
        finally:
            root.destroy()


@pytest.mark.skipif(not TKINTER_AVAILABLE, reason="tkinter not available")
class TestBaseConfigTab:
    """Test BaseConfigTab abstract class."""

    def test_domain_overrides_tab_created(self):
        """DomainOverridesTab should create successfully."""
        root = tk.Tk()
        frame = ttk.Frame(root)
        try:
            tab = DomainOverridesTab(frame)
            assert tab.file_name == "domain_overrides.yml"
            assert tab.file_type == "yaml"
            assert tab.current_data is not None
        finally:
            root.destroy()

    def test_classification_rules_tab_created(self):
        """ClassificationRulesTab should create successfully."""
        root = tk.Tk()
        frame = tk.Frame(root)
        try:
            tab = ClassificationRulesTab(frame)
            assert tab.file_name == "classification_rules.json"
            assert tab.file_type == "json"
            assert tab.current_data is not None
        finally:
            root.destroy()

    def test_all_tabs_have_validators(self):
        """All tabs should have corresponding validators in VALIDATORS_BY_FILE."""
        root = tk.Tk()
        frame = tk.Frame(root)
        try:
            tabs = [
                DomainOverridesTab(frame),
                ClassificationRulesTab(frame),
                IntentMappingTab(frame),
                StrategicPatternsTab(frame),
                BriefPatternRoutingTab(frame),
                IntentClassifierTriggersTab(frame),
                ConfigSettingsTab(frame),
                UrlPatternRulesTab(frame),
            ]
            for tab in tabs:
                assert tab.file_name in VALIDATORS_BY_FILE, f"No validator for {tab.file_name}"
        finally:
            root.destroy()


@pytest.mark.skipif(not TKINTER_AVAILABLE, reason="tkinter not available")
class TestTabFileAssociations:
    """Test that tabs are correctly associated with files."""

    @pytest.mark.parametrize("tab_class, expected_file, expected_type", [
        (DomainOverridesTab, "domain_overrides.yml", "yaml"),
        (ClassificationRulesTab, "classification_rules.json", "json"),
        (IntentMappingTab, "intent_mapping.yml", "yaml"),
        (StrategicPatternsTab, "strategic_patterns.yml", "yaml"),
        (BriefPatternRoutingTab, "brief_pattern_routing.yml", "yaml"),
        (IntentClassifierTriggersTab, "intent_classifier_triggers.yml", "yaml"),
        (ConfigSettingsTab, "config.yml", "yaml"),
        (UrlPatternRulesTab, "url_pattern_rules.yml", "yaml"),
    ])
    def test_tab_file_associations(self, tab_class, expected_file, expected_type):
        """Each tab should be associated with correct file and type."""
        root = tk.Tk()
        frame = tk.Frame(root)
        try:
            tab = tab_class(frame)
            assert tab.file_name == expected_file
            assert tab.file_type == expected_type
        finally:
            root.destroy()


class TestHelpRegistry:
    """Test help text registries."""

    def test_all_files_have_help(self):
        """All config files should have help text in HELP_BY_FILE."""
        expected_files = [
            "intent_mapping.yml",
            "strategic_patterns.yml",
            "brief_pattern_routing.yml",
            "intent_classifier_triggers.yml",
            "config.yml",
            "domain_overrides.yml",
            "classification_rules.json",
            "url_pattern_rules.yml",
        ]
        for file_name in expected_files:
            assert file_name in HELP_BY_FILE, f"No help text for {file_name}"
            assert len(HELP_BY_FILE[file_name]) > 0

    def test_help_field_registry_not_empty(self):
        """HELP_BY_FIELD should contain help for fields."""
        assert len(HELP_BY_FIELD) > 0


class TestValidatorRegistry:
    """Test validator registry."""

    def test_all_files_have_validators(self):
        """All config files should have validators in VALIDATORS_BY_FILE."""
        expected_files = [
            "intent_mapping.yml",
            "strategic_patterns.yml",
            "brief_pattern_routing.yml",
            "intent_classifier_triggers.yml",
            "config.yml",
            "domain_overrides.yml",
            "classification_rules.json",
            "url_pattern_rules.yml",
        ]
        for file_name in expected_files:
            assert file_name in VALIDATORS_BY_FILE, f"No validator for {file_name}"
            assert callable(VALIDATORS_BY_FILE[file_name])


@pytest.mark.skipif(not TKINTER_AVAILABLE, reason="tkinter not available")
class TestTabValidation:
    """Test tab validation methods."""

    def test_tab_validate_returns_tuple(self):
        """Tab.validate() should return (is_valid, errors, warnings) tuple."""
        root = tk.Tk()
        frame = tk.Frame(root)
        try:
            tab = DomainOverridesTab(frame)
            result = tab.validate()
            assert isinstance(result, tuple)
            assert len(result) == 3
            is_valid, errors, warnings = result
            assert isinstance(is_valid, bool)
            assert isinstance(errors, list)
            assert isinstance(warnings, list)
        finally:
            root.destroy()

    def test_tab_unsaved_changes_detection(self):
        """Tab.has_unsaved_changes() should detect changes."""
        root = tk.Tk()
        frame = tk.Frame(root)
        try:
            tab = DomainOverridesTab(frame)
            # Initially no changes
            assert not tab.has_unsaved_changes()
        finally:
            root.destroy()


@pytest.mark.skipif(not TKINTER_AVAILABLE, reason="tkinter not available")
class TestTabDataLoading:
    """Test that tabs load data from disk."""

    def test_tab_loads_data_from_disk(self):
        """Tabs should load current data from disk on initialization."""
        root = tk.Tk()
        frame = tk.Frame(root)
        try:
            tab = DomainOverridesTab(frame)
            # current_data should be loaded
            assert tab.current_data is not None
            assert isinstance(tab.current_data, (dict, list))
        finally:
            root.destroy()

    def test_tab_get_edited_data_returns_data(self):
        """Tab.get_edited_data() should return data structure."""
        root = tk.Tk()
        frame = tk.Frame(root)
        try:
            tab = DomainOverridesTab(frame)
            data = tab.get_edited_data()
            assert data is not None
        finally:
            root.destroy()
