import os
import json
import yaml
import threading
from datetime import datetime
from abc import ABC, abstractmethod
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog, scrolledtext, Text
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False
    # Provide dummy classes for testing without tkinter
    class tk:
        pass
    class ttk:
        class Frame:
            pass
    class messagebox:
        pass

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


# Registry: file_path -> (validator_func, data_loader, data_dumper)
VALIDATORS_BY_FILE = {
    "intent_mapping.yml": validate_intent_mapping,
    "strategic_patterns.yml": validate_strategic_patterns,
    "brief_pattern_routing.yml": validate_brief_pattern_routing,
    "intent_classifier_triggers.yml": validate_intent_classifier_triggers,
    "config.yml": validate_config_yml,
    "domain_overrides.yml": validate_domain_overrides,
    "classification_rules.json": validate_classification_rules,
    "url_pattern_rules.yml": validate_url_pattern_rules,
}

# Help text registry
HELP_BY_FILE = {
    "intent_mapping.yml": (
        "Maps SERP characteristics to intent verdicts. Rules are evaluated top-to-bottom "
        "(first-match-wins); order matters. Edit rules here to refine intent classification."
    ),
    "strategic_patterns.yml": (
        "Bowen Family Systems patterns used for content brief generation. Each pattern includes "
        "triggers, status quo message, and reframe. Pattern names must match brief_pattern_routing.yml."
    ),
    "brief_pattern_routing.yml": (
        "Routes content briefs to specific patterns and keyword themes. Pattern names must exist "
        "in strategic_patterns.yml. Edit this to customize which patterns appear in briefs."
    ),
    "intent_classifier_triggers.yml": (
        "PAA External Locus and Systemic vocabulary lists. Used to classify PAA questions. "
        "Add trigger words to improve classification accuracy."
    ),
    "config.yml": (
        "Operational settings for SerpAPI, file paths, thresholds, and enrichment options. "
        "Edit these to customize tool behavior (API keys, output folders, etc.)."
    ),
    "domain_overrides.yml": (
        "Manual entity-type overrides for specific domains. When a domain is not auto-classified "
        "correctly, add it here to force a specific entity type."
    ),
    "classification_rules.json": (
        "Content types and entity types with their pattern definitions. Entity types used here "
        "must match those referenced in intent_mapping.yml and domain_overrides.yml."
    ),
    "url_pattern_rules.yml": (
        "URL pattern fallbacks for content classification. Used when other classification "
        "methods fail. Patterns are regex; they are evaluated top-to-bottom (first-match-wins)."
    ),
}

HELP_BY_FIELD = {
    "intent_mapping.rules[].intent": (
        "Primary intent category. Options:\n"
        "  - informational: User seeking information (how-to, definitions, research)\n"
        "  - commercial_investigation: Evaluating products/services before purchase\n"
        "  - transactional: Ready to buy/take action\n"
        "  - navigational: Looking for specific website/brand\n"
        "  - local: Geographic/local business search\n"
        "  - uncategorised: Unclassifiable by other rules"
    ),
    "intent_mapping.rules[].match.content_type": (
        "SERP content type to match. Must be one of: "
        + ", ".join(sorted(VALID_CONTENT_TYPES))
    ),
    "intent_mapping.rules[].match.entity_type": (
        "Entity type to match. Must be one of: "
        + ", ".join(sorted(VALID_ENTITY_TYPES)) + ", or 'any' (wildcard)"
    ),
    "strategic_patterns.yml[].Pattern_Name": (
        "Unique pattern identifier. Must match a pattern_name in brief_pattern_routing.yml exactly."
    ),
    "brief_pattern_routing.yml[].pattern_name": (
        "Must match a Pattern_Name from strategic_patterns.yml. Determines which PAA questions and keywords "
        "associate with each content brief."
    ),
    "domain_overrides.yml[].entity_type": (
        "Force a specific entity type for this domain. Must be one of: "
        + ", ".join(sorted(VALID_ENTITY_TYPES))
    ),
}


