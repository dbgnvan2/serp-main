import pytest
import os
import sqlite3
from src.database import DatabaseManager

@pytest.fixture
def temp_db():
    db_path = "test_competitor_history.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    db = DatabaseManager(db_path)
    yield db
    if os.path.exists(db_path):
        os.remove(db_path)

def test_competitor_tagging(temp_db):
    # Volume Scaler: Traffic > 1000, Medical > 15
    temp_db.tag_competitor_position("volumescaler.com", medical_score=20, systems_t2=5, systems_t3=0, traffic=1500)
    meta = temp_db.get_competitor_metadata("volumescaler.com")
    assert meta['market_position'] == "Volume Scaler"
    
    # Direct Systemic: T3 > 0
    temp_db.tag_competitor_position("systemic.com", medical_score=5, systems_t2=5, systems_t3=2, traffic=100)
    meta = temp_db.get_competitor_metadata("systemic.com")
    assert meta['market_position'] == "Direct Systemic"
    
    # Generalist: T2 > 10
    temp_db.tag_competitor_position("generalist.com", medical_score=5, systems_t2=15, systems_t3=0, traffic=100)
    meta = temp_db.get_competitor_metadata("generalist.com")
    assert meta['market_position'] == "Generalist"

def test_feasibility_drift(temp_db):
    run_id1 = temp_db.create_run("client.com")
    url = "https://competitor.com/page"
    
    # First run
    temp_db.save_competitor_history(run_id1, url, position=1, pa=30, traffic=500)
    
    # Second run with drift
    run_id2 = temp_db.create_run("client.com")
    temp_db.save_competitor_history(run_id2, url, position=1, pa=25, traffic=500) # PA dropped from 30 to 25
    
    alerts = temp_db.get_feasibility_drift(run_id2)
    assert len(alerts) == 1
    assert alerts[0]['url'] == url
    assert alerts[0]['drift'] == -5
    assert alerts[0]['alert'] == "Fragile Magnet"

def test_no_drift(temp_db):
    run_id1 = temp_db.create_run("client.com")
    url = "https://competitor.com/page"
    
    temp_db.save_competitor_history(run_id1, url, position=1, pa=30, traffic=500)
    
    run_id2 = temp_db.create_run("client.com")
    temp_db.save_competitor_history(run_id2, url, position=1, pa=29, traffic=500) # Drift is -1 (> -2)
    
    alerts = temp_db.get_feasibility_drift(run_id2)
    assert len(alerts) == 0
