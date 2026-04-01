import pytest
from src.analysis import AnalysisEngine

def test_find_keyword_intersection():
    engine = AnalysisEngine("client.com")
    competitor_keywords = {
        "comp1.com": {"counselling", "therapy", "anxiety"},
        "comp2.com": {"counselling", "trauma", "anxiety"},
        "comp3.com": {"counselling", "family", "anxiety"}
    }
    client_keywords = {"counselling"}
    
    intersection = engine.find_keyword_intersection(competitor_keywords, client_keywords)
    # Both "counselling" and "anxiety" are in all 3, but "counselling" is in client
    assert intersection == {"anxiety"}

def test_check_feasibility():
    engine = AnalysisEngine("client.com")
    # Case 1: Feasible (Client DA 30 + 5 = 35, Comp PA 35)
    assert engine.check_feasibility(30, 35)["feasible"] is True
    # Case 2: Not Feasible (Client DA 30 + 5 = 35, Comp PA 45)
    result = engine.check_feasibility(30, 45)
    assert result["feasible"] is False
    assert result["suggestion"] == "Hyper-Local Pivot"
