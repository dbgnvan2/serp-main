import pytest
import pandas as pd
import os
from src.ingestion import validate_domain, read_key_domains

def test_validate_domain():
    assert validate_domain("example.com") is True
    assert validate_domain("sub.example.co.uk") is True
    assert validate_domain("wellspringcounselling.ca") is True
    assert validate_domain("http://example.com") is False
    assert validate_domain("example.com/path") is False
    assert validate_domain("example.com/") is False
    assert validate_domain("not_a_domain") is False

def test_read_key_domains(tmp_path):
    d = tmp_path / "data"
    d.mkdir()
    csv_file = d / "Key_domains.csv"
    csv_file.write_text("domain,role\nwellspring.ca,competitor\nlivingsystems.ca,client")
    
    competitors, client = read_key_domains(str(csv_file))
    assert competitors == ["wellspring.ca"]
    assert client == "livingsystems.ca"

def test_read_key_domains_invalid(tmp_path):
    d = tmp_path / "data"
    d.mkdir()
    csv_file = d / "Key_domains_invalid.csv"
    csv_file.write_text("domain,role\nhttp://invalid.ca,competitor\nlivingsystems.ca,client")
    
    with pytest.raises(ValueError, match="Invalid root domains found"):
        read_key_domains(str(csv_file))