class BaseConfigTab(ttk.Frame):
    """Abstract base class for all configuration tabs."""

    def __init__(self, parent, file_name: str, file_type: str):
        """
        Args:
            parent: Parent widget
            file_name: Name of config file (e.g., 'intent_mapping.yml')
            file_type: 'yaml' or 'json'
        """
        super().__init__(parent)
        self.file_name = file_name
        self.file_type = file_type
        self.file_path = os.path.join(os.getcwd(), file_name)
        self.current_data = None
        self.edited_data = None
        self.load_current_data()
        self.render_ui()

    def load_current_data(self):
        """Load file from disk. Subclasses should override if custom loading needed."""
        if not os.path.exists(self.file_path):
            self.current_data = {} if self.file_type == "json" else {}
            return

        try:
            if self.file_type == "yaml":
                with open(self.file_path, "r") as f:
                    self.current_data = yaml.safe_load(f) or {}
            else:  # json
                with open(self.file_path, "r") as f:
                    self.current_data = json.load(f)
        except Exception as e:
            self.current_data = {} if self.file_type == "json" else {}
            print(f"Error loading {self.file_name}: {e}")

    def render_ui(self):
        """Render tab UI. Must be implemented by subclasses."""
        # Default: show placeholder
        placeholder = ttk.Label(
            self,
            text=f"Tab UI for {self.file_name}\n(Placeholder for Phase 1)",
            foreground="gray"
        )
        placeholder.pack(padx=20, pady=20)

    def get_edited_data(self):
        """Extract current form values into a data structure."""
        return self.current_data

    def validate(self):
        """Validate file-specific constraints. Return (is_valid, errors, warnings)."""
        validator = VALIDATORS_BY_FILE.get(self.file_name)
        if not validator:
            return (True, [], [])

        data = self.get_edited_data()
        is_valid, errors, warnings = validator(data)
        return (is_valid, errors, warnings)

    def revert_to_disk(self):
        """Reload from disk, discard unsaved changes."""
        self.load_current_data()
        self.render_ui()

    def save_to_disk(self):
        """Validate, then write to disk. Return (success, message)."""
        is_valid, errors, warnings = self.validate()

        if not is_valid:
            return (False, f"Validation failed for {self.file_name}:\n" + "\n".join(errors))

        try:
            data = self.get_edited_data()
            if self.file_type == "yaml":
                with open(self.file_path, "w") as f:
                    yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
            else:  # json
                with open(self.file_path, "w") as f:
                    json.dump(data, f, indent=2)

            self.current_data = data
            return (True, f"Saved {self.file_name}")
        except Exception as e:
            return (False, f"Failed to save {self.file_name}: {e}")

    def has_unsaved_changes(self):
        """Check if current data differs from disk version."""
        return self.get_edited_data() != self.current_data


class DomainOverridesTab(BaseConfigTab):
    """Tab for domain_overrides.yml."""

    def __init__(self, parent):
        super().__init__(parent, "domain_overrides.yml", "yaml")

    def render_ui(self):
        """Placeholder UI for Phase 1."""
        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(
            frame,
            text="Domain Overrides Configuration",
            font=("Helvetica", 12, "bold")
        ).pack(anchor="w")

        help_text = HELP_BY_FILE.get("domain_overrides.yml", "")
        ttk.Label(frame, text=help_text, wraplength=600, justify="left").pack(anchor="w", pady=(5, 15))

        ttk.Label(frame, text="Phase 1: Placeholder", foreground="gray").pack(anchor="w")


class ClassificationRulesTab(BaseConfigTab):
    """Tab for classification_rules.json."""

    def __init__(self, parent):
        super().__init__(parent, "classification_rules.json", "json")

    def render_ui(self):
        """Placeholder UI for Phase 1."""
        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(
            frame,
            text="Classification Rules Configuration",
            font=("Helvetica", 12, "bold")
        ).pack(anchor="w")

        help_text = HELP_BY_FILE.get("classification_rules.json", "")
        ttk.Label(frame, text=help_text, wraplength=600, justify="left").pack(anchor="w", pady=(5, 15))

        ttk.Label(frame, text="Phase 1: Placeholder", foreground="gray").pack(anchor="w")


