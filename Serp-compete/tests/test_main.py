import pytest
from unittest.mock import MagicMock, patch
from src.main import pre_flight_check

@patch('src.main.DataForSEOClient')
@patch('src.main.ReframeEngine')
@patch('requests.get')
def test_pre_flight_check_low_balance(mock_get, mock_reframe, mock_dfs):
    # Mock low balance response
    mock_get.return_value.json.return_value = {
        'tasks': [{'result': [{'money': {'balance': -0.01}}]}]
    }
    
    with patch.dict('os.environ', {
        'DATAFORSEO_LOGIN': 'test', 'DATAFORSEO_PASSWORD': 'test',
        'OPENAI_API_KEY': 'test', 'MOZ_TOKEN': 'test'
    }):
        assert pre_flight_check() is False

@patch('src.main.DataForSEOClient')
@patch('src.main.ReframeEngine')
@patch('requests.get')
def test_pre_flight_check_success(mock_get, mock_reframe, mock_dfs):
    # Mock positive balance
    mock_get.return_value.json.return_value = {
        'tasks': [{'result': [{'money': {'balance': 10.0}}]}]
    }
    # Mock OpenAI model retrieval success
    mock_reframe_instance = MagicMock()
    mock_reframe.return_value = mock_reframe_instance
    
    with patch.dict('os.environ', {
        'DATAFORSEO_LOGIN': 'test', 'DATAFORSEO_PASSWORD': 'test',
        'OPENAI_API_KEY': 'test', 'MOZ_TOKEN': 'test'
    }):
        assert pre_flight_check() is True
