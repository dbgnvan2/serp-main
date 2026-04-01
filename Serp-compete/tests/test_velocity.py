import pytest
import os
import sqlite3
from src.velocity_module import VelocityTracker

@pytest.fixture
def temp_tracker(tmp_path):
    # Create a dummy shared_config.json
    config_file = tmp_path / "shared_config.json"
    config_file.write_text('{"technical": {"database_path": "test_velocity.db"}}')
    
    tracker = VelocityTracker(str(config_file))
    yield tracker
    
    # Cleanup
    if os.path.exists(tracker.db_path):
        os.remove(tracker.db_path)

def test_save_and_calculate_velocity(temp_tracker):
    url = "https://competitor.com/page"
    kw = "anxiety"
    
    # Run 1
    temp_tracker.save_market_snapshot("competitor.com", url, kw, rank=10, da=30, systems_score=1.0, medical_score=5.0)
    
    # Run 2 (Dropping Rank and DA)
    temp_tracker.save_market_snapshot("competitor.com", url, kw, rank=12, da=28, systems_score=1.5, medical_score=4.0)
    
    v = temp_tracker.calculate_velocity(url, kw)
    
    assert v["rank_drift"] == -2
    assert v["da_drift"] == -2
    assert v["systems_drift"] == 0.5
    assert v["medical_drift"] == -1.0

def test_fragile_magnet_alert(temp_tracker):
    url = "https://competitor.com/fragile"
    kw = "trauma"
    
    # Run 1
    temp_tracker.save_market_snapshot("competitor.com", url, kw, rank=5, da=40, systems_score=0, medical_score=10)
    
    # Run 2 (Dropping significantly)
    temp_tracker.save_market_snapshot("competitor.com", url, kw, rank=8, da=39, systems_score=0, medical_score=10)
    
    alerts = temp_tracker.get_market_alerts()
    assert len(alerts) == 1
    assert alerts[0]["type"] == "Fragile Magnet"
    assert "Strike this page now" in alerts[0]["advice"]
