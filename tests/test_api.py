# tests/test_api.py
import pytest
from src.api.yandex_client import YandexAPIClient
from src.api.ozon_client import OzonAPIClient
from src.api.parsers import YandexOrderParser, OzonOrderParser
from src.api.services import OrderService
from unittest.mock import patch, Mock, AsyncMock

# Фикстуры для клиентов
@pytest.fixture
def yandex_client():
    return YandexAPIClient("test_token", "http://test-api", "test_campaign", "test_business")

@pytest.fixture
def ozon_client():
    return OzonAPIClient("test_key", "test_client", "http://test-api")

# Тесты для YandexAPIClient
def test_yandex_get_orders_success(yandex_client):
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"orders": [{"id": "1"}]}
        mock_get.return_value = mock_response
        orders = yandex_client.get_orders("PROCESSING", "STARTED")
        assert len(orders) == 1
        assert orders[0]["id"] == "1"

def test_yandex_get_orders_failure(yandex_client):
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = Exception("Server error")
        mock_get.return_value = mock_response
        with pytest.raises(Exception, match="Server error"):
            yandex_client.get_orders("PROCESSING", "STARTED")

# Тесты для OzonAPIClient
def test_ozon_get_orders_success(ozon_client):
    with patch('requestsKwargs'({'requests.post': Mock(return_value=Mock(status_code=200, json=lambda: {"result": {"postings": [{"posting_number": "123"}] }))}))
    orders = ozon_client.get_orders("awaiting_packaging")
    assert len(orders) == 1
    assert orders[0]["posting_number"] == "123"

def test_ozon_get_label_failure(ozon_client):
    with patch('requests.post') as mock_post:
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        mock_post.return_value = mock_response
        label = ozon_client.get_label("123")
        assert label is None

# Тесты для парсеров
def test_yandex_parser():
    parser = YandexOrderParser()
    order_data = {
        "id": "456",
        "items": [{"shopSku": "sku1", "offerName": "Item1", "count": 2}],
        "delivery": {"address": {"city": "Moscow"}, "shipments": [{"shipmentDate": "2025-04-10"}]},
        "itemsTotal": 500.0
    }
    order = parser.parse(order_data)
    assert order.id == "456"
    assert len(order.items) == 1
    assert order.items[0].shop_sku == "sku1"
    assert order.delivery.address.city == "Moscow"

def test_ozon_parser():
    parser = OzonOrderParser()
    order_data = {
        "posting_number": "789",
        "products": [{"sku": "sku2", "name": "Item2", "quantity": 3}],
        "delivery": {"address": {"city": "SPb"}, "shipment_date": "2025-04-11"},
        "price": "300"
    }
    order = parser.parse(order_data)
    assert order.id == "789"
    assert len(order.items) == 1
    assert order.items[0].offer_name == "Item2"
    assert order.items_total == 300.0

# Тесты для OrderService
@pytest.mark.asyncio
async def test_check_new_orders(yandex_client):
    with patch.object(yandex_client, 'get_orders', return_value=[{"id": "1", "items": [], "delivery": {"address": {}, "shipments": [{}]}}]):
        bot = AsyncMock()
        db = Mock(load_sent_orders=Mock(return_value=[]), save_sent_order=Mock())
        service = OrderService({"yandex": yandex_client}, db)
        await service.check_new_orders(bot, "chat_id")
        bot.send_document.assert_awaited()  # Проверяем, что уведомление отправлено