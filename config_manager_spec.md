# Configuration Manager GUI Specification

**Status of this document:** Implementation spec for Configuration Manager feature  
**Date:** 2026-05-02  
**Audience:** Development agent or engineer implementing this feature  
**Scope:** Tool 1 (serp-discover) only

---

## Problem Statement

Users must currently edit 9 editorial configuration files directly in a text editor:
- intent_mapping.yml
- strategic_patterns.yml
- brief_pattern_routing.yml
- intent_classifier_triggers.yml
- config.yml
- domain_overrides.yml
- classification_rules.json
- url_pattern_rules.yml
- clinical_dictionary.json (does not exist yet)

**Pain points:**
1. No validation → typos break reports silently
2. No schema guidance → users don't know what fields are required
3. No help/documentation → users must read YAML comments or docs
4. Error-prone → easy to introduce cross-file reference breaks
5. Not integrated in GUI → requires text editor workflow

**Risk hierarchy (user priority):**
1. **Bad reports** (misleading analysis) — CRITICAL
2. **Crashed reports** (missing fields, type errors) — SECONDARY
3. **User friction** (complexity, integration) — TERTIARY

---

## Solution: Configuration Manager GUI

A new Tkinter window integrated into `serp-me.py` that allows users to:
- **View, edit, add, delete, reorder** entries in all 9 config files
- **See contextual help** for every field
- **Validate before saving** (schema + cross-file constraints)
- **Do everything in the GUI** (no text editor required)

### User Workflow

```
User opens serp-me.py launcher
  → Clicks "Edit Configuration" button
    → ConfigManagerWindow opens with 8 tabs
      → User clicks "intent_mapping" tab
        → Sees table of current rules
          → Double-clicks a rule to edit
            → Edit dialog opens with nested form
              → User changes value, saves
                → Dialog validates, closes
                  → Table updates
                    → User clicks "Save All" at bottom
                      → All tabs validate
                      → Files backup
                      → Files write to disk
                      → Confirmation: "Configuration saved"
```

---

## Design Specification

### Architecture

```
┌─ serp-me.py (existing launcher)
│  └─ New Button: "Edit Configuration"
│     └─ Calls: self.open_config_manager()
│        └─ Opens: ConfigManagerWindow (Toplevel)
│           ├─ ttk.Notebook (tabbed interface)
│           │  ├─ Tab 1: IntentMappingTab (Treeview + edit dialogs)
│           │  ├─ Tab 2: StrategicPatternsTab (Treeview + edit dialogs)
│           │  ├─ Tab 3: BriefPatternRoutingTab (Treeview + edit dialogs)
│           │  ├─ Tab 4: IntentClassifierTriggersTab (Two lists)
│           │  ├─ Tab 5: ConfigSettingsTab (Nested forms)
│           │  ├─ Tab 6: DomainOverridesTab (Flat Treeview)
│           │  ├─ Tab 7: ClassificationRulesTab (Dual sections)
│           │  └─ Tab 8: UrlPatternRulesTab (Treeview + edit dialogs)
│           └─ Footer buttons
│              ├─ [Validate All]
│              ├─ [Save All] — Backup → Validate → Write → Reload
│              ├─ [Cancel] — Discard unsaved changes (with prompt)
│              └─ [Help] — Open user guide
```

### New Files to Create

**1. `config_manager.py` (1500-2000 lines)**
- **ConfigManagerWindow** class
  - Entry point: manages window lifecycle
  - Orchestrates all tabs (load, validate, save)
  - Footer buttons: Validate All, Save All, Cancel, Help
  - Backup/restore logic
  - Progress dialog during save
  - Validation error report dialog

- **BaseConfigTab** abstract class (reusable for all tabs)
  ```python
  class BaseConfigTab(ttk.Frame):
      def load_current_data(self): → dict | list
      def render_ui(self): → None  # Override in subclasses
      def get_edited_data(self): → dict | list
      def validate(self): → (bool, list[str])
      def revert_to_disk(self): → None
      def save_to_disk(self): → (bool, str)
      def has_unsaved_changes(self): → bool
  ```

- **Tab implementations** (8 classes, each extends BaseConfigTab)
  - IntentMappingTab
  - StrategicPatternsTab
  - BriefPatternRoutingTab
  - IntentClassifierTriggersTab
  - ConfigSettingsTab
  - DomainOverridesTab
  - ClassificationRulesTab
  - UrlPatternRulesTab

- **UI Helper functions**
  - `create_treeview_list()` — Reusable Treeview builder for list-of-dicts
  - `create_edit_dialog()` — Reusable dialog for editing nested structures
  - `create_field_with_help()` — Field + help button
  - `create_collapsible_section()` — LabelFrame with expand/collapse
  - `backup_files()` → list[Path]
  - `restore_files(backup_paths)`

