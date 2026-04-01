import pytest
import os
from src.database import DatabaseManager

@pytest.fixture
def db():
    db_path = "test_competitor_history.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    manager = DatabaseManager(db_path)
    yield manager
    if os.path.exists(db_path):
        os.remove(db_path)

def test_run_creation(db):
    run_id1 = db.create_run("client.com")
    run_id2 = db.create_run("client.com")
    assert run_id2 == run_id1 + 1
    assert db.get_latest_run_id() == run_id2

def test_volatility_logic(db):
    run_id1 = db.create_run("client.com")
    run_id2 = db.create_run("client.com")
    
    # Run 1: Competitor at Pos 10
    db.save_competitor_metrics([
        {"domain": "comp.com", "url": "url1", "keyword": "anxiety", "position": 10, "traffic": 100}
    ], run_id=run_id1)
    
    # Run 2: Competitor drops to Pos 5 (Shift of 5)
    db.save_competitor_metrics([
        {"domain": "comp.com", "url": "url1", "keyword": "anxiety", "position": 5, "traffic": 100}
    ], run_id=run_id2)
    
    alerts = db.get_volatility_alerts(run_id2)
    assert len(alerts) == 1
    assert alerts[0]['domain'] == "comp.com"
    assert alerts[0]['shift'] == -5.0 # Average position improved (decreased) by 5

def test_strategic_openings(db):
    run_id = db.create_run("client.com")
    
    # Case 1: High traffic, 0 systems score (Strategic Vacuum)
    db.save_traffic_magnet(run_id, "comp.com", "url1", "anxiety", 500.0, 10, 0)
    
    # Case 2: High traffic, high systems score (Not an opening)
    db.save_traffic_magnet(run_id, "comp.com", "url2", "depression", 500.0, 10, 5)
    
    openings = db.identify_strategic_openings(run_id)
    assert len(openings) == 1
    assert openings[0]['keyword'] == "anxiety"
    assert openings[0]['medical_score'] == 10