class IntentMappingTab(BaseConfigTab):
    """Tab for intent_mapping.yml."""

    def __init__(self, parent):
        super().__init__(parent, "intent_mapping.yml", "yaml")

    def render_ui(self):
        """Placeholder UI for Phase 1."""
        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(
            frame,
            text="Intent Mapping Configuration",
            font=("Helvetica", 12, "bold")
        ).pack(anchor="w")

        help_text = HELP_BY_FILE.get("intent_mapping.yml", "")
        ttk.Label(frame, text=help_text, wraplength=600, justify="left").pack(anchor="w", pady=(5, 15))

        ttk.Label(frame, text="Phase 1: Placeholder", foreground="gray").pack(anchor="w")


class StrategicPatternsTab(BaseConfigTab):
    """Tab for strategic_patterns.yml."""

    def __init__(self, parent):
        super().__init__(parent, "strategic_patterns.yml", "yaml")

    def render_ui(self):
        """Placeholder UI for Phase 1."""
        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(
            frame,
            text="Strategic Patterns Configuration",
            font=("Helvetica", 12, "bold")
        ).pack(anchor="w")

        help_text = HELP_BY_FILE.get("strategic_patterns.yml", "")
        ttk.Label(frame, text=help_text, wraplength=600, justify="left").pack(anchor="w", pady=(5, 15))

        ttk.Label(frame, text="Phase 1: Placeholder", foreground="gray").pack(anchor="w")


class BriefPatternRoutingTab(BaseConfigTab):
    """Tab for brief_pattern_routing.yml."""

    def __init__(self, parent):
        super().__init__(parent, "brief_pattern_routing.yml", "yaml")

    def render_ui(self):
        """Placeholder UI for Phase 1."""
        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(
            frame,
            text="Brief Pattern Routing Configuration",
            font=("Helvetica", 12, "bold")
        ).pack(anchor="w")

        help_text = HELP_BY_FILE.get("brief_pattern_routing.yml", "")
        ttk.Label(frame, text=help_text, wraplength=600, justify="left").pack(anchor="w", pady=(5, 15))

        ttk.Label(frame, text="Phase 1: Placeholder", foreground="gray").pack(anchor="w")


class IntentClassifierTriggersTab(BaseConfigTab):
    """Tab for intent_classifier_triggers.yml."""

    def __init__(self, parent):
        super().__init__(parent, "intent_classifier_triggers.yml", "yaml")

    def render_ui(self):
        """Placeholder UI for Phase 1."""
        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(
            frame,
            text="Intent Classifier Triggers Configuration",
            font=("Helvetica", 12, "bold")
        ).pack(anchor="w")

        help_text = HELP_BY_FILE.get("intent_classifier_triggers.yml", "")
        ttk.Label(frame, text=help_text, wraplength=600, justify="left").pack(anchor="w", pady=(5, 15))

        ttk.Label(frame, text="Phase 1: Placeholder", foreground="gray").pack(anchor="w")


class ConfigSettingsTab(BaseConfigTab):
    """Tab for config.yml."""

    def __init__(self, parent):
        super().__init__(parent, "config.yml", "yaml")

    def render_ui(self):
        """Placeholder UI for Phase 1."""
        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(
            frame,
            text="Configuration Settings",
            font=("Helvetica", 12, "bold")
        ).pack(anchor="w")

        help_text = HELP_BY_FILE.get("config.yml", "")
        ttk.Label(frame, text=help_text, wraplength=600, justify="left").pack(anchor="w", pady=(5, 15))

        ttk.Label(frame, text="Phase 1: Placeholder", foreground="gray").pack(anchor="w")


class UrlPatternRulesTab(BaseConfigTab):
    """Tab for url_pattern_rules.yml."""

    def __init__(self, parent):
        super().__init__(parent, "url_pattern_rules.yml", "yaml")

    def render_ui(self):
        """Placeholder UI for Phase 1."""
        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(
            frame,
            text="URL Pattern Rules Configuration",
            font=("Helvetica", 12, "bold")
        ).pack(anchor="w")

        help_text = HELP_BY_FILE.get("url_pattern_rules.yml", "")
        ttk.Label(frame, text=help_text, wraplength=600, justify="left").pack(anchor="w", pady=(5, 15))

        ttk.Label(frame, text="Phase 1: Placeholder", foreground="gray").pack(anchor="w")