- **Constants**
  - `HELP_BY_FILE` dict — File-level help text
  - `HELP_BY_FIELD` dict — Field-level help text
  - `VALIDATORS_BY_FILE` dict — File → validator function mapping

**2. `config_validators.py` (800-1200 lines)**

Centralize all validation logic (extracted from existing code):

- `validate_intent_mapping(data) → (bool, [errors], [warnings])`
- `validate_strategic_patterns(data) → (bool, [errors], [warnings])`
- `validate_brief_pattern_routing(data) → (bool, [errors], [warnings])`
- `validate_intent_classifier_triggers(data) → (bool, [errors], [warnings])`
- `validate_config_yml(data) → (bool, [errors], [warnings])`
- `validate_domain_overrides(data) → (bool, [errors], [warnings])`
- `validate_classification_rules(data) → (bool, [errors], [warnings])`
- `validate_url_pattern_rules(data) → (bool, [errors], [warnings])`
- `validate_cross_file_constraints(intent_mapping, strategic_patterns, brief_pattern_routing, domain_overrides, classification_rules) → (bool, [errors])`

Each validator:
- Takes the in-memory data structure (dict or list)
- Returns tuple: `(is_valid: bool, errors: list[str], warnings: list[str])`
- Errors = schema violations, breaks pipeline, prevent save
- Warnings = non-critical (missing optional fields, deprecated patterns), allow save with confirmation
- Extracted from: `intent_verdict.py`, `pattern_matching.py`, `brief_rendering.py`, `intent_classifier.py`, `classifiers.py`

### Modifications to Existing Files

**`serp-me.py`**
- Line ~20: Add import: `from config_manager import ConfigManagerWindow`
- Line ~290: Add button to control panel:
  ```python
  config_btn = ttk.Button(
      control_frame,
      text="Edit Configuration",
      command=self.open_config_manager,
  )
  config_btn.pack(side="left", padx=5)
  ```
- Add method (lines ~800+):
  ```python
  def open_config_manager(self):
      ConfigManagerWindow(self.root, self.log)
  ```

---

## UI Specification by Tab

### Tab 1: Intent Mapping

**Schema:** List of dicts, order-sensitive (first-match-wins)

**UI:**
```
┌─ Treeview (columns: content_type, entity_type, local_pack, intent, rationale) ─┐
│ content_type │ entity_type   │ local_pack │ intent            │ rationale       │
├──────────────┼───────────────┼────────────┼───────────────────┼─────────────────┤
│ pdf          │ counselling   │ any        │ informational     │ PDFs are guides │
│ service      │ counselling   │ yes        │ local             │ Local services  │
└──────────────┴───────────────┴────────────┴───────────────────┴─────────────────┘

[+ Add New] [↑ Move Up] [↓ Move Down] [Delete] [? Help]

Help text on ?: "Maps SERP characteristics to intent verdicts. Rules evaluated 
first-match-wins; order matters. Edit a rule by double-clicking it."
```

**Interactions:**
- Double-click row → Edit dialog:
  ```
  Edit Intent Mapping Rule
  ┌────────────────────────────────────────┐
  │ content_type: [Dropdown: pdf|service...] │
  │ entity_type: [Dropdown: counselling|...] │
  │ local_pack: [Dropdown: yes|no|any]      │
  │ intent: [Dropdown: informational|...]   │
  │ rationale: [Text field]                 │
  │                                          │
  │ Each field has a (?) help button        │
  │                                          │
  │ [Save] [Cancel]                         │
  └────────────────────────────────────────┘
  ```
- Space: Toggle selection (for bulk operations later)
- Delete: Remove selected row
- ↑/↓: Move row up/down (order matters)
- Add New: Insert blank row at end

**Validation (before save):**
- Each rule has all 4 match keys (content_type, entity_type, local_pack, intent)
- intent value ∈ {informational, commercial_investigation, transactional, navigational, local, uncategorised}
- content_type value ∈ {pdf, directory, news, service, guide, other, unknown, any}
- entity_type value ∈ valid entity types from classification_rules.json
- entity_type values actually used in domain_overrides.yml must exist in intent_mapping rules
- rationale is optional

---

### Tab 2: Strategic Patterns

**Schema:** List of dicts, order not critical

**UI:**
```
┌─ Treeview (columns: Pattern_Name, Triggers, Status) ──────────────────┐
│ Pattern_Name              │ Triggers  │ Status                       │
├──────────────────────────┼───────────┼──────────────────────────────┤
│ The Medical Model Trap   │ 10        │ ✓ All fields present         │
│ The Fusion Trap          │ 5         │ ✓ All fields present         │
│ The Resource Trap        │ 7         │ ✗ Missing Content_Angle      │
└──────────────────────────┴───────────┴──────────────────────────────┘

[+ Add New] [Delete] [? Help]
```

