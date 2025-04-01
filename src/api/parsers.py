# src/api/parsers.py
from typing import Dict
from src.api.models import Order, Item, Address, Delivery

class OrderParser:
    """Base class for parsing marketplace order data."""
    def parse(self, order_data: Dict) -> Order:
        raise NotImplementedError("Subclasses must implement parse method")

class YandexOrderParser(OrderParser):
    """Parser for Yandex Market order data."""
    def parse(self, order_data: Dict) -> Order:
        address = Address(**{k: order_data["delivery"].get("address", {}).get(k, "") for k in Address.__annotations__})
        shipment_date = order_data["delivery"].get("shipments", [{}])[0].get("shipmentDate", "Not specified")
        items = [Item(shop_sku=item["shopSku"], offer_name=item["offerName"], count=item["count"], id=item.get("id")) 
                 for item in order_data["items"]]
        return Order(
            id=str(order_data["id"]), items=items, delivery=Delivery(address=address, shipment_date=shipment_date),
            items_total=order_data.get("itemsTotal", 0.0), status=order_data.get("status", ""),
            substatus=order_data.get("substatus", "")
        )

class OzonOrderParser(OrderParser):
    """Parser for Ozon order data."""
    def parse(self, order_data: Dict) -> Order:
        address_data = order_data.get("delivery", {}).get("address", {})
        address = Address(
            city=address_data.get("city", ""),
            street=address_data.get("address_tail", ""),
            postcode=address_data.get("zip_code", "")
        )
        shipment_date = order_data.get("shipment_date", "Not specified")
        items = [Item(shop_sku=str(item["sku"]), offer_name=item["name"], count=item["quantity"], id=item.get("posting_number")) 
                 for item in order_data.get("products", [])]
        return Order(
            id=str(order_data["posting_number"]), items=items, delivery=Delivery(address=address, shipment_date=shipment_date),
            items_total=float(order_data.get("price", "0")), status=order_data.get("status", ""),
            substatus=""
        )

# Фабрика парсеров
PARSERS = {
    "yandex": YandexOrderParser(),
    "ozon": OzonOrderParser()
}

def get_parser(platform: str) -> OrderParser:
    """Get the appropriate parser for the platform."""
    parser = PARSERS.get(platform)
    if not parser:
        raise ValueError(f"Unsupported platform: {platform}")
    return parser