class ConfigManagerWindow:
    """Main Configuration Manager window with tabbed interface."""

    def __init__(self, root, log_func=None):
        """
        Args:
            root: Parent Tkinter window
            log_func: Optional function to log messages to main window
        """
        self.root = root
        self.log = log_func or (lambda msg: print(msg))
        self.window = tk.Toplevel(root)
        self.window.title("Configuration Manager")
        self.window.geometry("1000x700")
        self.window.transient(root)

        # Header
        header_frame = ttk.Frame(self.window)
        header_frame.pack(fill="x", padx=15, pady=15)

        ttk.Label(
            header_frame,
            text="Configuration Manager",
            font=("Helvetica", 14, "bold")
        ).pack(anchor="w")

        ttk.Label(
            header_frame,
            text="Edit editorial configuration files (YAML/JSON) with validation and help guidance.",
            foreground="gray"
        ).pack(anchor="w")

        # Tabbed interface
        notebook = ttk.Notebook(self.window)
        notebook.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        self.tabs = [
            DomainOverridesTab(notebook),
            ClassificationRulesTab(notebook),
            IntentMappingTab(notebook),
            StrategicPatternsTab(notebook),
            BriefPatternRoutingTab(notebook),
            IntentClassifierTriggersTab(notebook),
            ConfigSettingsTab(notebook),
            UrlPatternRulesTab(notebook),
        ]

        # Add tabs to notebook
        for tab in self.tabs:
            notebook.add(tab, text=tab.file_name)

        # Footer buttons
        footer_frame = ttk.Frame(self.window)
        footer_frame.pack(fill="x", padx=15, pady=(0, 15))

        ttk.Button(
            footer_frame,
            text="Validate All",
            command=self.validate_all
        ).pack(side="left", padx=(0, 10))

        ttk.Button(
            footer_frame,
            text="Save All",
            command=self.save_all
        ).pack(side="left", padx=(0, 10))

        ttk.Button(
            footer_frame,
            text="Discard Changes",
            command=self.discard_changes
        ).pack(side="left", padx=(0, 10))

        ttk.Button(
            footer_frame,
            text="Close",
            command=self.close_window
        ).pack(side="left")

        self.log("[Config Manager] Window opened\n")

    def validate_all(self):
        """Validate all tabs."""
        all_valid = True
        errors_by_file = {}

        for tab in self.tabs:
            is_valid, errors, warnings = tab.validate()
            if not is_valid:
                all_valid = False
                errors_by_file[tab.file_name] = errors

        if all_valid:
            messagebox.showinfo("Validation", "All configuration files are valid.")
            self.log("[Config Manager] All files validated successfully\n")
        else:
            error_msg = "Validation failed:\n\n"
            for file_name, errors in errors_by_file.items():
                error_msg += f"{file_name}:\n"
                for error in errors:
                    error_msg += f"  - {error}\n"
            messagebox.showerror("Validation Failed", error_msg)
            self.log("[Config Manager] Validation failed\n")

    def save_all(self):
        """Save all tabs to disk."""
        self.validate_all()

        for tab in self.tabs:
            success, message = tab.save_to_disk()
            if not success:
                messagebox.showerror("Save Failed", message)
                self.log(f"[Config Manager] Save failed: {message}\n")
                return

        messagebox.showinfo("Success", f"Saved {len(self.tabs)} configuration files.")
        self.log("[Config Manager] All files saved successfully\n")

    def discard_changes(self):
        """Discard unsaved changes and revert to disk."""
        has_changes = any(tab.has_unsaved_changes() for tab in self.tabs)
        if not has_changes:
            messagebox.showinfo("Discard", "No unsaved changes to discard.")
            return

        confirm = messagebox.askyesno(
            "Discard Changes",
            "Discard all unsaved changes and reload from disk?"
        )
        if confirm:
            for tab in self.tabs:
                tab.revert_to_disk()
            messagebox.showinfo("Success", "All changes discarded.")
            self.log("[Config Manager] Changes discarded, data reloaded from disk\n")

    def close_window(self):
        """Close the configuration manager window."""
        has_changes = any(tab.has_unsaved_changes() for tab in self.tabs)
        if has_changes:
            confirm = messagebox.askyesnocancel(
                "Unsaved Changes",
                "You have unsaved changes. Save before closing?"
            )
            if confirm is None:
                return  # Cancel
            elif confirm:
                self.save_all()

        self.window.destroy()
        self.log("[Config Manager] Window closed\n")