**Interactions:**
- Double-click row → Edit dialog:
  ```
  Edit Strategic Pattern
  ┌──────────────────────────────────────────────────┐
  │ Pattern_Name: [Text field]                       │
  │                                                  │
  │ Triggers: [Treeview of trigger words]           │
  │ ┌────────────────────────┐                       │
  │ │ trigger1               │                       │
  │ │ trigger2               │                       │
  │ │ trigger3               │                       │
  │ └────────────────────────┘                       │
  │ [+ Add Trigger] [Delete Selected]                │
  │                                                  │
  │ Status_Quo_Message: [Text area, multi-line]     │
  │ [Help: explain what this is]                    │
  │                                                  │
  │ Bowen_Bridge_Reframe: [Text area, multi-line]   │
  │ Content_Angle: [Text area, multi-line]          │
  │ Relevant_Intent_Class: [Dropdown: External Locus│Systemic] (optional) │
  │                                                  │
  │ [Save] [Cancel]                                 │
  └──────────────────────────────────────────────────┘
  ```
- Add New: Blank row, prompt for Pattern_Name
- Delete: Remove pattern (warn if referenced by brief_pattern_routing)

**Validation (before save):**
- Pattern_Name unique across all patterns
- Pattern_Name non-empty string
- Triggers list non-empty
- Each trigger: min 4 chars, non-empty after strip
- Status_Quo_Message, Bowen_Bridge_Reframe, Content_Angle all present and non-empty
- Relevant_Intent_Class (if present) ∈ {External Locus, Systemic}
- Cross-file: Pattern_Name must exist in brief_pattern_routing.yml

---

### Tab 3: Brief Pattern Routing

**Schema:** Dict with `patterns` list and `intent_slot_descriptions` dict

**UI:**
```
┌─ Section: Intent Slot Descriptions ──────────────────┐
│ [Expandable] (view/edit descriptions)               │
│ informational: [User seeking information...]        │
│ commercial_investigation: [Evaluating...]           │
│ ... (6 intent types)                                │
└─────────────────────────────────────────────────────┘

┌─ Section: Pattern Routing Rules ──────────────────┐
│ Treeview (columns: pattern_name, paa_themes, paa_categories, keyword_hints) │
├─────────────────────┼──────────┼──────────────┼──────────────┤
│ The Medical Model.. │ 10       │ 1            │ 3            │
│ The Fusion Trap     │ 8        │ 0            │ 4            │
└─────────────────────┴──────────┴──────────────┴──────────────┘

[+ Add New] [Delete] [? Help]
```

**Interactions:**
- Click "Expandable" to show intent_slot_descriptions (edit in place)
- Double-click pattern row → Edit dialog:
  ```
  Edit Brief Pattern Routing
  ┌────────────────────────────────────────────┐
  │ pattern_name: [Dropdown: from strategic..] │
  │                                            │
  │ PAA Themes (phrases in PAA questions):    │
  │ [Treeview of themes]                      │
  │ [+ Add] [Delete]                          │
  │                                            │
  │ PAA Categories (from intent classifier):  │
  │ [Treeview of categories]                  │
  │ [+ Add] [Delete]                          │
  │                                            │
  │ Keyword Hints (in source keyword):        │
  │ [Treeview of hints]                       │
  │ [+ Add] [Delete]                          │
  │                                            │
  │ [Save] [Cancel]                           │
  └────────────────────────────────────────────┘
  ```

**Validation (before save):**
- intent_slot_descriptions must have all 6 intent types as keys
- Each patterns[] entry has pattern_name, paa_themes, paa_categories, keyword_hints
- pattern_name must exist in strategic_patterns.yml
- paa_themes, paa_categories, keyword_hints are lists (can be empty)
- Cross-file: Every pattern_name must match strategic_patterns.yml exactly

---

### Tab 4: Intent Classifier Triggers

**Schema:** Dict with medical_triggers and systemic_triggers, each with multi_word and single_word lists

**UI:**
```
┌─ Section: Medical Triggers ─────────────────────┐
│ Multi-word (phrases): [Treeview]               │
│ ┌──────────────────┐                           │
│ │ mental health    │                           │
│ │ therapy session  │                           │
│ └──────────────────┘                           │
│ [+ Add] [Delete]                               │
│                                                │
│ Single-word (terms): [Treeview]               │
│ ┌──────────────────┐                           │
│ │ therapist        │                           │
│ │ counselor        │                           │
│ └──────────────────┘                           │
│ [+ Add] [Delete]                               │
└────────────────────────────────────────────────┘

┌─ Section: Systemic Triggers ────────────────────┐
│ (Same layout as Medical)                        │
└────────────────────────────────────────────────┘
```

