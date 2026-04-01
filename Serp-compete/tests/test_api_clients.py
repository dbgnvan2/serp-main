import pytest
import requests_mock
from src.api_clients import DataForSEOClient, MozClient

def test_dataforseo_get_relevant_pages():
    client = DataForSEOClient()
    with requests_mock.Mocker() as m:
        m.post("https://api.dataforseo.com/v3/dataforseo_labs/google/ranked_keywords/live",
               json={
                   "tasks": [{
                       "result": [{
                           "items": [
                               {
                                   "keyword": "anxiety", 
                                   "ranked_serp_element": {
                                       "serp_item": {
                                           "url": "https://example.com/page1",
                                           "rank_absolute": 5,
                                           "etv": 100
                                       }
                                   }
                               }
                           ]
                       }]
                   }]
               })
        
        results = client.get_relevant_pages("example.com")
        assert len(results) == 1
        assert results[0]['url'] == "https://example.com/page1"
        assert results[0]['keyword_data']['keyword'] == "anxiety"

def test_moz_get_url_metrics():
    client = MozClient()
    with requests_mock.Mocker() as m:
        m.post("https://api.moz.com/v2/url_metrics",
               json={
                   "results": [
                       {"url": "https://example.com/page1", "page_authority": 35},
                       {"url": "https://example.com/page2", "page_authority": 42}
                   ]
               })
        
        results = client.get_url_metrics(["https://example.com/page1", "https://example.com/page2"])
        assert len(results) == 2
        assert results[0]['page_authority'] == 35
        assert results[1]['page_authority'] == 42
