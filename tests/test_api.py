import pytest
from src.api.client import YandexAPIClient
from unittest.mock import patch, Mock

@pytest.fixture
def client():
    return YandexAPIClient("test_token", "http://test-api")

def test_get_orders_success(client):
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"orders": [{"id": "1"}]}
        mock_get.return_value = mock_response
        orders = client.get_orders("test_campaign", "PROCESSING", "STARTED")
        assert len(orders) == 1
        assert orders[0]["id"] == "1"

def test_get_orders_failure(client):
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = Exception("Server error")
        mock_get.return_value = mock_response
        with pytest.raises(Exception):
            client.get_orders("test_campaign", "PROCESSING", "STARTED")