**Interactions:**
- Add: Prompt for new trigger text
- Delete: Remove selected trigger
- Edit inline: Double-click cell to edit text

**Validation (before save):**
- Both medical_triggers and systemic_triggers present
- Both have multi_word and single_word keys
- multi_word and single_word are lists
- Each trigger: min 3 chars, non-empty after strip
- At least one trigger in medical_triggers (union of multi + single)
- At least one trigger in systemic_triggers (union of multi + single)

---

### Tab 5: Config Settings

**Schema:** Nested dict (serpapi, files, enrichment, app, client, analysis_report, serp_intent)

**UI:** Collapsible sections with auto-detected widget types

```
┌─ Section: SerpAPI Settings ┐
│ ▸ [Click to expand/collapse] │
│   engine: [Entry: google]    │
│   gl: [Entry: ca]            │
│   hl: [Entry: en]            │
│   location: [Entry: ...]     │
│   num: [Spinbox: 100]        │
│   device: [Dropdown: desktop|mobile] │
│   google_max_pages: [Spinbox: 5]    │
│   google_max_results: [Spinbox: 100] │
│   retry_max_attempts: [Spinbox: 3]   │
│   retry_backoff_seconds: [Spinbox: 2.0] │
│   request_delay_seconds: [Spinbox: 1.0] │
│   no_cache: [Checkbox]       │
│   ai_fallback_without_location: [Checkbox] │
└──────────────────────────────┘

┌─ Section: Files ┐
│ ▸ [Click to expand/collapse] │
│   input_csv: [Entry + Browse Button] │
│   output_xlsx: [Entry + Browse Button] │
│   output_json: [Entry + Browse Button] │
│   output_md: [Entry + Browse Button] │
│   domain_overrides: [Entry + Browse Button] │
└──────────────────┘

... (enrichment, app, client, analysis_report, serp_intent sections follow same pattern)
```

**Widget auto-detection:**
- str → Entry (text field)
- int → Spinbox (with +/- buttons)
- float → Entry (for numeric input, spinbox with step 0.1)
- bool → Checkbutton
- list → Treeview (e.g., known_brands, preferred_intents)
- dict → Recurse into sub-sections (LabelFrame)
- File paths (files.* keys) → Entry + Browse button (filedialog.askopenfilename)

**Interactions:**
- Click section header to expand/collapse
- Click Browse button to open file dialog
- Spinbox fields: increment/decrement or type directly
- Entry fields: free-form text input
- Checkbutton: toggle on/off
- List fields: Treeview with [+ Add] [Delete] buttons

**Validation (before save):**
- Required keys present in each section
- int/float values in valid ranges (e.g., 0 < timeout < 3600, 0 ≤ threshold ≤ 1)
- File paths (files.*) exist on disk (warn if missing)
- YAML/JSON structurally valid
- Enum values (device, gl, hl) validated against known values

---

### Tab 6: Domain Overrides

**Schema:** Flat key-value pairs (domain → entity_type)

**UI:**
```
┌─ Treeview (columns: domain, entity_type) ─────────────┐
│ Domain                    │ Entity Type               │
├───────────────────────────┼──────────────────────────┤
│ psychologytoday.com       │ directory                │
│ openspacecounselling.ca   │ counselling              │
│ example.com               │ legal                    │
└───────────────────────────┴──────────────────────────┘

[+ Add] [Delete] [? Help]
```

**Interactions:**
- entity_type column: Combobox with dropdown (ENTITY_TYPES from classifiers.py)
- Add: Insert blank row, focus domain field
- Delete: Remove selected row
- Edit inline: Click domain cell to edit, Tab to entity_type dropdown

**Validation (before save):**
- domain non-empty, valid domain format
- entity_type ∈ classification_rules.json entity_types
- No duplicate domains (warn, allow override)
- Cross-file: entity_types used must exist in classification_rules

---

### Tab 7: Classification Rules

**Schema:** Dict with entity_types list, entity_type_descriptions dict, content_patterns dict, entity_patterns dict

**UI:**
```
┌─ Section: Valid Entity Types ─────────────────┐
│ [Treeview of entity types]                    │
│ counselling                                   │
│ legal                                         │
│ directory                                     │
│ ... (8 types)                                 │
│ [+ Add] [Delete]                              │
└──────────────────────────────────────────────┘

┌─ Section: Entity Type Descriptions ───────────┐
│ [Treeview: type → description]                │
│ counselling │ "Mental health counselling.." │
│ legal       │ "Legal services and advice.." │
│ ... (must match entity_types list)           │
│ [+ Add] [Delete]                              │
└──────────────────────────────────────────────┘

┌─ Section: Content Patterns ──────────────────┐
│ (Read-only overview; edit advanced users via YAML) │
│ directory_url: [16 patterns...]               │
│ service_signals: [24 patterns...]             │
│ guide_titles: [18 patterns...]                │
└──────────────────────────────────────────────┘

┌─ Section: Entity Patterns ───────────────────┐
│ (Read-only overview; edit advanced users via YAML) │
└──────────────────────────────────────────────┘
```

