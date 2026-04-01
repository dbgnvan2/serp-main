import pytest
import json
import os

SHARED_CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "shared_config.json"))

def test_config_exists():
    assert os.path.exists(SHARED_CONFIG_PATH), "shared_config.json is missing from root"

def test_gsc_config_integrity():
    with open(SHARED_CONFIG_PATH, 'r') as f:
        config = json.load(f)
    
    auth = config.get("auth", {})
    property_url = auth.get("gsc_property_url", "")
    
    # Requirement: GSC Property URL must be a valid HTTPS URL
    assert property_url.startswith("https://"), "GSC Property URL must use HTTPS"
    assert property_url.endswith("/"), "GSC Property URL should end with a trailing slash for GSC consistency"
    
    # Requirement: Client Secrets path should be absolute or point to an existing file
    secrets_path = auth.get("gsc_client_secrets", "")
    assert secrets_path, "GSC Client Secrets path is missing from config"
    
def test_clinical_dictionary_integrity():
    CLINICAL_DICT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "clinical_dictionary.json"))
    assert os.path.exists(CLINICAL_DICT_PATH), "clinical_dictionary.json is missing from root"
    
    with open(CLINICAL_DICT_PATH, 'r') as f:
        data = json.load(f)
    
    assert "tier_1_medical" in data
    assert "tier_2_systems" in data
    assert "tier_3_bowen" in data
    assert len(data["tier_1_medical"]) > 0, "Clinical dictionary is empty"