**Interactions:**
- Add entity type: Prompt for name
- Add description: Combobox select type, text area for description
- Content/Entity Patterns: Read-only (user edits YAML directly if needed)

**Validation (before save):**
- entity_types list unique, non-empty
- entity_type_descriptions keys ⊆ entity_types (no orphan descriptions)
- entity_type_descriptions values non-empty
- content_patterns, entity_patterns structurally valid
- Cross-file: entity_types must include all types used in intent_mapping

---

### Tab 8: URL Pattern Rules

**Schema:** List of dicts, order-sensitive (first-match-wins)

**UI:**
```
┌─ Treeview (columns: pattern, content_type, entity_types, rationale) ─┐
│ Pattern              │ content_type │ entity_types │ rationale       │
├──────────────────────┼──────────────┼──────────────┼─────────────────┤
│ \.pdf$               │ pdf          │ [any]        │ File extension  │
│ /blog/               │ guide        │ [counselling]│ Blog post URL   │
│ /directory/          │ directory    │ [any]        │ Directory URL   │
└──────────────────────┴──────────────┴──────────────┴─────────────────┘

[+ Add New] [↑ Move Up] [↓ Move Down] [Delete] [? Help]
```

**Interactions:**
- Double-click row → Edit dialog:
  ```
  Edit URL Pattern Rule
  ┌───────────────────────────────────────┐
  │ pattern (regex): [Text field]         │
  │ (Help: Must be valid Python regex)    │
  │                                       │
  │ content_type: [Dropdown: pdf|...]     │
  │ entity_types: [Treeview of types]     │
  │ [+ Add Type] [Delete Type]            │
  │                                       │
  │ rationale: [Text area]                │
  │ [Save] [Cancel]                       │
  └───────────────────────────────────────┘
  ```
- ↑/↓: Move rule up/down (order matters, first-match-wins)
- Delete: Remove rule

**Validation (before save):**
- pattern is valid Python regex (try to compile; error if SyntaxError)
- content_type ∈ {pdf, directory, news, service, guide, other}
- entity_types list non-empty; values ⊆ classification_rules entity_types
- rationale optional

---

## Validation (Centralized)

### File-Specific Validation

Each file has a validator function that returns: `(is_valid: bool, errors: list[str], warnings: list[str])`

**Error** (prevents save):
- Schema violation (missing required fields, wrong type)
- Enum value not in allowed set
- Regex doesn't compile
- String length constraint violated
- Cross-file reference broken

**Warning** (allows save with confirmation):
- Optional field missing (but not required)
- Deprecated pattern detected
- Unused configuration value
- Performance issue (e.g., timeout too short)

### Cross-File Validation

Before save, validate constraints **across** files:

```python
def validate_cross_file_constraints(
    intent_mapping, strategic_patterns, brief_pattern_routing,
    domain_overrides, classification_rules
) → (bool, [errors]):
    
    errors = []
    
    # intent_mapping entity types → classification_rules
    mapping_entity_types = {rule["match"]["entity_type"] for rule in intent_mapping["rules"]}
    valid_entity_types = set(classification_rules["entity_types"])
    if not mapping_entity_types ≤ valid_entity_types:
        errors.append(f"intent_mapping uses entity_types not in classification_rules: {mapping_entity_types - valid_entity_types}")
    
    # strategic_patterns ← brief_pattern_routing references
    pattern_names = {p["Pattern_Name"] for p in strategic_patterns}
    routing_pattern_names = {p["pattern_name"] for p in brief_pattern_routing["patterns"]}
    if not routing_pattern_names ≤ pattern_names:
        missing = routing_pattern_names - pattern_names
        errors.append(f"brief_pattern_routing references patterns not in strategic_patterns: {missing}")
    
    # domain_overrides entity types → classification_rules
    override_entity_types = set(domain_overrides.values())
    if not override_entity_types ≤ valid_entity_types:
        errors.append(f"domain_overrides uses entity_types not in classification_rules: {override_entity_types - valid_entity_types}")
    
    return (len(errors) == 0, errors)
```

---

## Save Workflow

### Before Save

1. User clicks "Save All" button
2. ConfigManagerWindow calls `validate_all_tabs(self.tabs)`
   - Each tab validates its file (call `tab.validate()`)
   - Collect errors and warnings into `errors_by_file`
   - Call `validate_cross_file_constraints()` on all tabs
   - Aggregate into `errors_by_file["_cross_file"]`
3. If **errors** (schema violations):
   - Show **validation error dialog**:
     ```
     Validation Failed
     Cannot save configuration due to the following errors:
     
     [Tab name] → [Field] → [Error message]
     [Suggestion for fix]
     
     intent_mapping → rules[3] → intent must be one of: informational, ...
     → Change "unknown_intent" to one of the valid options
     
     _cross_file → missing pattern in strategic_patterns
     → brief_pattern_routing references pattern "New Pattern" which doesn't exist
     → Add the pattern to strategic_patterns.yml first
     
     [Go to Tab] [Close]
     ```
   - User clicks "Go to Tab" → Focus switches to first error tab
   - User fixes issue, clicks "Save All" again
   - **DO NOT SAVE**

4. If **warnings** (non-critical issues):
   - Show **warning dialog**:
     ```
     Configuration Has Warnings
     Proceed with save? Some configuration may be suboptimal.
     
     ⚠ warning 1: ...
     ⚠ warning 2: ...
     
     [Yes, Save] [No, Review] [Cancel]
     ```
   - User chooses: Save (proceed), Review (go to tab), or Cancel

5. On success (no errors, user confirmed warnings):
   - Create backups: `*.yml.backup.<timestamp>`, `*.json.backup.<timestamp>`
   - Write all files to disk (try-except):
     ```python
     try:
         for tab in self.tabs:
             tab.save_to_disk()
     except Exception as e:
         # Restore from backup
         for backup_path in backup_paths:
             shutil.copy(backup_path, backup_path.without_suffix())
         raise e
     ```
   - Reload all tabs from disk: `tab.load_current_data()` and `tab.render_ui()`
   - Show success dialog:
     ```
     Configuration Saved
     8 files updated:
     - intent_mapping.yml
     - strategic_patterns.yml
     - brief_pattern_routing.yml
     - intent_classifier_triggers.yml
     - config.yml
     - domain_overrides.yml
     - classification_rules.json
     - url_pattern_rules.yml
     ```

---

## Help System

### Help Text Registry

**File-level help:**
```python
HELP_BY_FILE = {
    "intent_mapping.yml": 
        "Maps SERP characteristics (entity type, content type, local pack presence) to intent verdicts. "
        "Rules are evaluated first-match-wins; order matters. Most specific rules should appear first.",
    
    "strategic_patterns.yml":
        "Bowen Family Systems patterns used for content brief generation. "
        "Each pattern has triggers (keywords) that match against the SERP. "
        "When a pattern is selected for a brief, its 'Status_Quo_Message', 'Bowen_Bridge_Reframe', and 'Content_Angle' are used.",
    
    "brief_pattern_routing.yml":
        "Routes People Also Ask (PAA) questions and source keywords to Bowen patterns. "
        "Each pattern specifies which PAA themes, categories, and keyword hints associate with it.",
    
    "intent_classifier_triggers.yml":
        "Trigger words for PAA intent classification (External Locus vs. Systemic). "
        "Medical/therapeutic terms trigger 'External Locus'; systemic/relational terms trigger 'Systemic'.",
    
    "config.yml":
        "Operational settings for the pipeline. SerpAPI parameters, file paths, client context, and analysis thresholds.",
    
    "domain_overrides.yml":
        "Manual overrides for domain entity type classification. "
        "Add entries here to correct misclassifications (e.g., a psychology directory that's classified as 'other').",
    
    "classification_rules.json":
        "Canonical lists of entity types, content patterns, and domain patterns for URL classification. "
        "Rarely edited; changes here affect all pipeline runs.",
    
    "url_pattern_rules.yml":
        "Regex patterns for content type classification (PDF, guide, directory, etc.). "
        "Rules are applied first-match-wins; order matters.",
}
```

**Field-level help:**
```python
HELP_BY_FIELD = {
    "intent_mapping.rules[].match.content_type":
        "Content type of the URL (what kind of page). "
        "Values: pdf | directory | news | service | guide | other | unknown | any (wildcard)",
    
    "intent_mapping.rules[].match.entity_type":
        "Entity type of the URL domain (what kind of organization). "
        "Values: counselling | legal | directory | nonprofit | government | media | professional_association | education | any",
    
    "intent_mapping.rules[].match.local_pack":
        "Whether a local pack (maps) module is present in the SERP. "
        "Values: yes | no | any (wildcard)",
    
    "intent_mapping.rules[].intent":
        "Primary search intent this rule maps to:\n"
        "  - informational: User seeking information (how-to, definitions, research)\n"
        "  - commercial_investigation: Evaluating products/services before purchase\n"
        "  - transactional: Ready to buy/take action\n"
        "  - navigational: Looking for specific website/brand\n"
        "  - local: Geographic/local business search\n"
        "  - uncategorised: Unclassifiable by above rules",
    
    "strategic_patterns.yml[].Pattern_Name":
        "Unique name for this Bowen Family Systems pattern. "
        "Must match exactly in brief_pattern_routing.yml for routing to work.",
    
    "strategic_patterns.yml[].Triggers":
        "List of keywords (min 4 chars each, case-insensitive) that match this pattern against the SERP. "
        "Used to determine if this pattern's brief should be generated.",
    
    "strategic_patterns.yml[].Status_Quo_Message":
        "Describes the current unhealthy pattern/dynamic the client is stuck in. "
        "Why the current approach isn't working (systemic perspective).",
    
    "strategic_patterns.yml[].Bowen_Bridge_Reframe":
        "Reframes the pattern using Bowen Family Systems theory. "
        "The 'aha moment' or reframe that helps clients see their situation differently.",
    
    "strategic_patterns.yml[].Content_Angle":
        "Specific angle or hook for the content brief. "
        "What should the content help the reader understand or do differently?",
    
    "strategic_patterns.yml[].Relevant_Intent_Class":
        "(Optional) PAA intent class this pattern matches. "
        "External Locus = medical/external framing; Systemic = relational/systemic framing. "
        "Improves keyword-to-pattern matching accuracy.",
    
    "brief_pattern_routing.yml[].pattern_name":
        "Must match a Pattern_Name from strategic_patterns.yml exactly. "
        "Determines which content brief receives PAA questions and keywords from this pattern.",
    
    "brief_pattern_routing.yml[].paa_themes":
        "Words/phrases found in People Also Ask question text that suggest this pattern. "
        "Examples: 'therapy', 'therapist', 'mental health' for Medical Model Trap.",
    
    "brief_pattern_routing.yml[].paa_categories":
        "PAA intent class tags from the classifier (External Locus, Systemic, General). "
        "Narrows which PAA questions associate with this pattern.",
    
    "brief_pattern_routing.yml[].keyword_hints":
        "Substrings in the source keyword text that suggest this pattern. "
        "Examples: 'estrangement', 'adult child', 'reach out' for Fusion Trap.",
    
    "intent_classifier_triggers.yml[].medical_triggers":
        "Words that indicate External Locus framing (medical/professional model). "
        "Examples: 'therapy', 'therapist', 'counselor', 'mental health', 'diagnosis'.",
    
    "intent_classifier_triggers.yml[].systemic_triggers":
        "Words that indicate Systemic framing (relational/family systems model). "
        "Examples: 'estrangement', 'relationship', 'cutoff', 'communication', 'differentiation'.",
    
    "config.yml.serpapi.gl":
        "Geographic location code (e.g., 'ca' for Canada, 'us' for USA). "
        "Affects SERP results and local search ranking.",
    
    "config.yml.files.output_json":
        "Path where market analysis JSON is written. "
        "Contains all parsed SERP data and keyword profiles.",
    
    "config.yml.serp_intent.thresholds.confidence_high":
        "Number of classified organic URLs (0-1 scale) required for 'high' confidence. "
        "Example: 0.8 means 80% of top 10 must be classified.",
    
    "domain_overrides.yml":
        "Override domain entity type classification. "
        "Format: domain_name: entity_type (one per line, e.g., example.com: counselling). "
        "Use when the automatic classifier gets it wrong.",
    
    "classification_rules.json[].entity_types":
        "Canonical list of valid entity types (organizations/domains). "
        "Changes here affect all classifications; be careful!",
    
    "url_pattern_rules.yml[].pattern":
        "Python regex (case-insensitive) to match against URL. "
        "Must be valid regex (e.g., '\.pdf$' matches .pdf files, '/blog/' matches blog URLs). "
        "First match wins; order matters.",
    
    "url_pattern_rules.yml[].content_type":
        "Content type assigned if this rule matches. "
        "Values: pdf | directory | news | service | guide | other",
}
```

### Help UI

For every editable field, add a small `(?)` button:

```python
def create_field_with_help(parent, label: str, widget_type: str, initial_value, help_key: str):
    frame = ttk.Frame(parent)
    
    # Label + help button
    label_frame = ttk.Frame(frame)
    ttk.Label(label_frame, text=label).pack(side="left")
    
    if help_key in HELP_BY_FIELD:
        def show_help():
            messagebox.showinfo(
                f"Help: {label}",
                HELP_BY_FIELD[help_key]
            )
        ttk.Button(label_frame, text="?", width=2, command=show_help).pack(side="left", padx=5)
    
    label_frame.pack(fill="x")
    
    # Widget (type-specific)
    if widget_type == "entry":
        widget = ttk.Entry(frame)
        widget.insert(0, str(initial_value))
    elif widget_type == "spinbox":
        widget = ttk.Spinbox(frame, from_=0, to=100)
        widget.insert(0, str(initial_value))
    elif widget_type == "checkbox":
        widget = ttk.Checkbutton(frame)
        widget.state = "selected" if initial_value else "!"
    elif widget_type == "dropdown":
        widget = ttk.Combobox(frame, state="readonly", values=[...])
        widget.set(str(initial_value))
    
    widget.pack(fill="x", expand=True)
    frame.pack(fill="x", pady=5)
    
    return widget
```

---

## Acceptance Criteria

1. ✓ All 8 tabs open without errors (stubs are OK for Phase 1)
2. ✓ Load current data from disk (YAML/JSON parse)
3. ✓ UI renders data structures appropriate to file schema
4. ✓ User can add, edit, delete, reorder entries (basic interactions work)
5. ✓ Each file validates against its schema before save
6. ✓ Cross-file constraints validated (pattern_name refs, entity_type refs, etc.)
7. ✓ All validation errors shown in detail report (tab + field + message + suggestion)
8. ✓ Save creates backup before write
9. ✓ Save fails gracefully if write errors (restore from backup, no data loss)
10. ✓ After save, UI reloads data from disk (no stale state)
11. ✓ Every field has contextual help (`?` button + messagebox text)
12. ✓ Discard changes workflow (prompt if unsaved edits exist)
13. ✓ Unit tests pass: validators + integration tests
14. ✓ Pipeline produces identical output after config edit + save → reload

---

## Risk Mitigation

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Bad intent_mapping rule breaks all reports | **CRITICAL** | Pre-save validation checks rule structure + enum values; cross-file check against intent types |
| Data loss on save failure | **CRITICAL** | Backup files before write; restore on exception |
| User sees stale data after save | **HIGH** | Reload all tabs from disk post-save |
| Broken cross-file refs | **HIGH** | Validate refs at save time; error message guides user to fix |
| UI freeze during save | **MEDIUM** | Threading + progress dialog |
| User makes mistake in config, crashes report | **MEDIUM** | Comprehensive validation pre-save + clear error messages + "undo" via backup restore |

---

## Implementation Timeline

| Phase | Task | Duration | Deliverable |
|-------|------|----------|-------------|
| 1 | Extract validators, scaffold ConfigManager + BaseConfigTab, add button to serp-me.py | 1-2 hrs | Imports resolve, tabs open (empty), unit tests pass |
| 2 | DomainOverrides + ClassificationRules tabs | 1-2 hrs | Two tabs fully functional (load, edit, save) |
| 3 | IntentMapping + StrategicPatterns tabs + edit dialogs | 2-3 hrs | Two more tabs + nested form editing |
| 4 | BriefPatternRouting + IntentClassifierTriggers tabs | 2-3 hrs | Four tabs total functional |
| 5 | ConfigSettings + UrlPatternRules tabs (type-safe widgets) | 2-3 hrs | All 8 tabs functional |
| 6 | Cross-file validation + help registry | 1-2 hrs | Validation + help text complete |
| 7 | Save workflow (backup, restore, error recovery) | 1-2 hrs | Safe save pipeline |
| 8 | Testing + documentation + integration tests | 2-3 hrs | Full test coverage, user guide |
| **Total** | — | **12-20 hrs** | **Full Configuration Manager** |

---

## Files to Create/Modify

### New Files
- `config_manager.py` (1500-2000 lines) — Main GUI module
- `config_validators.py` (800-1200 lines) — Centralized validators
- `tests/test_config_validators.py` — Validator unit tests
- `tests/test_config_manager.py` — Integration tests
- `docs/config_manager_guide.md` — User documentation

### Modified Files
- `serp-me.py` — Add button + import + handler method

### No Changes Needed
- `config.yml` — Backward compatible

---

## References

### Existing Code Patterns

- **Domain override review pattern** (`serp-me.py:806-1293`) — Reuse Treeview layout, combobox, validation
- **YAML/JSON loading** (`serp-me.py:339-348`) — Load/save pattern
- **Error handling** (`serp-me.py:817-848`) — Try-except + messagebox
- **Threading** (`serp-me.py:734-779`) — Thread-safe UI updates via `root.after()`
- **Validation composition** (`apply_domain_override_candidates.py`) — Merge + validate pattern
- **Entity types** (`classifiers.py`) — ENTITY_TYPES, ENTITY_TYPE_DESCRIPTIONS constants
- **Intent validation** (`intent_verdict.py`) — Intent enum, confidence rules

### Related Files

- `intent_verdict.py` — Intent mapping logic (extract validator)
- `pattern_matching.py` — Strategic patterns validation (extract validator)
- `brief_rendering.py` — Brief routing validation (extract validator)
- `intent_classifier.py` — Intent trigger validation (extract validator)
- `classifiers.py` — Entity/content classification rules (extract validator)
